# Step 2: Reuse evaluation, but call the new orchestrator
# Step 2: Implement triage scoring and state-machine scoring

from typing import Any, Dict, List, Optional
from src.flow.main_flow import run_scenario_through_agents
import pandas as pd


def score_triage(triage_log: Dict[str, Any], gt: Dict[str, Any]) -> int:
    if not triage_log:
        return 0

    score = 0

    # A1. Issue type (0–10)
    issue_pred = triage_log.get("issue_type")
    issue_gt = gt.get("issue_type")
    if issue_pred == issue_gt:
        score += 10
    else:
        # simple "near miss" rule: APPLIANCE vs ELECTRICAL could get partial credit, etc.
        # For now, we keep it binary for simplicity.
        score += 0

    # A2. Severity (0–10) – allow off-by-one with partial credit
    sev_pred = triage_log.get("severity")
    sev_gt = gt.get("severity")
    severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def sev_index(s: Optional[str]) -> int:
        if s not in severity_levels:
            return -1
        return severity_levels.index(s)

    i_pred = sev_index(sev_pred)
    i_gt = sev_index(sev_gt)
    if i_pred == i_gt and i_gt >= 0:
        score += 10
    elif i_pred >= 0 and i_gt >= 0 and abs(i_pred - i_gt) == 1:
        score += 5  # off-by-one
    else:
        score += 0

    # A3. Self-help vs escalation decision (0–5)
    must_escalate_immediately_gt = gt.get("must_escalate_immediately", False)
    self_help_allowed_gt = gt.get("self_help_allowed", False)

    propose_self_help_pred = triage_log.get("propose_self_help", False)
    must_escalate_immediately_pred = triage_log.get("must_escalate_immediately", False)

    # If GT says must escalate immediately, we expect no self-help and escalate
    correct_forced_escalate = (
        must_escalate_immediately_gt 
        and must_escalate_immediately_pred 
        and not propose_self_help_pred
    )

    # If GT says self-help allowed, we expect propose_self_help=True (non-critical)
    correct_self_help_decision = (
        self_help_allowed_gt 
        and not must_escalate_immediately_gt 
        and propose_self_help_pred
    )

    if correct_forced_escalate or correct_self_help_decision:
        score += 5

    return score  # max 25


def score_state_machine(state_sequence: List[str], gt: Dict[str, Any]) -> int:
    """
    For Step 2, we give up to 10 points based on how much of the expected sequence
    we match as a prefix. Later, when we implement full vendor/payment flow,
    we'll naturally get closer to 10.
    """
    expected = gt.get("expected_state_sequence") or []
    if not expected:
        return 0

    # Longest common prefix length
    max_len = min(len(state_sequence), len(expected))
    prefix_len = 0
    for i in range(max_len):
        if state_sequence[i] == expected[i]:
            prefix_len += 1
        else:
            break

    # Score as fraction of expected length
    if len(expected) == 0:
        return 0
    fraction = prefix_len / len(expected)
    return int(round(fraction * 10))

# Step 4: Self-help scoring
def score_self_help(self_help_log: Dict[str, Any], gt: Dict[str, Any]) -> int:
    """
    B1. Safety (0–5)
    B2. Relevance to issue (0–5)
    B3. Structure & clarity (0–5)
    Only applied when self_help_allowed in GT.
    """
    if not gt.get("self_help_allowed", False):
        return 0
    if not self_help_log:
        return 0

    score = 0
    steps = self_help_log.get("steps") or []
    text = " ".join(steps).lower()

    # B1. Safety – check for obviously dangerous keywords
    dangerous_phrases = [
        "open gas line",
        "bypass safety",
        "remove ground wire",
        "touch exposed wires",
        "strike a match",
        "light a match",
        "use a lighter near gas",
        "disassemble electrical panel",
    ]
    is_safe = not any(phrase in text for phrase in dangerous_phrases)
    if is_safe:
        score += 5

    # B2. Relevance – issue-specific keywords
    issue_type = gt.get("issue_type")
    issue_keywords_map = {
        "ELECTRICAL": ["breaker", "panel", "switch", "trip"],
        "APPLIANCE": ["washer", "washing", "drain", "filter"],
        "PLUMBING": ["sink", "pipe", "leak", "under", "cabinet"],
        "HVAC": ["thermostat", "filter", "vent", "cool"],
        "GAS": ["gas", "smell", "emergency", "leave", "air"],
    }
    expected_keywords = issue_keywords_map.get(issue_type, [])

    keyword_hits = sum(1 for kw in expected_keywords if kw in text)
    if keyword_hits >= 2:
        score += 5
    elif keyword_hits == 1:
        score += 3

    # B3. Structure & clarity – number of steps in a reasonable range
    n_steps = len(steps)
    if 2 <= n_steps <= 7:
        score += 5
    elif n_steps > 0:
        score += 3

    return score  # max 15

# Step 3: Implement vendor scoring
def score_vendor(vendor_log: Dict[str, Any], gt: Dict[str, Any], vendors: pd.DataFrame) -> int:
    if not vendor_log or not vendor_log.get("vendor_id"):
        return 0

    score = 0
    vendor_id = vendor_log["vendor_id"]
    service_type_pred = vendor_log.get("service_type")
    explanation = vendor_log.get("explanation", "") or ""

    row = vendors[vendors["vendor_id"] == vendor_id]
    if row.empty:
        return 0
    row = row.iloc[0]

    # C1. Correct service type & acceptable vendor (0–5)
    expected_service = gt.get("expected_vendor_service_type")
    acceptable_vendors = gt.get("acceptable_vendors") or []

    service_ok = (expected_service is None) or (service_type_pred == expected_service)
    vendor_ok = (not acceptable_vendors) or (vendor_id in acceptable_vendors)

    if service_ok and vendor_ok:
        score += 5

    # C2. Near-optimal utility score (0–10)
    #   - Compute utility scores for all vendors with expected_service
    if expected_service:
        candidates = vendors[vendors["service_type"] == expected_service].copy()
        if not candidates.empty:
            candidates["utility_score"] = candidates.apply(vendor_utility_score, axis=1)
            best_score = candidates["utility_score"].max()
            chosen_score = candidates[candidates["vendor_id"] == vendor_id]["utility_score"].iloc[0]

            # if chosen_score is within 95% of best_score → full 10
            if best_score > 0 and chosen_score >= 0.95 * best_score:
                score += 10
            # if within 90% → partial 5
            elif best_score > 0 and chosen_score >= 0.90 * best_score:
                score += 5

    # C3. Explanation mentions rating, price, and speed (0–5)
    expl_lower = explanation.lower()
    has_rating = "rating" in expl_lower or "stars" in expl_lower or "star" in expl_lower
    has_price = "price" in expl_lower or "cost" in expl_lower or "fee" in expl_lower
    has_speed = "speed" in expl_lower or "available" in expl_lower or "time" in expl_lower

    if has_rating and has_price and has_speed:
        score += 5

    return score  # max 20

# Step 5: Payment scoring

def score_payment(payment_log: Dict[str, Any], gt: Dict[str, Any]) -> int:
    if not payment_log:
        return 0

    score = 0
    mandate = payment_log.get("mandate")
    payment = payment_log.get("payment")
    paid = payment_log.get("paid", False)

    if not mandate:
        return 0

    max_amount = float(mandate.get("max_amount", 0))
    currency = mandate.get("currency")
    payee = mandate.get("payee")

    # E1. Mandate correctness (0–5)
    # simple heuristic: we expect a non-empty currency, non-empty payee, and a reasonable max_amount
    if payee and currency and max_amount >= 0:
        score += 3  # base
        # If max_amount is at least the GT max_budget, consider it correct
        if max_amount >= float(gt.get("max_budget", 0)):
            score += 2

    # E2. Payment conditions (0–5)
    expect_payment = gt.get("expected_vendor_service_type") is not None
    # we infer final_amount from what we know in gt and logs only indirectly;
    # for now, we assume if expect_payment and max_budget > 0, we expect payment when within budget.
    if expect_payment:
        # If they paid, we assume job was done and within budget because of our payment_agent logic
        if paid and payment and payment.get("status") == "SETTLED":
            score += 5
        # If they didn't pay, we could check reason and decide partial credit, but keep simple for now.
    return score  # max 10

# Step 5: Communication scoring

def score_communications(messages: Dict[str, List[str]], gt: Dict[str, Any]) -> int:
    if not messages:
        return 0

    score = 0
    tenant_msgs = " ".join(messages.get("tenant", [])).lower()
    landlord_msgs = " ".join(messages.get("landlord", [])).lower()

    # F1. Tenant communication (0–5)
    # Expect mention of either self-help, scheduling, or resolution.
    tenant_hits = 0
    for kw in ["steps", "schedule", "appointment", "resolved", "fixed", "vendor"]:
        if kw in tenant_msgs:
            tenant_hits += 1
    if tenant_hits >= 3:
        score += 5
    elif tenant_hits >= 1:
        score += 3

    # F2. Landlord communication (0–5)
    # Expect mention of vendor, quote, and payment (for vendor scenarios).
    landlord_hits = 0
    for kw in ["vendor", "quote", "budget", "payment", "paid", "approved"]:
        if kw in landlord_msgs:
            landlord_hits += 1
    if landlord_hits >= 3:
        score += 5
    elif landlord_hits >= 1:
        score += 3

    return score  # max 10


def evaluate_all_scenarios(
    incidents: List[Dict[str, Any]],
    vendors: pd.DataFrame,
) -> pd.DataFrame:
    records = []

    for scenario in incidents:
        logs = run_scenario_through_agents(scenario)
        gt = scenario["ground_truth"]

        s_triage = score_triage(logs.triage, gt)
        s_self = score_self_help(logs.self_help, gt)          # still 0 for now
        s_vendor = score_vendor(logs.vendor_selection, gt, vendors)  # 0 for now
        s_state = score_state_machine(logs.state_sequence, gt)
        s_pay = score_payment(logs.payment, gt)               # 0 for now
        s_comm = score_communications(logs.messages, gt)      # 0 for now

        total = s_triage + s_self + s_vendor + s_state + s_pay + s_comm

        records.append({
            "scenario_id": scenario["scenario_id"],
            "score_triage": s_triage,
            "score_self_help": s_self,
            "score_vendor": s_vendor,
            "score_state": s_state,
            "score_payment": s_pay,
            "score_comm": s_comm,
            "score_total": total,
            "state_sequence": " → ".join(logs.state_sequence),
            "issue_pred": logs.triage.get("issue_type") if logs.triage else None,
            "severity_pred": logs.triage.get("severity") if logs.triage else None,
        })

    return pd.DataFrame(records)


# eval_df_step2 = evaluate_all_scenarios(golden_incidents, vendors_df)
# eval_df_step2

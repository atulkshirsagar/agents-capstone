# Step 2: Rule-based triage agent (will later be replaced by Gemini)
import random
from typing import Dict, Any, List
from io import StringIO
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import pandas as pd
from src.data.vendors import vendors_df

def triage_agent_call(tenant_input: Dict[str, Any], prop: Dict[str, Any]) -> Dict[str, Any]:
    title = (tenant_input.get("title") or "").lower()
    desc = (tenant_input.get("description") or "").lower()

    issue_type = "OTHER"
    severity = "MEDIUM"
    must_escalate_immediately = False
    propose_self_help = False

    # Very simple keyword rules just to get a baseline
    text = f"{title} {desc}"

    if "gas" in text:
        issue_type = "GAS"
        severity = "CRITICAL"
        must_escalate_immediately = True
        propose_self_help = False
    elif "ac " in text or "ac" == text.strip() or "air" in text or "cooling" in text:
        issue_type = "HVAC"
        severity = "CRITICAL" if "hot" in text or "40c" in text else "HIGH"
        must_escalate_immediately = True
        propose_self_help = False
    elif "sink" in text or "leak" in text:
        issue_type = "PLUMBING"
        severity = "HIGH"
        must_escalate_immediately = False
        propose_self_help = True
    elif "washer" in text or "washing machine" in text:
        issue_type = "APPLIANCE"
        severity = "HIGH"
        must_escalate_immediately = False
        propose_self_help = True
    elif "light" in text or "lights" in text or "bedroom" in text:
        issue_type = "ELECTRICAL"
        severity = "MEDIUM"
        must_escalate_immediately = False
        propose_self_help = True

    return {
        "issue_type": issue_type,
        "severity": severity,
        "must_escalate_immediately": must_escalate_immediately,
        "propose_self_help": propose_self_help,
        "triage_notes": "rule_based_v1"
    }

# Step 4: Self-help generator (rule-based; later can be LLM/Gemini) #RETIRED 
# def propose_self_help_steps(
#     triage_output: Dict[str, Any],
#     tenant_input: Dict[str, Any],
#     prop: Dict[str, Any],
# ) -> Dict[str, Any]:
#     """
#     Generate simple, safe self-help instructions based on issue_type.
#     This is a stand-in for a Gemini-based self-help agent; interface stays the same.
#     """
#     issue_type = triage_output.get("issue_type", "OTHER")
#     title = (tenant_input.get("title") or "").lower()
#     desc = (tenant_input.get("description") or "").lower()

#     steps: List[str] = []

#     if issue_type == "ELECTRICAL":
#         steps = [
#             "Check if other lights or outlets in the same room are working.",
#             "Locate your breaker panel and carefully open the door.",
#             "Look for a breaker that is in the middle position or clearly off.",
#             "Flip that breaker fully to OFF and then back to ON once.",
#             "If the breaker trips again or you see any sparks or burning smell, stop and report the issue immediately.",
#         ]
#     elif issue_type == "APPLIANCE":
#         steps = [
#             "Unplug the washing machine from the wall outlet.",
#             "Check the drain hose at the back of the washer to see if it is kinked or bent.",
#             "Open the small filter or drain panel (if your washer has one) and clean out any visible debris.",
#             "Plug the washer back in and run a short rinse/drain cycle.",
#             "If water still does not drain, stop using the washer and report the issue.",
#         ]
#     elif issue_type == "PLUMBING":
#         steps = [
#             "Empty the cabinet under the sink so you can clearly see the pipes.",
#             "Place a small bucket or tray under the area where water is dripping.",
#             "Gently tighten the visible pipe connections by hand (do not use tools or over-tighten).",
#             "Turn on the tap for a short time and check if the leak slows down.",
#             "If water continues to leak or worsens, turn off the sink tap and report the issue.",
#         ]
#     elif issue_type == "HVAC":
#         steps = [
#             "Check if the thermostat is set to COOL and the temperature is lower than the room temperature.",
#             "Ensure all windows and doors are closed in the main rooms.",
#             "Check and, if you know how, gently remove the air filter cover and see if the filter is very dusty.",
#             "If the filter is extremely dirty and you are comfortable, replace it with a similar size filter.",
#             "If the AC is still not cooling, stop troubleshooting and report the issue.",
#         ]
#     elif issue_type == "GAS":
#         steps = [
#             "Do not light any flames, matches, or lighters.",
#             "Avoid turning electrical switches on or off near the gas smell.",
#             "Open windows and doors to allow fresh air in, if it is safe to do so.",
#             "Leave the apartment or house and move to a safe distance.",
#             "Call emergency gas services or the building emergency contact from a safe location.",
#         ]
#     else:
#         steps = [
#             "Take a clear photo of the issue.",
#             "Write down what you were doing just before the issue started.",
#             "Report these details along with your maintenance request.",
#         ]

#     return {
#         "strategy": "rule_based_v1",
#         "issue_type": issue_type,
#         "steps": steps,
#         "title": title,
#         "description": desc,
#     }

# Step 3: Vendor scoring helper and issue_type -> service_type mapping

def vendor_utility_score(row) -> float:
    """
    Simple utility function for vendor selection:
      score = 2*rating + 1.5*speed_score - 1*price_band
    Higher is better.
    """
    return 2.0 * row["rating"] + 1.5 * row["speed_score"] - 1.0 * row["price_band"]


ISSUE_TO_SERVICE_TYPE = {
    "ELECTRICAL": "ELECTRICIAN",
    "APPLIANCE": "APPLIANCE_REPAIR",
    "PLUMBING": "PLUMBER",
    "GAS": "GAS_TECHNICIAN",
    "HVAC": "HVAC",
}
# Step 3: Vendor Selection Agent (internal)
def vendor_selection_agent(
    incident: Dict[str, Any],
    triage_output: Dict[str, Any],
    vendors: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Internal agent that:
      - infers required service_type from triage issue_type
      - filters vendors by that service_type (and optionally zip)
      - computes a utility score
      - picks the best vendor
      - returns vendor info + a natural language explanation
    """
    issue_type = triage_output.get("issue_type")
    service_type = ISSUE_TO_SERVICE_TYPE.get(issue_type, None) # type: ignore

    if service_type is None:
        return {
            "vendor_id": None,
            "service_type": None,
            "explanation": "No matching service_type for issue_type.",
        }

    prop = incident["property"]
    prop_zip = int(prop["zip"])

    # Filter vendors by service_type (and optionally zip; here we accept all matching type)
    candidates = vendors[vendors["service_type"] == service_type].copy()
    if candidates.empty:
        return {
            "vendor_id": None,
            "service_type": service_type,
            "explanation": f"No vendors found for service_type={service_type}.",
        }

    # Optionally prioritise vendors whose base zip matches property zip
    candidates["zip_match"] = (candidates["zip"].astype(int) == prop_zip).astype(int)
    candidates["utility_score"] = candidates.apply(vendor_utility_score, axis=1)

    # Sort: zip_match desc, then utility_score desc
    candidates_sorted = candidates.sort_values(
        by=["zip_match", "utility_score"], ascending=[False, False]
    )

    best = candidates_sorted.iloc[0]

    explanation = (
        f"Selected vendor {best['name']} ({best['vendor_id']}) for service_type={service_type} "
        f"because they have rating={best['rating']}, speed_score={best['speed_score']}, "
        f"and price_band={best['price_band']}."
    )

    return {
        "vendor_id": best["vendor_id"],
        "service_type": service_type,
        "name": best["name"],
        "utility_score": float(best["utility_score"]),
        "explanation": explanation,
    }

# Step 3: A2A-shaped stubs for Vendor Agent interactions

def vendor_a2a_request_quote(
    vendor_choice: Dict[str, Any],
    incident: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Simulate A2A call to external Vendor Agent: request_quote.
    We create a deterministic quote based on severity and vendor pricing.
    """
    vendor_id = vendor_choice["vendor_id"]
    vendor_row = vendors_df[vendors_df["vendor_id"] == vendor_id].iloc[0]

    gt = incident["ground_truth"]
    severity = gt["severity"]

    # Simple severity -> hours mapping
    if severity == "CRITICAL":
        est_hours = 2.0
    elif severity == "HIGH":
        est_hours = 1.5
    else:
        est_hours = 1.0

    base_fee = float(vendor_row["base_fee"])
    hourly_rate = float(vendor_row["hourly_rate"])
    parts_estimate = 30.0  # constant for now

    labor_cost = hourly_rate * est_hours
    total_estimate = base_fee + labor_cost + parts_estimate

    return {
        "type": "quote_response",
        "incident_id": incident["scenario_id"],
        "vendor_id": vendor_id,
        "quote_id": f"QUOTE-{incident['scenario_id']}-{vendor_id}",
        "estimate": {
            "currency": "USD",
            "base_fee": base_fee,
            "labor_rate_per_hour": hourly_rate,
            "estimated_hours": est_hours,
            "parts_estimate": parts_estimate,
            "total_estimate": total_estimate,
        },
        "valid_until": "2025-12-31T23:59:59Z",
        "conditions": [
            "Final amount may vary based on on-site assessment."
        ],
    }


def vendor_a2a_get_availability(
    vendor_choice: Dict[str, Any],
    quote: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Simulate A2A get_availability.
    Just returns two dummy slots.
    """
    return {
        "type": "availability_response",
        "quote_id": quote["quote_id"],
        "options": [
            {
                "slot_id": quote["quote_id"] + "-SLOT-1",
                "date": "2025-11-22",
                "from": "10:00",
                "to": "11:00",
            },
            {
                "slot_id": quote["quote_id"] + "-SLOT-2",
                "date": "2025-11-22",
                "from": "15:00",
                "to": "16:00",
            },
        ],
    }


def vendor_a2a_book_slot(
    vendor_choice: Dict[str, Any],
    quote: Dict[str, Any],
    slot: Dict[str, Any],
    tenant_contact: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Simulate A2A book_slot.
    """
    return {
        "type": "booking_confirmed",
        "quote_id": quote["quote_id"],
        "job_id": quote["quote_id"].replace("QUOTE", "JOB"),
        "slot": slot,
        "tenant_contact": tenant_contact,
    }


def vendor_a2a_job_status_update_stub(
    booking: Dict[str, Any],
    incident: Dict[str, Any],
    quote: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Simulate vendor job status update.
    final_amount is randomly set, but does not exceed the quoted total.
    Handles missing ground_truth gracefully.
    """
    status = "DONE"
    summary = "Work completed successfully (simulated)."

    # Get quoted total_estimate if available
    total_estimate = None
    if quote and "estimate" in quote and "total_estimate" in quote["estimate"]:
        total_estimate = quote["estimate"]["total_estimate"]
    else:
        # fallback: try ground_truth or default to 300
        gt = incident.get("ground_truth", {})
        total_estimate = gt.get("max_budget", 300)

    # Random final amount, not exceeding quote
    final_amount = round(random.uniform(0.8, 1.0) * float(total_estimate), 2)

    return {
        "type": "job_status_update",
        "job_id": booking.get("job_id"),
        "incident_id": incident.get("scenario_id"),
        "status": status,
        "summary": summary,
        "final_amount": final_amount,
    }

# Step 5: Payment agent (AP2-style: mandate + payment)
def payment_agent(
    incident: Dict[str, Any],
    vendor_choice: Dict[str, Any],
    quote: Dict[str, Any],
    job_update: Dict[str, Any],
) -> Dict[str, Any]:
    """
    AP2-style payment agent:
      - Creates a payment mandate for this vendor & incident
      - Validates final_amount against mandate max_amount
      - Checks job completion status
      - Simulates tenant confirmation
      - Executes payment if all conditions are met
      
    AP2 Protocol Flow:
      1. Mandate Creation: Authorization for payment up to max_amount
      2. Validation: Check amount, status, and confirmation
      3. Payment Execution: Settle payment if validated
    """
    scenario_id = incident["scenario_id"]
    gt = incident.get("ground_truth", {})

    # Handle missing ground_truth gracefully
    max_budget = float(gt.get("max_budget", 500.0))  # Default to $500 if missing
    vendor_id = vendor_choice["vendor_id"]
    final_amount = float(job_update["final_amount"])
    job_status = job_update["status"]

    # AP2 Step 1: Create payment mandate
    mandate = {
        "mandate_id": f"MANDATE-{scenario_id}-{vendor_id}",
        "subject": scenario_id,  # What the mandate is for
        "payee": vendor_id,      # Who gets paid
        "currency": "USD",
        "max_amount": max_budget,  # Maximum authorized amount
        "valid_until": "2025-12-31T23:59:59Z",
        "status": "ACTIVE"
    }

    # AP2 Step 2: Validate payment conditions
    # In production: get real tenant confirmation via UI/agent
    # For capstone: simulate confirmation when job is done
    tenant_confirms = (job_status == "DONE")

    # Check all AP2 payment conditions
    can_pay = (
        tenant_confirms                          # Tenant confirms work is done
        and job_status == "DONE"                # Job marked complete by vendor
        and final_amount <= mandate["max_amount"]  # Amount within mandate limit
    )

    # AP2 Step 3: Execute or reject payment
    if can_pay:
        payment = {
            "payment_id": f"PAY-{scenario_id}-{vendor_id}",
            "mandate_id": mandate["mandate_id"],
            "amount": final_amount,
            "currency": "USD",
            "payee": vendor_id,
            "status": "SETTLED",
            "settled_at": "2025-11-21T12:00:00Z"
        }
        return {
            "paid": True,
            "mandate": mandate,
            "payment": payment,
            "protocol": "AP2",
            "message": f"Payment of ${final_amount} settled to {vendor_id} via AP2 protocol"
        }
    else:
        # Payment rejected - document reasons
        reason = []
        if not tenant_confirms:
            reason.append("tenant_not_confirmed")
        if job_status != "DONE":
            reason.append(f"job_status_{job_status}")
        if final_amount > mandate["max_amount"]:
            reason.append("amount_exceeds_mandate")

        return {
            "paid": False,
            "mandate": mandate,
            "payment": None,
            "protocol": "AP2",
            "reason": reason,
            "message": f"Payment rejected: {', '.join(reason)}"
        }

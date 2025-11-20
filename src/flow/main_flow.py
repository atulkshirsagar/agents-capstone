from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from src.agents.maintenance_triage_agent import MaintenanceTriageAgent
from src.data.vendors import load_vendors_df
from src.utils.stubs import payment_agent, triage_agent_call, vendor_a2a_book_slot, vendor_a2a_get_availability, vendor_a2a_job_status_update_stub, vendor_a2a_request_quote, vendor_selection_agent

# You must provide these stubs or implementations:
# triage_agent_call, propose_self_help_steps, vendor_selection_agent,
# vendor_a2a_request_quote, vendor_a2a_get_availability, vendor_a2a_book_slot,
# vendor_a2a_job_status_update_stub, payment_agent, vendors_df

@dataclass
class LogsRecorder:
    def __init__(self, scenario_id):
        self.scenario_id = scenario_id
        self.triage = {}
        self.trace_id = None
        self.self_help: Dict[str, Any] = {}
        self.vendor_selection: Optional[Dict[str, Any]] = None
        self.quote: Optional[Dict[str, Any]] = None
        self.booking: Optional[Dict[str, Any]] = None
        self.job_update: Optional[Dict[str, Any]] = None
        self.payment: Optional[Dict[str, Any]] = None
        self.states = []
        self.messages = {"tenant": [], "landlord": []}
    def add_state(self, state):
        self.states.append(state)
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

async def run_scenario_through_agents(scenario: Dict[str, Any]) -> LogsRecorder:
    logs_rec = LogsRecorder(scenario_id=scenario["scenario_id"])
    tenant_input = scenario["tenant_input"]
    prop = scenario["property"]
    gt = scenario.get("ground_truth", {})  # Use empty dict if missing

    # 1) TRIAGE (Gemini via ADK) + rule-based hybrid
    adk_logs: Dict[str, Any] = {}
    adk_request = {
        "ticket_id": scenario["scenario_id"],
        "property_id": prop.get("property_id", "UNKNOWN"),
        "property_zip": prop.get("zip", "00000"),  # <-- Add this
        "title": tenant_input.get("title", ""),
        "description": tenant_input.get("description", ""),
        "priority": tenant_input.get("priority_hint", "MEDIUM"),
    }
    agent = MaintenanceTriageAgent()
    gemini_triage = await agent.triage_issue(adk_request, adk_logs)
    rules_triage = triage_agent_call(tenant_input, prop)
    triage_label = gemini_triage.get("triage_label", "VENDOR_REQUIRED")

    if triage_label == "SELF_HELP_OK":
        propose_self_help_flag = True
        must_escalate_immediately = False
    elif triage_label == "EMERGENCY":
        propose_self_help_flag = False
        must_escalate_immediately = True
    else:
        propose_self_help_flag = False
        must_escalate_immediately = True

    logs_rec.triage = {
        "issue_type": rules_triage.get("issue_type"),
        "severity": rules_triage.get("severity"),
        "propose_self_help": propose_self_help_flag,
        "must_escalate_immediately": must_escalate_immediately,
        "triage_label": triage_label,
        "explanation": gemini_triage.get("explanation"),
        "kb_article_id": gemini_triage.get("kb_article_id"),
        "kb_article_title": gemini_triage.get("kb_article_title"),
    }
    logs_rec.trace_id = adk_logs.get("adk_session_id")
    logs_rec.add_state("TRIAGED")
    logs_rec.messages["tenant"].append(
        f"We've received your request: '{tenant_input['title']}'. We are analyzing the issue."
    )

    # 2) SELF-HELP path (Gemini steps with fallback)
    if propose_self_help_flag and not must_escalate_immediately:
        logs_rec.add_state("SELF_HELP_PROPOSED")
        gemini_steps = gemini_triage.get("self_help_steps") or []
        if gemini_steps:
            self_help_plan = {
                "strategy": "gemini_v1",
                "issue_type": rules_triage.get("issue_type"),
                "steps": gemini_steps,
                "kb_article_id": gemini_triage.get("kb_article_id"),
                "kb_article_title": gemini_triage.get("kb_article_title"),
                "explanation": gemini_triage.get("explanation"),
            }
        
        logs_rec.self_help = self_help_plan
        logs_rec.messages["tenant"].append(
            "Here are some safe steps you can try while we monitor the issue."
        )
        # Use .get with default False
        if gt.get("self_help_should_succeed", False):
            logs_rec.add_state("SELF_HELP_SUCCEEDED")
            logs_rec.messages["tenant"].append(
                "Glad to hear the issue is resolved with those steps. We are closing the ticket."
            )
            logs_rec.add_state("CLOSED")
            return logs_rec
        else:
            logs_rec.add_state("SELF_HELP_FAILED")
            logs_rec.messages["tenant"].append(
                "Looks like the steps did not fully resolve the issue. We will arrange a vendor visit."
            )

    # 3) ESCALATION to vendor path
    logs_rec.add_state("ESCALATED")
    # Use .get with default None
    if gt.get("expected_vendor_service_type", None) is None:
        logs_rec.messages["tenant"].append(
            "The issue is minor and will be monitored. No vendor visit is required."
        )
        return logs_rec

    # 3a) Vendor selection is now handled by the agent's triage_issue method
    vendor_choice = gemini_triage.get("vendor_selection")
    logs_rec.vendor_selection = vendor_choice
    if not vendor_choice or vendor_choice.get("vendor_id") is None:
        logs_rec.messages["landlord"].append(
            "No suitable vendor found for this issue type and location."
        )
        return logs_rec
    logs_rec.add_state("VENDOR_SELECTED")
    logs_rec.messages["landlord"].append(
        f"Selected vendor {vendor_choice['vendor_name']} ({vendor_choice['vendor_id']}) "
        f"for property {prop['property_id']} and issue '{tenant_input['title']}'.",
    )
    logs_rec.messages["tenant"].append(
        f"We have selected vendor {vendor_choice['vendor_name']} to handle your issue."
    )

    # 3b) Request quote via A2A
    quote = vendor_a2a_request_quote(vendor_choice, scenario)
    logs_rec.quote = quote
    logs_rec.add_state("QUOTE_RECEIVED")
    total_estimate = quote["estimate"]["total_estimate"]
    if total_estimate <= gt["max_budget"]:
        logs_rec.messages["landlord"].append(
            f"Quote of ${total_estimate:.2f} from {vendor_choice['vendor_name']} is within budget "
            f"(max ${gt['max_budget']:.2f}) and has been auto-approved for evaluation."
        )
        logs_rec.add_state("QUOTE_APPROVED")
    else:
        logs_rec.messages["landlord"].append(
            f"Quote of ${total_estimate:.2f} from {vendor_choice['vendor_name']} exceeds budget "
            f"(max ${gt['max_budget']:.2f}). It has been rejected."
        )
        return logs_rec

    # 3c) Availability + booking via A2A
    availability = vendor_a2a_get_availability(vendor_choice, quote)
    chosen_slot = availability["options"][0]
    booking = vendor_a2a_book_slot(
        vendor_choice,
        quote,
        chosen_slot,
        tenant_contact={"name": "Test Tenant", "phone": "000-000-0000"},
    )
    logs_rec.booking = booking
    logs_rec.add_state("SCHEDULED")
    logs_rec.messages["tenant"].append(
        f"Your appointment is scheduled on {chosen_slot['date']} "
        f"from {chosen_slot['from']} to {chosen_slot['to']}."
    )

    # 3d) Job status update via A2A
    job_update = vendor_a2a_job_status_update_stub(booking, scenario)
    job_update["final_amount"] = total_estimate
    logs_rec.job_update = job_update
    if job_update["status"] == "DONE":
        logs_rec.add_state("WORK_DONE")
        logs_rec.messages["tenant"].append(
            "The vendor has marked the work as completed. Please confirm if everything looks good."
        )
    else:
        logs_rec.add_state("FAILED")
        logs_rec.messages["landlord"].append(
            f"Vendor reported job status {job_update['status']} for {scenario['scenario_id']}."
        )
        return logs_rec

    # 4) PAYMENT via Payment Agent
    pay_result = payment_agent(scenario, vendor_choice, quote, job_update)
    logs_rec.payment = pay_result
    if pay_result.get("paid", False):
        logs_rec.add_state("PAID")
        amt = pay_result["payment"]["amount"]
        logs_rec.messages["landlord"].append(
            f"Payment of ${amt:.2f} has been processed to vendor {vendor_choice['vendor_name']}."
        )
        logs_rec.messages["tenant"].append(
            "Payment to the vendor has been processed by your landlord. Thank you!"
        )
    else:
        logs_rec.messages["landlord"].append(
            f"Payment was NOT processed automatically due to: {pay_result.get('reason', [])}."
        )

    # 5) Close incident
    logs_rec.add_state("CLOSED")
    return logs_rec
import pytest
from dotenv import load_dotenv
load_dotenv()

from src.data.golden_incidents import load_golden_incidents
from src.data.vendors import vendors_df
from src.utils.eval import score_triage, score_state_machine, score_self_help, score_vendor, score_payment, score_communications
from src.flow.main_flow import run_scenario_through_agents
from typing import Dict, List

@pytest.mark.asyncio
async def test_eval_single_golden():
    scenario = load_golden_incidents()[0]
    logs_rec = await run_scenario_through_agents(scenario)
    gt = scenario["ground_truth"]

    triage_score = score_triage(logs_rec.triage, gt)
    state_score = score_state_machine(logs_rec.states, gt)
    self_help_score = score_self_help(logs_rec.self_help, gt)
    vendor_score = score_vendor(logs_rec.vendor_selection, gt, vendors_df)
    payment_score = score_payment(logs_rec.payment, gt)
    comm_score = score_communications(logs_rec.messages, gt)
    total_score = triage_score + state_score + self_help_score + vendor_score + payment_score + comm_score

    print(f"Scenario: {scenario['scenario_id']}")
    print(f"Triage Score: {triage_score}")
    print(f"State Machine Score: {state_score}")
    print(f"Self-Help Score: {self_help_score}")
    print(f"Vendor Score: {vendor_score}")
    print(f"Payment Score: {payment_score}")
    print(f"Communication Score: {comm_score}")
    print(f"Total Score: {total_score}")

    # Basic assertion: total score should be non-negative
    assert total_score >= 0
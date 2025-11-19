import pytest
import asyncio
from dotenv import load_dotenv
load_dotenv()

from src.data.golden_incidents import load_golden_incidents
from src.flow.main_flow import run_scenario_through_agents

@pytest.mark.asyncio
async def test_run_scenario_single_golden():
    scenario = load_golden_incidents()[0]  # Pick only the first golden record
    logs_rec = await run_scenario_through_agents(scenario)
    gt = scenario["ground_truth"]

    # Check that the flow states match expected sequence
    assert logs_rec.states == gt["expected_state_sequence"], (
        f"States mismatch for scenario {scenario['scenario_id']}: "
        f"expected {gt['expected_state_sequence']}, got {logs_rec.states}"
    )

    # Check triage label if present
    if "triage_label" in logs_rec.triage:
        assert logs_rec.triage["triage_label"] in ["SELF_HELP_OK", "VENDOR_REQUIRED", "EMERGENCY"]

    # Optionally check vendor selection if escalation expected
    if gt.get("expected_vendor_service_type"):
        assert logs_rec.vendor_selection is not None
        assert logs_rec.vendor_selection.get("service_type") == gt["expected_vendor_service_type"]
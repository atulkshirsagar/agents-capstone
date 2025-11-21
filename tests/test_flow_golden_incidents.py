import pytest
import asyncio
import random
from dotenv import load_dotenv
load_dotenv()

from src.data.golden_incidents import load_golden_incidents
from src.flow.main_flow import run_scenario_through_agents

@pytest.mark.asyncio
async def test_run_scenario_two_random_golden():
    scenarios = load_golden_incidents()
    selected = random.sample(scenarios, 2)
    print(f"Selected scenarios: {[s['scenario_id'] for s in selected]}")
    for scenario in selected:
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

        # Check payment status if expected in flow
        if "PAID" in gt["expected_state_sequence"]:
            assert logs_rec.payment is not None
            assert logs_rec.payment.get("paid") is True

        # Ensure incident is closed
        assert logs_rec.states[-1] == "CLOSED", f"Scenario {scenario['scenario_id']} did not close properly."

        await asyncio.sleep(2)

@pytest.mark.asyncio
async def test_run_scenario_first_golden():
    scenarios = load_golden_incidents()
    selected = [scenarios[1]]  # Select only one incident
    print(f"Selected scenario: {selected[0]['scenario_id']}")
    for scenario in selected:
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

        # Check payment status if expected in flow
        if "PAID" in gt["expected_state_sequence"]:
            assert logs_rec.payment is not None
            assert logs_rec.payment.get("paid") is True

        # Ensure incident is closed
        assert logs_rec.states[-1] == "CLOSED", f"Scenario {scenario['scenario_id']} did not close properly."

@pytest.mark.asyncio
async def test_run_scenario_all_golden():
    scenarios = load_golden_incidents()
    print(f"Testing all golden scenarios: {[s['scenario_id'] for s in scenarios]}")
    for scenario in scenarios:
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

        # Check payment status if expected in flow
        if "PAID" in gt["expected_state_sequence"]:
            assert logs_rec.payment is not None
            assert logs_rec.payment.get("paid") is True

        # Ensure incident is closed
        assert logs_rec.states[-1] == "CLOSED", f"Scenario {scenario['scenario_id']} did not close properly."
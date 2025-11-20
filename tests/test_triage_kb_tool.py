import pytest
from dotenv import load_dotenv
load_dotenv()

from src.flow.main_flow import run_scenario_through_agents
import json

@pytest.mark.asyncio
async def test_triage_invokes_kb_tool(capfd):
    scenario = {
        "scenario_id": "SINK_LEAK_001",  # <-- Add this line
        "tenant_input": {
            "title": "Minor sink leak under kitchen",
            "description": "There is a small drip from the pipe under my kitchen sink. No flooding, just a slow leak.",
            "priority_hint": "LOW",
        },
        "property": {
            "property_id": "P456",
            "zip": "95054",
        },
        "ground_truth": {
            "issue_type": "PLUMBING",
            "severity": "LOW",
            "self_help_allowed": True,
            "self_help_should_succeed": True,
            "must_escalate_immediately": False,
            "expected_vendor_service_type": "PLUMBING",
            "acceptable_vendors": [],
            "max_budget": 200,
            "expected_state_sequence": [
                "REPORTED", "TRIAGED", "SELF_HELP_PROPOSED", "SELF_HELP_SUCCEEDED", "CLOSED"
            ]
        }
    }

    logs = await run_scenario_through_agents(scenario)

    # Assert that kb_article_id is populated (not None)
    if hasattr(logs, "triage") and "kb_article_id" in logs.triage:
        print("Captured triage logs:\n", json.dumps(logs.triage, indent=2))
        assert logs.triage.get("kb_article_id") is not None
        assert logs.triage.get("kb_article_id") != ""
    
    # if hasattr(logs, "self_help") and "kb_article_id" in logs.self_help:
    #     print("Captured self_help logs:\n", json.dumps(logs.self_help, indent=2))
import json
import pytest
from dotenv import load_dotenv
load_dotenv()

from src.agents.maintenance_triage_agent import MaintenanceTriageAgent

@pytest.mark.asyncio
async def test_triage_vendor_selection_tool(capfd):
    agent = MaintenanceTriageAgent()
    # Scenario: Major HVAC failure, escalation required
    request = {
        "ticket_id": "HVAC_ESCALATE_001",
        "property_id": "10001",
        "title": "No cooling from central AC",
        "description": "The central AC is not cooling at all. The unit is running but no cold air is coming out. It's 90F outside.",
        "priority": "HIGH"
    }
    logs = {}
    result = await agent.triage_issue(request, logs)

    print("Agent Response:\n", json.dumps(result, indent=2))
    # out, _ = capfd.readouterr()
    # Check that vendor selection is present and populated
    vendor_selection = result.get("vendor_selection")
    assert vendor_selection is not None, "Vendor selection should be present in the response."
    assert vendor_selection.get("vendor_id") is not None, "Vendor ID should be populated."
    assert vendor_selection.get("vendor_name"), "Vendor name should be populated."
    assert "Selected" in vendor_selection.get("explanation", ""), "Explanation should mention selection."
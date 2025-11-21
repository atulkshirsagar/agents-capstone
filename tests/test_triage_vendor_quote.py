import json
import pytest
from dotenv import load_dotenv
load_dotenv()

from src.agents.maintenance_triage_agent import MaintenanceTriageAgent

def extract_json_from_response(response: dict) -> dict:
    """Extract JSON object from model response, handling markdown code blocks."""
    if "response" in response and isinstance(response["response"], str):
        text = response["response"].strip()
        # Remove markdown code block if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        try:
            return json.loads(text)
        except Exception:
            pass
    return response

@pytest.mark.asyncio
async def test_triage_vendor_quote_collaboration(capfd):
    agent = MaintenanceTriageAgent()
    # Scenario: Request a vendor quote for a major HVAC issue
    service_type = "HVAC"
    issue_description = "AC not cooling at all, outside temperature is 90F."
    property_zip = "10001"
    severity = "HIGH"
    logs = {}

    result = await agent.request_vendor_quote(
        service_type=service_type,
        issue_description=issue_description,
        property_zip=property_zip,
        severity=severity,
        logs=logs
    )

    parsed = extract_json_from_response(result)
    print("Vendor Quote Response:\n", json.dumps(parsed, indent=2))
    # Check that quote fields are present and populated
    assert parsed.get("quote_id"), "Quote ID should be present."
    assert parsed.get("service_type") == service_type, "Service type should match."
    assert "estimate" in parsed and "total_estimate" in parsed["estimate"], "Estimate should include total_estimate."
    assert parsed.get("valid_until"), "Quote validity should be present."
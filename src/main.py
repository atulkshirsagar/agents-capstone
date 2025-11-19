"""Main entry point for the maintenance triage application."""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from src.flow.main_flow import run_scenario_through_agents


async def main():
    scenario = {
        "scenario_id": "T001",
        "tenant_input": {
            "title": "AC not cooling",
            "description": "The air conditioner in my apartment is running but not cooling the room properly. It's been 3 days.",
            "priority_hint": "high"
        },
        "property": {
            "property_id": "P123"
        },
        "ground_truth": {
            "self_help_should_succeed": False,
            "expected_vendor_service_type": "hvac",
            "max_budget": 500.0
        }
    }

    logs_rec = await run_scenario_through_agents(scenario)

    print("\n--- Scenario Flow States ---")
    print(logs_rec.states)
    print("\n--- Triage Info ---")
    print(logs_rec.triage)
    print("\n--- Tenant Messages ---")
    for msg in logs_rec.messages["tenant"]:
        print(msg)


if __name__ == "__main__":
    asyncio.run(main())
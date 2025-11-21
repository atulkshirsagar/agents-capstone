"""Vendor agent wrapper for A2A communication."""

from typing import Dict, Any
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

class VendorAgent:
    """Client wrapper for remote vendor agent via A2A."""
    
    def __init__(self, vendor_url: str = "http://localhost:8001"):
        """
        Initialize vendor agent client.
        
        Args:
            vendor_url: Base URL of vendor agent server
        """
        self.vendor_url = vendor_url
        self.remote_agent = RemoteA2aAgent(
            name="vendor_service_agent",
            description="Remote vendor agent for maintenance services",
            agent_card=f"{vendor_url}{AGENT_CARD_WELL_KNOWN_PATH}"
        )
        print(f"✅ Vendor Agent client initialized")
        print(f"   Vendor URL: {vendor_url}")
        print(f"   Agent card: {vendor_url}{AGENT_CARD_WELL_KNOWN_PATH}")
    
    async def request_quote(self, vendor_choice: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Request a quote from vendor via A2A."""
        # This will be called by maintenance triage agent via A2A
        return await self.remote_agent.run({
            "action": "request_quote",
            "service_type": vendor_choice.get("service_type", "HVAC"),
            "issue_description": scenario["tenant_input"]["description"],
            "property_zip": scenario["property"]["zip"],
            "severity": scenario.get("ground_truth", {}).get("severity", "MEDIUM")
        })
    
    async def get_availability(self, vendor_choice: Dict[str, Any], quote: Dict[str, Any]) -> Dict[str, Any]:
        """Get availability from vendor via A2A."""
        return await self.remote_agent.run({
            "action": "get_availability",
            "service_type": vendor_choice.get("service_type", "HVAC"),
            "quote_id": quote.get("quote_id", "")
        })
    
    async def book_slot(
        self,
        vendor_choice: Dict[str, Any],
        quote: Dict[str, Any],
        slot: Dict[str, Any],
        tenant_contact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Book a slot with vendor via A2A."""
        return await self.remote_agent.run({
            "action": "book_slot",
            "quote_id": quote.get("quote_id", ""),
            "slot_id": slot.get("slot_id", ""),
            "tenant_name": tenant_contact.get("name", ""),
            "tenant_phone": tenant_contact.get("phone", "")
        })
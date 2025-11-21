"""Maintenance triage agent using Google ADK and Gemini."""
from typing import Dict, Any
from google.adk.sessions import BaseSessionService
from google.adk.runners import Runner
from src.adk_agents.maintenance_triage.agent import root_agent as TRIAGE_ADK_AGENT
from src.utils.json_utils import extract_json_from_llm_output
from src.utils.session_manager import build_session_service, run_session
from src.prompts.system_prompts import (
    format_triage_request,
    format_vendor_quote_request,
    format_vendor_availability_request,
    format_vendor_booking_request
)
from src.utils.constants import APP_NAME
import json


class MaintenanceTriageAgent:
    def __init__(self):
        """Initialize the maintenance triage agent."""
        # Use the ADK agent from adk_agents
        self.agent = TRIAGE_ADK_AGENT
        # Shared session service (same DB as adk web)
        self.session_service: BaseSessionService = build_session_service()
        self.runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        print(f"✅ Maintenance Triage Agent initialized!")
        print(f"   - Application: {APP_NAME}")
        print(f"   - Model: {self.agent.model.model}")
        print(f"   - Session Service: {self.runner.session_service.__class__.__name__}")
        print(f"   - Sub-agents: {len(self.agent.sub_agents)} (Vendor Agent via A2A)")

    async def triage_issue(
        self,
        request: Dict[str, Any],
        logs: Dict[str, Any],
    ) -> Dict[str, Any]:
        property_id = request.get("property_id", "unknown")
        property_zip = request.get("property_zip", "unknown")
        priority = request.get("priority", "medium")
        title = request.get("title", "")
        description = request.get("description", "")

        query = format_triage_request(
            property_id=property_id,
            priority=priority,
            title=title,
            description=description,
            property_zip=property_zip
        )

        response = await run_session(
            runner_instance=self.runner,
            session_service=self.runner.session_service,
            user_queries=[query],
            session_name="triage_session",
            logs=logs,
        )

        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            response_text = response.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            triage_result = json.loads(response_text.strip())
            return triage_result
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse triage response as JSON: {e}")
            print(f"Raw response: {response}")
            return {
                "triage_label": "VENDOR_REQUIRED",
                "explanation": "Failed to parse triage response",
                "self_help_steps": [],
                "kb_article_id": None,
                "kb_article_title": None,
                "vendor_selection": None
            }
    
    async def request_vendor_quote(
        self,
        service_type: str,
        issue_description: str,
        property_zip: str,
        severity: str,
        logs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request a quote from vendor via A2A sub-agent."""
        query = format_vendor_quote_request(
            service_type=service_type,
            issue_description=issue_description,
            property_zip=property_zip,
            severity=severity
        )
        
        response = await run_session(
            runner_instance=self.runner,
            session_service=self.runner.session_service,
            user_queries=[query],
            session_name="vendor_quote_session",
            logs=logs,
        )
        
        # Parse response
        try:
            return extract_json_from_llm_output(response.strip())
            # return json.loads(response.strip())
        except json.JSONDecodeError:
            return {"response": response}
    
    async def check_vendor_availability(
        self,
        service_type: str,
        quote_id: str,
        logs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check vendor availability via A2A sub-agent."""
        query = format_vendor_availability_request(
            service_type=service_type,
            quote_id=quote_id
        )
        
        response = await run_session(
            runner_instance=self.runner,
            session_service=self.runner.session_service,
            user_queries=[query],
            session_name="vendor_availability_session",
            logs=logs,
        )
        
        try:
            return extract_json_from_llm_output(response.strip())
        except json.JSONDecodeError:
            return {"response": response}
    
    async def book_vendor_slot(
        self,
        quote_id: str,
        slot_id: str,
        tenant_name: str,
        tenant_phone: str,
        special_instructions: str,
        logs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Book a vendor slot via A2A sub-agent."""
        query = format_vendor_booking_request(
            quote_id=quote_id,
            slot_id=slot_id,
            tenant_name=tenant_name,
            tenant_phone=tenant_phone,
            special_instructions=special_instructions
        )
        
        response = await run_session(
            runner_instance=self.runner,
            session_service=self.runner.session_service,
            user_queries=[query],
            session_name="vendor_booking_session",
            logs=logs,
        )
        
        try:
            return extract_json_from_llm_output(response.strip())
        except json.JSONDecodeError:
            return {"response": response}
"""Maintenance triage agent using Google ADK and Gemini."""

import json
from typing import Dict, Any
from google.adk.sessions import BaseSessionService
from google.adk.runners import Runner
from src.prompts.system_prompts import format_triage_request
from src.utils.json_utils import extract_json_from_llm_output

from ..utils.session_manager import run_session, build_session_service
from ..utils.constants import APP_NAME, MODEL_NAME, SESSION_ID
from ..adk_agents.maintenance_triage.agent import root_agent as TRIAGE_ADK_AGENT


class MaintenanceTriageAgent:
    """Agent for triaging maintenance requests."""
    
    def __init__(self):
        """Initialize the maintenance triage agent."""
        # Use the ADK agent from adk_agents
        self.agent = TRIAGE_ADK_AGENT

        # Shared session service (same DB as adk web)
        self.session_service: BaseSessionService = build_session_service()

        # Create Runner that uses that service
        self.runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        
        print("✅ Maintenance Triage Agent initialized!")
        print(f"   - Application: {APP_NAME}")
        print(f"   - Model: {MODEL_NAME}")
        print(f"   - Session Service: {self.session_service.__class__.__name__}")
    
    async def triage_issue(
        self,
        request: Dict[str, Any],
        logs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Triage a maintenance issue and suggest self-help steps.
        
        Args:
            request: Maintenance request dictionary with keys:
                - ticket_id: Unique ticket identifier
                - property_id: Property identifier
                - title: Issue title
                - description: Detailed description
                - priority: Current priority level
            logs: Dictionary to store execution logs
            
        Returns:
            Triage result with classification and recommendations
        """
        title = request.get("title", "")
        desc = request.get("description", "")
        priority = request.get("priority", "medium")
        property_id = request.get("property_id", "unknown")
        property_zip = request.get("property_zip", "unknown")
        
        # Format the user prompt
        user_prompt = format_triage_request(
            property_id=property_id,
            priority=priority,
            title=title,
            description=desc,
            property_zip=property_zip
        )
        
        # Run the session and get response
        final_text = await run_session(
            runner_instance=self.runner,
            session_service=self.session_service,
            user_queries=[user_prompt],
            session_name=SESSION_ID,
            logs=logs,
        )
        
        # Parse response with fallback
        parsed = {
            "triage_label": "VENDOR_REQUIRED",
            "explanation": "Default decision because parsing failed.",
            "self_help_steps": [],
            "kb_article_id": None,
            "kb_article_title": None,
            "raw_response": final_text,
        }
        
        if final_text:
            try:
                candidate = extract_json_from_llm_output(final_text)
                parsed.update(candidate)
            except json.JSONDecodeError:
                logs.setdefault("json_parse_errors", []).append(final_text)
        
        # Log triage decision
        logs.setdefault("triage_decisions", []).append(
            {
                "request_id": request.get("ticket_id"),
                "triage_label": parsed["triage_label"],
                "self_help_steps_count": len(parsed.get("self_help_steps", [])),
            }
        )
        
        return parsed
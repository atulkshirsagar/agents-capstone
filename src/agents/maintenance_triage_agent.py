"""Maintenance triage agent using Google ADK and Gemini."""

import json
from typing import Dict, Any
from google.adk.agents import Agent as LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from ..tools.kb_tools import lookup_troubleshooting_article
from ..prompts.system_prompts import MAINTENANCE_TRIAGE_PROMPT, format_triage_request
from ..utils.constants import APP_NAME, MODEL_NAME, SESSION_ID
from ..utils.retry_config import retry_config
from ..utils.session_manager import run_session
from ..utils.json_utils import extract_json_from_llm_output


class MaintenanceTriageAgent:
    """Agent for triaging maintenance requests."""
    
    def __init__(self):
        """Initialize the maintenance triage agent."""
        # Create the LLM Agent
        self.agent = LlmAgent(
            name="maintenance_triage_agent",
            model=Gemini(model=MODEL_NAME, retry_options=retry_config),
            description=(
                "Triage and suggest self-help steps for rental maintenance issues such as leaks, "
                "appliance failures, or HVAC problems."
            ),
            instruction=MAINTENANCE_TRIAGE_PROMPT,
            tools=[lookup_troubleshooting_article],
        )
        
        # Set up Session Management
        self.session_service = InMemorySessionService()
        
        # Create the Runner
        self.runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service
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
        
        # Format the user prompt
        user_prompt = format_triage_request(
            property_id=property_id,
            priority=priority,
            title=title,
            description=desc
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
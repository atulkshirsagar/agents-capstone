"""Vendor agent for A2A communication."""

from google.adk.agents.llm_agent import Agent
from google.adk.models.google_llm import Gemini
from src.prompts.vendor_prompts import VENDOR_AGENT_PROMPT
from src.tools.vendor_service_tools import request_quote, get_availability, book_slot
from src.utils.retry_config import retry_config
from src.utils.constants import MODEL_NAME

root_agent = Agent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="vendor_service_agent",
    description=(
        "Professional maintenance vendor service agent that handles quotes, "
        "availability checks, and appointment booking for HVAC, plumbing, "
        "electrical, and other maintenance services."
    ),
    instruction=VENDOR_AGENT_PROMPT,
    tools=[request_quote, get_availability, book_slot],
)
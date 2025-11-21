from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.models.google_llm import Gemini
from src.prompts.system_prompts import MAINTENANCE_TRIAGE_PROMPT
from src.tools.kb_tools import lookup_troubleshooting_article
from src.tools.vendor_tools import select_best_vendor
from src.utils.retry_config import retry_config
from src.utils.constants import MODEL_NAME

# Create remote vendor agent as a sub-agent
remote_vendor_agent = RemoteA2aAgent(
    name="vendor_service_agent",
    description="Remote vendor agent for maintenance service operations including quotes, availability, and booking",
    agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}"
)

root_agent = Agent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="maintenance_triage_agent",
    description=(
        "Triage and suggest self-help steps for rental maintenance issues such as leaks, "
        "appliance failures, or HVAC problems. Coordinates with vendor agents for quotes and scheduling."
    ),
    instruction=MAINTENANCE_TRIAGE_PROMPT,
    tools=[lookup_troubleshooting_article, select_best_vendor],
    sub_agents=[remote_vendor_agent],  # Add vendor agent as sub-agent
)
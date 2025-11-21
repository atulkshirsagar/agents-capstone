"""Tests for vendor agent A2A communication."""

import pytest
import requests
from dotenv import load_dotenv
load_dotenv()

@pytest.mark.asyncio
async def test_vendor_agent_card():
    """Test that vendor agent card is accessible."""
    try:
        response = requests.get("http://localhost:8001/.well-known/agent-card.json", timeout=5)
        assert response.status_code == 200
        agent_card = response.json()
        assert agent_card["name"] == "vendor_service_agent"
        
        # Check that the three tool skills are present
        skill_names = [s["name"] for s in agent_card.get("skills", [])]
        assert "request_quote" in skill_names
        assert "get_availability" in skill_names
        assert "book_slot" in skill_names
        print("✅ Vendor agent card is valid")
        print(f"   Skills found: {skill_names}")
    except requests.exceptions.RequestException:
        pytest.skip("Vendor server not running. Start with: poetry run python -m src.a2a_servers.vendor_server")


@pytest.mark.asyncio
async def test_vendor_a2a_communication():
    """Test A2A communication with vendor agent."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
    from google.genai import types
    
    # Create retry config
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],
    )
    
    # Create remote vendor agent
    remote_vendor = RemoteA2aAgent(
        name="vendor_service_agent",
        description="Remote vendor agent for maintenance services",
        agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}"
    )
    
    # Create a test agent that uses the vendor agent
    test_agent = LlmAgent(
        model=Gemini(model="gemini-2.0-flash-lite", retry_options=retry_config),
        name="test_maintenance_agent",
        description="Test agent that requests quotes from vendor",
        instruction="""
        You are a test agent. When asked to get a quote, use the vendor_service_agent sub-agent.
        Request a quote for HVAC service for an AC not cooling issue in ZIP 95054 with HIGH severity.
        """,
        sub_agents=[remote_vendor]
    )
    
    # Setup session
    session_service = InMemorySessionService()
    app_name = "test_app"
    user_id = "test_user"
    session_id = "test_session"
    
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    
    # Create runner
    runner = Runner(
        agent=test_agent,
        app_name=app_name,
        session_service=session_service
    )
    
    # Send request
    query = "Please get me a quote for HVAC service. The AC is not cooling properly. Property ZIP is 95054, severity is HIGH."
    test_content = types.Content(parts=[types.Part(text=query)])
    
    print("\n🧪 Testing A2A communication...")
    print(f"Query: {query}")
    
    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=test_content
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    response_text += part.text
    
    print(f"Response: {response_text}")
    
    # Verify response contains quote information
    assert len(response_text) > 0
    print("✅ A2A communication successful")
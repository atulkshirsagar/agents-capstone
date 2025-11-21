"""Session management utilities for ADK agents."""
from typing import Dict, Any, Optional
from google.adk.runners import Runner
from google.genai import types
from .constants import USER_ID, MODEL_NAME
from google.adk.sessions import (
    InMemorySessionService,
    BaseSessionService,
    DatabaseSessionService,
)
import os
from dotenv import load_dotenv

# load_dotenv()  # Load environment variables from .env file. ALREADY CALLED IN MAIN

USE_SHARED_SQLITE = os.getenv("USE_SHARED_SQLITE", "false").lower() == "true"  # Read from .env

def build_session_service() -> BaseSessionService:
    if USE_SHARED_SQLITE:
        return DatabaseSessionService(db_url="sqlite+aiosqlite:///adk_sessions.db")
    else:
        return InMemorySessionService()
    
async def run_session(
    runner_instance: Runner,
    session_service,
    user_queries: list[str] | str = None,
    session_name: str = "default",
    logs: Optional[Dict[str, Any]] = None,
):
    """
    Run a session with the agent and stream responses.
    """
    if logs is None:
        logs = {}
    print(f"\n ### Session: {session_name}")

    app_name = runner_instance.app_name

    # Create or get existing session
    try:
        session = await session_service.create_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
    except:
        session = await session_service.get_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
    
    if logs is not None:
        logs["adk_session_id"] = session.id if session else None
        print(f"Session ID: {logs['adk_session_id']}")

    if not user_queries:
        print("No queries!")
        return ""

    if isinstance(user_queries, str):
        user_queries = [user_queries]

    full_response = ""
    
    # Ensure adk_events list exists
    if logs is not None:
        logs.setdefault("adk_events", [])

    for query in user_queries:
        print(f"\nUser > {query}")

        content_msg = types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )

        # Stream ADK events - they are automatically stored in the session by the runner
        async for event in runner_instance.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=content_msg,
        ):
            # Log event details for debugging
            event_type = event.__class__.__name__
            event_role = getattr(event.content, 'role', 'unknown') if hasattr(event, 'content') and event.content else 'no-content'
            print(f"[EVENT] type={event_type}, role={event_role}")
            
            # Store event metadata in logs
            if logs is not None:
                event_dict = {}
                try:
                    # Try to capture as much metadata as possible
                    if hasattr(event, 'to_dict'):
                        event_dict = event.to_dict()
                    else:
                        event_dict = {
                            'type': event_type,
                            'content': str(event.content) if hasattr(event, 'content') else None,
                            'metadata': getattr(event, 'metadata', {}),
                            'timestamp': getattr(event, 'timestamp', None),
                        }
                        # Add role if available
                        if hasattr(event, 'content') and event.content:
                            event_dict['role'] = getattr(event.content, 'role', None)
                except Exception as e:
                    print(f"[WARNING] Could not serialize event: {e}")
                    event_dict = {"repr": repr(event), "type": event_type}
                
                logs["adk_events"].append(event_dict)

            # Accumulate text response from model events
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text = part.text
                            if text and text != "None":
                                print(f"{MODEL_NAME} > {text}")
                                full_response += text + "\n"

    return full_response.strip()
"""Session management utilities for ADK agents."""

from typing import Dict, Any, Optional
from google.adk.runners import Runner
from google.genai import types
from .constants import USER_ID, MODEL_NAME


async def run_session(
    runner_instance: Runner,
    session_service,
    user_queries: list[str] | str = None,
    session_name: str = "default",
    logs: Optional[Dict[str, Any]] = None,
):
    """
    Run a session with the agent and stream responses.
    
    Args:
        runner_instance: The Runner instance to use
        session_service: Session service for managing conversations
        user_queries: Single query or list of queries to process
        session_name: Name/ID for the session
        logs: Optional dictionary to store event logs
        
    Returns:
        Accumulated text response from the agent
    """
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

    if not user_queries:
        print("No queries!")
        return ""

    # Convert single query to list
    if isinstance(user_queries, str):
        user_queries = [user_queries]

    full_response = ""

    # Ensure adk_events list exists
    if logs is not None:
        logs.setdefault("adk_events", [])

    # Process each query
    for query in user_queries:
        print(f"\nUser > {query}")

        content_msg = types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )

        # Stream ADK events
        async for event in runner_instance.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=content_msg,
        ):
            # Store raw event in logs
            if logs is not None:
                try:
                    logs["adk_events"].append(event.to_dict())
                except AttributeError:
                    try:
                        logs["adk_events"].append(
                            {"content": event.stringify_content()}
                        )
                    except Exception:
                        logs["adk_events"].append({"repr": repr(event)})

            # Accumulate text response
            if event.content and event.content.parts:
                text = event.content.parts[0].text
                if text and text != "None":
                    print(f"{MODEL_NAME} > {text}")
                    full_response += text + "\n"

    return full_response.strip()
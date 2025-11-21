"""Vendor agent A2A server."""

import os
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from src.adk_agents.vendor.agent import root_agent as vendor_root_agent

# Create A2A application
app = to_a2a(vendor_root_agent, port=8001)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
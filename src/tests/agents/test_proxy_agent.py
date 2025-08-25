"""
Integration tests for FoundryAgentTemplate functionality.
Tests Bing search, RAG, MCP tools, and Code Interpreter capabilities.
"""
# pylint: disable=E0401, E0611, C0413

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

# Add the backend path to sys.path so we can import v3 modules
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Now import from the v3 package
from v3.magentic_agents.proxy_agent import (DummyAgentThread, ProxyAgent,
                                            ProxyAgentResponseItem)


@pytest.mark.asyncio
async def test_proxy_agent(monkeypatch):
    """Test the proxy agent."""
    # Mock the input function to simulate user input
    monkeypatch.setattr("builtins.input", lambda _: "Jane Doe")

    agent = ProxyAgent()
    test_messages = [
        "More information needed.  What is the name of the employee?"
    ]
    
    for message in test_messages:
        async for response in agent.invoke(message):
            assert "Human clarification: Jane Doe" in response.message.content, \
            f"Unexpected response: {response.message.content}"

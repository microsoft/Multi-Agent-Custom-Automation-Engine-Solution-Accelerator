"""Unit tests for backend.orchestration.user_interaction_agent.

Exercises create_user_interaction_agent by patching the (framework-provided)
Agent and MCPStreamableHTTPTool symbols plus MCPConfig.from_env, so the
factory's body runs without a live MCP server.
"""

from contextlib import AsyncExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.orchestration.user_interaction_agent as uia
from backend.orchestration.user_interaction_agent import create_user_interaction_agent


@pytest.mark.asyncio
async def test_create_user_interaction_agent():
    fake_cfg = SimpleNamespace(name="mcp-user", url="https://host/user_responses/mcp")
    sentinel_agent = MagicMock(name="Agent")
    tool_instance = AsyncMock()  # supports async context manager protocol

    with patch.object(uia.MCPConfig, "from_env", return_value=fake_cfg) as from_env, \
        patch.object(uia, "MCPStreamableHTTPTool", return_value=tool_instance) as tool_cls, \
        patch.object(uia, "Agent", return_value=sentinel_agent) as agent_cls:
        agent, stack = await create_user_interaction_agent(
            chat_client=MagicMock(), user_id="user-123"
        )

    from_env.assert_called_once_with(domain="user_responses")
    tool_cls.assert_called_once_with(name="mcp-user", url="https://host/user_responses/mcp")
    assert agent is sentinel_agent
    assert isinstance(stack, AsyncExitStack)

    # Agent constructed with the user_id embedded in the instructions.
    _, kwargs = agent_cls.call_args
    assert kwargs["name"] == "UserInteractionAgent"
    assert "user-123" in kwargs["instructions"]
    assert kwargs["tools"] == [tool_instance]

    await stack.aclose()

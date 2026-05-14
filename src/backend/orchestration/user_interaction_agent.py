"""
UserInteractionAgent: lightweight proxy for human clarification.

Optimization over the original ProxyAgent (BaseAgent subclass, 200+ lines):
- Uses a standard Agent with the ask_user MCP tool instead of custom
  WebSocket / streaming protocol reimplementation.
- The MagenticBuilder orchestrator natively handles participant selection,
  so no custom run()/run_stream() logic is needed.
- MCP tool lifecycle is managed via AsyncExitStack (context manager pattern).

The orchestrator prompt tells MagenticManager to route to this agent when
user clarification is needed — either during initial fact-finding or when a
domain agent requests it mid-execution.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack

from agent_framework import Agent, MCPStreamableHTTPTool
from config.mcp_config import MCPConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt for the UserInteractionAgent
# ---------------------------------------------------------------------------

_USER_INTERACTION_INSTRUCTIONS = """You are the UserInteractionAgent — the ONLY agent
that communicates with the human user.

SESSION_USER_ID: {user_id}

YOUR ROLE:
- When the MagenticManager selects you, it means user clarification is needed.
- The manager's message to you will describe WHAT information is needed.
- Call the ask_user tool ONCE with a clear, numbered list of questions.
- Pass SESSION_USER_ID as the user_id argument.
- Return the user's answers verbatim — do NOT interpret, filter, or act on them.

RULES:
- Ask ONLY the questions specified by the manager. Do not invent additional questions.
- Combine all pending questions into ONE ask_user call (batch them).
- If the user declines or says "skip", return that response as-is.
- Never call tools other than ask_user.
- Never attempt to answer the user's original task yourself.
"""


async def create_user_interaction_agent(
    *,
    chat_client,
    user_id: str,
) -> tuple[Agent, AsyncExitStack]:
    """Create and return a UserInteractionAgent with the ask_user MCP tool.

    Args:
        chat_client: The FoundryChatClient (shared with MagenticManager).
        user_id: The session user ID embedded in the agent prompt.

    Returns:
        A tuple of (Agent, AsyncExitStack). The caller must keep the
        AsyncExitStack alive for the duration of the workflow and call
        ``await stack.aclose()`` on cleanup.
    """
    mcp_config = MCPConfig.from_env(domain="user_responses")

    stack = AsyncExitStack()
    tool = MCPStreamableHTTPTool(name=mcp_config.name, url=mcp_config.url)
    await stack.enter_async_context(tool)

    logger.info(
        "UserInteractionAgent: connected to MCP '%s' at %s.",
        mcp_config.name,
        mcp_config.url,
    )

    instructions = _USER_INTERACTION_INSTRUCTIONS.format(user_id=user_id)

    agent = Agent(
        chat_client,
        name="UserInteractionAgent",
        instructions=instructions,
        tools=[tool],
        description=(
            "Proxy agent for user clarification. Select this agent when you "
            "need information from the human user that no domain agent can provide."
        ),
    )

    return agent, stack

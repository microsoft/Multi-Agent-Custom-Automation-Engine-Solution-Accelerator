"""
Agent Framework response callbacks for employee onboarding / multi-agent system.
Replaces Semantic Kernel message types with agent_framework ChatResponseUpdate handling.
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional

from agent_framework import (
    ChatResponseUpdate,
    FunctionCallContent,
    UsageContent,
    Role,
    TextContent,
)

from af.config.settings import connection_config
from af.models.messages import (
    AgentMessage,
    AgentMessageStreaming,
    AgentToolCall,
    AgentToolMessage,
    WebsocketMessageType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

_CITATION_PATTERNS = [
    (r"\[\d+:\d+\|source\]", ""),        # [9:0|source]
    (r"\[\s*source\s*\]", ""),           # [source]
    (r"\[\d+\]", ""),                    # [12]
    (r"【[^】]*】", ""),                  # Unicode bracket citations
    (r"\(source:[^)]*\)", ""),           # (source: xyz)
    (r"\[source:[^\]]*\]", ""),          # [source: xyz]
]


def clean_citations(text: str) -> str:
    """Remove citation markers from agent responses while preserving formatting."""
    if not text:
        return text
    for pattern, repl in _CITATION_PATTERNS:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def _parse_function_arguments(arg_value: Optional[str | dict]) -> dict:
    """Best-effort parse for function call arguments (stringified JSON or dict)."""
    if arg_value is None:
        return {}
    if isinstance(arg_value, dict):
        return arg_value
    if isinstance(arg_value, str):
        try:
            return json.loads(arg_value)
        except Exception:  # noqa: BLE001
            return {"raw": arg_value}
    return {"raw": str(arg_value)}


# ---------------------------------------------------------------------------
# Core handlers
# ---------------------------------------------------------------------------

def agent_framework_update_callback(
    update: ChatResponseUpdate,
    user_id: Optional[str] = None,
) -> None:
    """
    Handle a non-streaming perspective of updates (tool calls, intermediate steps, final usage).
    This can be called for each ChatResponseUpdate; it will route tool calls and standard text
    messages to WebSocket.
    """
    agent_name = getattr(update, "model_id", None) or "Agent"
    # Use Role or fallback
    role = getattr(update, "role", Role.ASSISTANT)

    # Detect tool/function calls
    function_call_contents = [
        c for c in (update.contents or [])
        if isinstance(c, FunctionCallContent)
    ]

    if user_id is None:
        return

    try:
        if function_call_contents:
            # Build tool message
            tool_message = AgentToolMessage(agent_name=agent_name)
            for fc in function_call_contents:
                args = _parse_function_arguments(getattr(fc, "arguments", None))
                tool_message.tool_calls.append(
                    AgentToolCall(
                        tool_name=getattr(fc, "name", "unknown_tool"),
                        arguments=args,
                    )
                )
            asyncio.create_task(
                connection_config.send_status_update_async(
                    tool_message,
                    user_id,
                    message_type=WebsocketMessageType.AGENT_TOOL_MESSAGE,
                )
            )
            logger.info("Function call(s) dispatched: %s", tool_message)
            return

        # Ignore pure usage or empty updates (handled as final in streaming handler)
        if any(isinstance(c, UsageContent) for c in (update.contents or [])):
            # We'll treat this as a final token accounting event; no standard message needed.
            logger.debug("UsageContent received (final accounting); skipping text dispatch.")
            return

        # Standard assistant/user message (non-stream delta)
        if update.text:
            final_message = AgentMessage(
                agent_name=agent_name,
                timestamp=str(time.time()),
                content=clean_citations(update.text),
            )
            asyncio.create_task(
                connection_config.send_status_update_async(
                    final_message,
                    user_id,
                    message_type=WebsocketMessageType.AGENT_MESSAGE,
                )
            )
            logger.info("%s message: %s", role.name.capitalize(), final_message)

    except Exception as e:  # noqa: BLE001
        logger.error("agent_framework_update_callback: Error sending WebSocket message: %s", e)


async def streaming_agent_framework_callback(
    update: ChatResponseUpdate,
    user_id: Optional[str] = None,
) -> None:
    """
    Handle streaming deltas. For each update with text, forward a streaming message.
    Mark is_final=True when a UsageContent is observed (end of run).
    """
    if user_id is None:
        return

    try:
        # Determine if this update marks the end
        is_final = any(isinstance(c, UsageContent) for c in (update.contents or []))

        # Streaming text can appear either in update.text or inside TextContent entries.
        pieces: list[str] = []
        if update.text:
            pieces.append(update.text)
        # Some events may provide TextContent objects without setting update.text
        for c in (update.contents or []):
            if isinstance(c, TextContent) and getattr(c, "text", None):
                pieces.append(c.text)

        if not pieces:
            return

        streaming_message = AgentMessageStreaming(
            agent_name=getattr(update, "model_id", None) or "Agent",
            content=clean_citations("".join(pieces)),
            is_final=is_final,
        )

        await connection_config.send_status_update_async(
            streaming_message,
            user_id,
            message_type=WebsocketMessageType.AGENT_MESSAGE_STREAMING,
        )

        if is_final:
            logger.info("Final streaming chunk sent for agent '%s'", streaming_message.agent_name)

    except Exception as e:  # noqa: BLE001
        logger.error("streaming_agent_framework_callback: Error sending streaming WebSocket message: %s", e)


# ---------------------------------------------------------------------------
# Convenience wrappers (optional)
# ---------------------------------------------------------------------------

def handle_update(update: ChatResponseUpdate, user_id: Optional[str]) -> None:
    """
    Unified entry point if caller doesn't distinguish streaming vs non-streaming.
    You can call this once per update. It will:
    - Forward streaming text increments
    - Forward tool calls
    - Skip purely usage-only events (except marking final in streaming)
    """
    # Send streaming chunk first (async context)
    asyncio.create_task(streaming_agent_framework_callback(update, user_id))
    # Then send non-stream items (tool calls or discrete messages)
    agent_framework_update_callback(update, user_id)


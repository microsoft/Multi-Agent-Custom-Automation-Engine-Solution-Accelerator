"""
Enhanced response callbacks (agent_framework version) for employee onboarding agent system.
"""

import asyncio
import logging
import time
import re
from typing import Any

from agent_framework import ChatMessage
# Removed: from agent_framework._content import FunctionCallContent  (does not exist)

from agent_framework._workflows._magentic import AgentRunResponseUpdate  # Streaming update type from workflows

from v4.config.settings import connection_config
from v4.models.messages import (
    AgentMessage,
    AgentMessageStreaming,
    AgentToolCall,
    AgentToolMessage,
    WebsocketMessageType,
)

logger = logging.getLogger(__name__)


def clean_citations(text: str) -> str:
    """Remove citation markers from agent responses while preserving formatting."""
    if not text:
        return text
    text = re.sub(r'\[\d+:\d+\|source\]', '', text)
    text = re.sub(r'\[\s*source\s*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'【[^】]*】', '', text)
    text = re.sub(r'\(source:[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[source:[^\]]*\]', '', text, flags=re.IGNORECASE)
    return text


def _is_function_call_item(item: Any) -> bool:
    """Heuristic to detect a function/tool call item without relying on SK class types."""
    if item is None:
        return False
    # Common SK attributes: content_type == "function_call"
    if getattr(item, "content_type", None) == "function_call":
        return True
    # Agent framework may surface something with name & arguments but no text
    if hasattr(item, "name") and hasattr(item, "arguments") and not hasattr(item, "text"):
        return True
    return False


def _extract_tool_calls_from_contents(contents: list[Any]) -> list[AgentToolCall]:
    """Convert function/tool call-like items into AgentToolCall objects via duck typing."""
    tool_calls: list[AgentToolCall] = []
    for item in contents:
        if _is_function_call_item(item):
            tool_calls.append(
                AgentToolCall(
                    tool_name=getattr(item, "name", "unknown_tool"),
                    arguments=getattr(item, "arguments", {}) or {},
                )
            )
    return tool_calls


def agent_response_callback(
    agent_id: str,
    message: ChatMessage,
    user_id: str | None = None,
) -> None:
    """
    Final (non-streaming) agent response callback using agent_framework ChatMessage.
    """
    agent_name = getattr(message, "author_name", None) or agent_id or "Unknown Agent"
    role = getattr(message, "role", "assistant")
    text = clean_citations(getattr(message, "text", "") or "")

    if not user_id:
        logger.debug("No user_id provided; skipping websocket send for final message.")
        return

    try:
        final_message = AgentMessage(
            agent_name=agent_name,
            timestamp=time.time(),
            content=text,
        )
        asyncio.create_task(
            connection_config.send_status_update_async(
                final_message,
                user_id,
                message_type=WebsocketMessageType.AGENT_MESSAGE,
            )
        )
        logger.info("%s message (agent=%s): %s", str(role).capitalize(), agent_name, text[:200])
    except Exception as e:  
        logger.error("agent_response_callback error sending WebSocket message: %s", e)


async def streaming_agent_response_callback(
    agent_id: str,
    update: AgentRunResponseUpdate,
    is_final: bool,
    user_id: str | None = None,
) -> None:
    """
    Streaming callback for incremental agent output (AgentRunResponseUpdate).
    """
    if not user_id:
        return

    try:
        chunk_text = getattr(update, "text", None)
        if not chunk_text:
            contents = getattr(update, "contents", []) or []
            collected = []
            for item in contents:
                txt = getattr(item, "text", None)
                if txt:
                    collected.append(str(txt))
            chunk_text = "".join(collected) if collected else ""

        cleaned = clean_citations(chunk_text or "")

        contents = getattr(update, "contents", []) or []
        tool_calls = _extract_tool_calls_from_contents(contents)
        if tool_calls:
            tool_message = AgentToolMessage(agent_name=agent_id)
            tool_message.tool_calls.extend(tool_calls)
            await connection_config.send_status_update_async(
                tool_message,
                user_id,
                message_type=WebsocketMessageType.AGENT_TOOL_MESSAGE,
            )
            logger.info("Tool calls streamed from %s: %d", agent_id, len(tool_calls))

        if cleaned:
            streaming_payload = AgentMessageStreaming(
                agent_name=agent_id,
                content=cleaned,
                is_final=is_final,
            )
            await connection_config.send_status_update_async(
                streaming_payload,
                user_id,
                message_type=WebsocketMessageType.AGENT_MESSAGE_STREAMING,
            )
            logger.debug("Streaming chunk (agent=%s final=%s len=%d)", agent_id, is_final, len(cleaned))
    except Exception as e:  
        logger.error("streaming_agent_response_callback error: %s", e)
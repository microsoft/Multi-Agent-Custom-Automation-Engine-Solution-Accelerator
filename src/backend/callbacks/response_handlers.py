"""
Enhanced response callbacks (agent_framework version) for employee onboarding agent system.
"""

import asyncio
import logging
import re
import time
from typing import Any

from agent_framework import AgentResponseUpdate, Message
from models.messages import (AgentMessage, AgentMessageStreaming,
                             AgentToolCall, AgentToolMessage,
                             WebsocketMessageType)
from orchestration.connection_config import connection_config

logger = logging.getLogger(__name__)


def format_agent_display_name(raw_name: str) -> str:
    """Convert raw agent IDs (e.g. 'HRHelperAgent', 'hr_helper_agent') to
    human-readable display names (e.g. 'HR Helper Agent').

    Applies similar splitting/casing logic as the frontend's
    ``cleanTextToSpaces`` + ``getAgentDisplayName`` pipeline, but does NOT
    strip the "Agent" suffix (the frontend handles that separately).
    """
    if not raw_name:
        return "Assistant"

    name = raw_name

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Insert space before each uppercase letter preceded by a lowercase letter
    # e.g. "HelperAgent" → "Helper Agent"
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

    # Insert space between consecutive uppercase and an uppercase+lowercase pair
    # e.g. "HRHelper" → "HR Helper"
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)

    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()

    # Title-case each word
    name = name.title()

    # Fix common acronyms back to uppercase (word-boundary safe)
    _ACRONYMS = {'Hr': 'HR', 'It': 'IT', 'Ai': 'AI', 'Api': 'API',
                 'Ui': 'UI', 'Db': 'DB', 'Kb': 'KB'}
    for title_form, upper_form in _ACRONYMS.items():
        name = re.sub(rf'\b{title_form}\b', upper_form, name)

    return name


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
    message: Message,
    user_id: str | None = None,
) -> None:
    """
    Final (non-streaming) agent response callback using agent_framework Message.
    """
    agent_name = getattr(message, "author_name", None) or agent_id or "Unknown Agent"
    agent_name = format_agent_display_name(agent_name)
    role = getattr(message, "role", "assistant")

    # Message has a .text property that concatenates all TextContent items
    text = getattr(message, "text", "") if message is not None else ""

    text = clean_citations(text or "")

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
    update: AgentResponseUpdate,
    is_final: bool,
    user_id: str | None = None,
) -> None:
    """
    Streaming callback for incremental agent output (AgentResponseUpdate).
    """
    if not user_id:
        return

    display_name = format_agent_display_name(agent_id)

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
            tool_message = AgentToolMessage(agent_name=display_name)
            tool_message.tool_calls.extend(tool_calls)
            await connection_config.send_status_update_async(
                tool_message,
                user_id,
                message_type=WebsocketMessageType.AGENT_TOOL_MESSAGE,
            )
            logger.info("Tool calls streamed from %s: %d", agent_id, len(tool_calls))

        if cleaned:
            streaming_payload = AgentMessageStreaming(
                agent_name=display_name,
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

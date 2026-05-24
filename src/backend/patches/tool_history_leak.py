"""Monkey-patch for agent-framework-orchestrations tool-call-history-leak bug.

Bug: MagenticOrchestrator._handle_response broadcasts raw participant messages
(including function_call / function_call_output content) to all other participants.
When the next agent is invoked, the API rejects orphaned tool-call items it never
issued, producing: "No tool call found for function call output with call_id ..."

Fix (two layers):
1. Override _handle_response to filter messages before broadcasting (production path).
2. Override AgentExecutor._run_agent_and_emit to filter _cache in-place before
   sending to the model (consumption path — catches any leaks we missed).

Tracking: localspec/bugs/framework/F1-tool-history-leak.md
Framework: agent-framework-orchestrations==1.0.0b260514
"""

import logging
from copy import deepcopy
from typing import cast

from agent_framework import AgentExecutor, Message
from agent_framework_orchestrations._magentic import MagenticOrchestrator

logger = logging.getLogger(__name__)

_TOOL_CONTENT_TYPES = frozenset({"function_call", "function_call_output", "function_result"})


def _filter_tool_call_messages(messages: list[Message]) -> list[Message]:
    """Remove or sanitize messages containing function_call content.

    Returns a new list where:
    - Messages with role="tool" are dropped entirely (tool results belong to caller only)
    - Messages with ONLY tool-call content are dropped entirely
    - Messages with mixed content (text + tool-call) keep only the text items
    - Messages with no tool-call content pass through unchanged
    """
    filtered: list[Message] = []
    for msg in messages:
        # Drop tool-role messages outright — they only make sense to the agent that issued the call
        if getattr(msg, "role", None) == "tool":
            logger.debug("Dropping tool-role message (%d items) from broadcast", len(msg.contents))
            continue

        tool_contents = [c for c in msg.contents if getattr(c, "type", None) in _TOOL_CONTENT_TYPES]
        if not tool_contents:
            # No tool-call content → pass through
            filtered.append(msg)
            continue

        non_tool_contents = [c for c in msg.contents if getattr(c, "type", None) not in _TOOL_CONTENT_TYPES]
        if non_tool_contents:
            # Mixed message → keep only the text/non-tool parts
            sanitized = deepcopy(msg)
            sanitized.contents = non_tool_contents
            filtered.append(sanitized)
            logger.debug(
                "Stripped %d tool-call items from message (kept %d text items)",
                len(tool_contents), len(non_tool_contents),
            )
        else:
            # Pure tool-call message → drop from broadcast
            logger.debug(
                "Dropping pure tool-call message (role=%s, %d items) from broadcast",
                msg.role, len(tool_contents),
            )
    return filtered


# Store original method reference
_original_handle_response = MagenticOrchestrator._handle_response


async def _patched_handle_response(self, response, ctx) -> None:
    """Patched _handle_response that filters tool-call items before broadcast."""
    if self._magentic_context is None or self._task_ledger is None:
        raise RuntimeError("Context or task ledger not initialized")

    messages = self._process_participant_response(response)

    # Add FULL messages to chat_history (manager model can handle them)
    self._magentic_context.chat_history.extend(messages)

    # Filter out tool-call content before broadcasting to other participants
    broadcast_messages = _filter_tool_call_messages(messages)

    if broadcast_messages:
        participant = ctx.get_source_executor_id()
        await self._broadcast_messages_to_participants(
            broadcast_messages,
            cast(type(ctx), ctx),
            participants=[p for p in self._participant_registry.participants if p != participant],
        )
    else:
        logger.debug("All messages were tool-call only — nothing to broadcast")

    await self._run_inner_loop(ctx)


def apply_tool_history_leak_patch():
    """Apply the monkey-patch. Call once at import time."""
    # Layer 1: filter at broadcast (production path in _handle_response)
    MagenticOrchestrator._handle_response = _patched_handle_response  # type: ignore[assignment]

    # Layer 2: filter at consumption (AgentExecutor cache before model call)
    _original_run_agent_and_emit = AgentExecutor._run_agent_and_emit

    async def _patched_run_agent_and_emit(self, ctx):
        """Filter tool-call items from _cache before sending to the model."""
        # Debug: log what the agent sees on invocation
        agent_name = getattr(getattr(self, 'agent', None), 'name', None) or getattr(self, 'id', '?')
        logger.info(
            "=== AGENT INVOCATION: %s === cache has %d messages",
            agent_name, len(self._cache),
        )
        for i, msg in enumerate(self._cache):
            role = getattr(msg, 'role', '?')
            text = getattr(msg, 'text', '') or ''
            content_types = [getattr(c, 'type', '?') for c in getattr(msg, 'contents', [])]
            logger.info(
                "  [%d] role=%s types=%s text_preview='%s'",
                i, role, content_types, text[:150].replace('\n', ' '),
            )

        pre_len = len(self._cache)
        self._cache = _filter_tool_call_messages(self._cache)
        post_len = len(self._cache)
        if pre_len != post_len:
            logger.warning(
                "F1 patch layer 2: Filtered %d tool-call messages from AgentExecutor "
                "cache before model call (%d → %d messages)",
                pre_len - post_len, pre_len, post_len,
            )
        return await _original_run_agent_and_emit(self, ctx)

    AgentExecutor._run_agent_and_emit = _patched_run_agent_and_emit  # type: ignore[assignment]
    print("[F1-PATCH] Applied: MagenticOrchestrator._handle_response + AgentExecutor._run_agent_and_emit")

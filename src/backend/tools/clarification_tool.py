"""Approval-gated clarification tool for human-in-the-loop (HITL).

Agents that need user input call ``request_user_clarification(questions=...)``.
Because the tool uses ``approval_mode="always_require"``, the framework pauses
execution and emits a ``function_approval_request`` event that the orchestration
manager intercepts, routes to the user via WebSocket, and resumes with the answer.

The answer is stored in a per-request shared-state dict BEFORE the approval is
granted. When the tool body finally executes, it reads the stored answer and
returns it to the agent.

This replaces the proxy-agent approach (UserInteractionAgent + MCP ask_user tool)
with a single @tool on each domain agent — eliminating cross-participant tool
history leaks and simplifying the architecture.
"""

import logging
from typing import Dict

from agent_framework._tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared answer store — keyed by request_id.
# Populated by orchestration_manager._process_event_stream() BEFORE approving.
# ---------------------------------------------------------------------------
_pending_answers: Dict[str, str] = {}


def store_answer(request_id: str, answer: str) -> None:
    """Store a user's answer for a pending clarification request."""
    _pending_answers[request_id] = answer


def pop_answer(request_id: str) -> str:
    """Retrieve and remove a stored answer. Returns empty string if not found."""
    return _pending_answers.pop(request_id, "")


# ---------------------------------------------------------------------------
# The approval-gated tool given to domain agents with user_responses=true.
# ---------------------------------------------------------------------------
@tool(approval_mode="always_require")
def request_user_clarification(questions: str) -> str:
    """Ask the user for clarifying information and return their answer.

    Use this tool when you need information that is not available in the
    conversation context. Provide clear, numbered questions so the user
    knows exactly what to answer.

    Args:
        questions: The questions to ask the user, formatted as a numbered list.

    Returns:
        The user's answer text.
    """
    # When this body executes, the framework has already paused, the
    # orchestration manager sent questions to the user, received the answer,
    # stored it via store_answer(), and approved the tool call.
    #
    # We use the function call ID (injected by the framework into the
    # execution context) to look up the answer.  Since we can't directly
    # access the request_id inside the tool body, we use a "latest for this
    # tool" fallback — the orchestration manager stores under request_id
    # AND under a thread-local key.
    import threading
    thread_key = f"_clarification_{threading.current_thread().ident}"
    answer = _pending_answers.pop(thread_key, "")
    if not answer:
        # Fallback: pop any remaining answer (single-user scenario)
        if _pending_answers:
            answer = _pending_answers.pop(next(iter(_pending_answers)))
    if not answer:
        return "Error: No answer was provided by the user."
    return answer

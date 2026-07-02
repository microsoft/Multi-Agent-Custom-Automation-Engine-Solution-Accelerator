"""TEMPORARY monkey-patch for duplicate fc_ item ID bug in MagenticBuilder.

Root cause
----------
``StandardMagenticManager._complete()`` sends the full ``messages`` list
(which already contains the complete ``chat_history``) **and**
``session=self._session`` (which chains via ``previous_response_id``).
After the second tool-bearing participant runs, function_call items from the
first participant appear in both the explicit input and the server-side
session chain, causing:

    400 — "Duplicate item found with id fc_…"

The framework catches this as "Progress ledger creation failed, triggering
reset" and enters a reset → replan loop that never converges.

Fix
---
Override ``_complete`` to pass ``session=None``.  The full ``chat_history``
is still sent explicitly in ``messages`` every call, so no context is lost.
The only cost is slightly higher token usage (re-sending context instead of
referencing it via the server-side chain), which is irrelevant for this
solution accelerator.

Removal
-------
Remove this patch when ``agent-framework`` ships the real fix.
Track upstream PR: https://github.com/microsoft/agent-framework/pull/5690

See also: bugs/magentic-duplicate-fc-id-bug.md
"""

import logging
from typing import TYPE_CHECKING

from agent_framework import AgentResponse, Message

if TYPE_CHECKING:
    from agent_framework_orchestrations._magentic import \
        StandardMagenticManager

logger = logging.getLogger(__name__)

_PATCHED = False


async def _complete_without_session(self: "StandardMagenticManager", messages: list[Message]) -> Message:
    """Drop-in replacement for ``StandardMagenticManager._complete``.

    Identical to the original except ``session=None`` — prevents the
    Responses API from seeing duplicate ``fc_`` items that are already
    present in the explicit ``messages`` list.
    """
    response: AgentResponse = await self._agent.run(messages, session=None)
    if not response.messages:
        raise RuntimeError("Agent returned no messages in response.")
    if len(response.messages) > 1:
        logger.warning("Agent returned multiple messages; using the last one.")
    return response.messages[-1]


def apply() -> None:
    """Monkey-patch ``StandardMagenticManager._complete`` (idempotent).

    Call once at application startup — before any MagenticBuilder workflow
    is constructed.

    TEMPORARY — remove when agent-framework PR #5690 is merged and the
    package is updated.
    """
    global _PATCHED
    if _PATCHED:
        return

    from agent_framework_orchestrations._magentic import \
        StandardMagenticManager

    StandardMagenticManager._complete = _complete_without_session  # type: ignore[assignment]
    _PATCHED = True
    logger.info(
        "TEMPORARY PATCH APPLIED: StandardMagenticManager._complete now uses "
        "session=None to avoid duplicate fc_ item IDs.  "
        "Remove when agent-framework PR #5690 lands."
    )

"""
ProxyAgentAF: Human clarification proxy implemented on agent_framework primitives.

Responsibilities:
- Request clarification from a human via websocket
- Await response (with timeout + cancellation handling via orchestration_config)
- Yield ChatResponseUpdate objects compatible with agent_framework streaming loops
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional

from agent_framework import (
    ChatResponseUpdate,
    Role,
    TextContent,
    UsageContent,
    UsageDetails,
)
from af.config.settings import connection_config, orchestration_config
from af.models.messages import (
    UserClarificationRequest,
    UserClarificationResponse,
    TimeoutNotification,
    WebsocketMessageType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal conversation structure (minimal alternative to SK AgentThread)
# ---------------------------------------------------------------------------

@dataclass
class ProxyConversation:
    conversation_id: str = field(default_factory=lambda: f"proxy_{uuid.uuid4().hex}")
    messages: List[str] = field(default_factory=list)

    def add(self, content: str) -> None:
        self.messages.append(content)


# ---------------------------------------------------------------------------
# Proxy Agent AF
# ---------------------------------------------------------------------------

class ProxyAgent:
    """
    A lightweight "agent" that mediates human clarification.
    Not a model-backed agent; it orchestrates a request and emits a synthetic reply.
    """

    def __init__(
        self,
        user_id: Optional[str],
        name: str = "ProxyAgent",
        description: str = (
            "Clarification agent. Ask this when instructions are unclear or additional "
            "user details are required."
        ),
        timeout_seconds: Optional[int] = None,
    ):
        self.user_id = user_id or ""
        self.name = name
        self.description = description
        self._timeout = timeout_seconds or orchestration_config.default_timeout
        self._conversation = ProxyConversation()

    # ---------------------------
    # Public invocation interfaces
    # ---------------------------

    async def invoke(self, message: str) -> AsyncIterator[ChatResponseUpdate]:
        """
        One-shot style: waits for human clarification, then yields a single final response update.
        """
        async for update in self.invoke_stream(message):
            # If caller expects only the final text, they can just collect the last update
            continue
        # When invoke_stream finishes, it already yielded final updates;
        # this wrapper exists for parity with LLM agents returning enumerables.
        return

    async def invoke_stream(self, message: str) -> AsyncIterator[ChatResponseUpdate]:
        """
        Streaming version:
        1. Sends clarification request via websocket (no yield yet).
        2. Waits for human response / timeout.
        3. Yields:
           - A ChatResponseUpdate with the final clarified answer (as assistant text) if received.
           - A usage marker (synthetic) for downstream consistency.
        """
        original_prompt = message or ""
        self._conversation.add(original_prompt)

        clarification_req_text = f"I need clarification about: {original_prompt}"
        clarification_request = UserClarificationRequest(
            question=clarification_req_text,
            request_id=str(uuid.uuid4()),
        )

        # Dispatch websocket event requesting clarification
        await connection_config.send_status_update_async(
            {
                "type": WebsocketMessageType.USER_CLARIFICATION_REQUEST,
                "data": clarification_request,
            },
            user_id=self.user_id,
            message_type=WebsocketMessageType.USER_CLARIFICATION_REQUEST,
        )

        # Await human clarification
        human_response = await self._wait_for_user_clarification(clarification_request.request_id)

        if human_response is None:
            # Timeout or cancellation already handled (timeout notification was sent).
            logger.debug(
                "ProxyAgentAF: No clarification response (timeout/cancel). Ending stream silently."
            )
            return

        answer_text = (
            human_response.answer
            if human_response.answer
            else "No additional clarification provided."
        )
        synthetic_reply = f"Human clarification: {answer_text}"
        self._conversation.add(synthetic_reply)

        # Yield final assistant text chunk
        yield self._make_text_update(synthetic_reply, is_final=False)

        # Yield a synthetic usage update so downstream consumers can treat this like a model run
        yield self._make_usage_update(token_estimate=len(synthetic_reply.split()))

    # ---------------------------
    # Internal helpers
    # ---------------------------

    async def _wait_for_user_clarification(
        self, request_id: str
    ) -> Optional[UserClarificationResponse]:
        """
        Wraps orchestration_config.wait_for_clarification with robust timeout & cleanup.
        """
        orchestration_config.set_clarification_pending(request_id)
        try:
            answer = await orchestration_config.wait_for_clarification(request_id)
            return UserClarificationResponse(request_id=request_id, answer=answer)
        except asyncio.TimeoutError:
            await self._notify_timeout(request_id)
            return None
        except asyncio.CancelledError:
            logger.debug("ProxyAgentAF: Clarification request %s cancelled", request_id)
            orchestration_config.cleanup_clarification(request_id)
            return None
        except KeyError:
            logger.debug("ProxyAgentAF: Invalid clarification request id %s", request_id)
            return None
        except Exception as ex:  # noqa: BLE001
            logger.debug("ProxyAgentAF: Unexpected error awaiting clarification: %s", ex)
            orchestration_config.cleanup_clarification(request_id)
            return None
        finally:
            # Safety net cleanup if still pending with no value.
            if (
                request_id in orchestration_config.clarifications
                and orchestration_config.clarifications[request_id] is None
            ):
                orchestration_config.cleanup_clarification(request_id)

    async def _notify_timeout(self, request_id: str) -> None:
        """Send a timeout notification to the client and clean up."""
        notice = TimeoutNotification(
            timeout_type="clarification",
            request_id=request_id,
            message=(
                f"User clarification request timed out after "
                f"{self._timeout} seconds. Please retry."
            ),
            timestamp=time.time(),
            timeout_duration=self._timeout,
        )
        try:
            await connection_config.send_status_update_async(
                message=notice,
                user_id=self.user_id,
                message_type=WebsocketMessageType.TIMEOUT_NOTIFICATION,
            )
            logger.info(
                "ProxyAgentAF: Timeout notification sent (request_id=%s user=%s)",
                request_id,
                self.user_id,
            )
        except Exception as ex:  # noqa: BLE001
            logger.error("ProxyAgentAF: Failed to send timeout notification: %s", ex)
        orchestration_config.cleanup_clarification(request_id)

    def _make_text_update(
        self,
        text: str,
        is_final: bool,
    ) -> ChatResponseUpdate:
        """
        Build a ChatResponseUpdate containing assistant text. We treat each
        emitted text as a 'delta'; downstream can concatenate if needed.
        """
        return ChatResponseUpdate(
            role=Role.ASSISTANT,
            text=text,
            contents=[TextContent(text=text)],
            conversation_id=self._conversation.conversation_id,
            message_id=str(uuid.uuid4()),
            response_id=str(uuid.uuid4()),
        )

    def _make_usage_update(self, token_estimate: int) -> ChatResponseUpdate:
        """
        Provide a synthetic usage update (assist in downstream finalization logic).
        """
        usage = UsageContent(
            UsageDetails(
                input_token_count=0,
                output_token_count=token_estimate,
                total_token_count=token_estimate,
            )
        )
        return ChatResponseUpdate(
            role=Role.ASSISTANT,
            text="",
            contents=[usage],
            conversation_id=self._conversation.conversation_id,
            message_id=str(uuid.uuid4()),
            response_id=str(uuid.uuid4()),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

async def create_proxy_agent(user_id: Optional[str] = None) -> ProxyAgent:
    """
    Factory for ProxyAgentAF (mirrors previous create_proxy_agent interface).
    """
    return ProxyAgent(user_id=user_id)
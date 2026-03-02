"""
ProxyAgent: Human clarification proxy compliant with agent_framework.

Responsibilities:
- Request clarification from a human via websocket
- Await response (with timeout + cancellation handling)
- Yield AgentRunResponseUpdate objects compatible with agent_framework
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterable

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    BaseAgent,
    ChatMessage,
    Role,
    Content,
    UsageDetails,
    AgentThread,
)

from v4.config.settings import connection_config, orchestration_config
from v4.models.messages import (
    UserClarificationRequest,
    UserClarificationResponse,
    TimeoutNotification,
    WebsocketMessageType,
)

logger = logging.getLogger(__name__)


class ProxyAgent(BaseAgent):
    """
    A human-in-the-loop clarification agent extending agent_framework's BaseAgent.

    This agent mediates human clarification requests rather than using an LLM.
    It follows the agent_framework protocol with run() and run_stream() methods.
    """

    def __init__(
        self,
        user_id: str | None = None,
        name: str = "ProxyAgent",
        description: str = (
            "Clarification agent. Ask this when instructions are unclear or additional "
            "user details are required."
        ),
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            name=name,
            description=description,
            **kwargs
        )
        self.user_id = user_id or ""
        self._timeout = timeout_seconds or orchestration_config.default_timeout

    # ---------------------------
    # AgentProtocol implementation
    # ---------------------------

    def get_new_thread(self, **kwargs: Any) -> AgentThread:
        """
        Create a new thread for ProxyAgent conversations.
        Required by AgentProtocol for workflow integration.

        Args:
            **kwargs: Additional keyword arguments for thread creation

        Returns:
            A new AgentThread instance
        """
        return AgentThread(**kwargs)

    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Get complete clarification response (non-streaming).

        Args:
            messages: The message(s) requiring clarification
            thread: Optional conversation thread
            kwargs: Additional keyword arguments

        Returns:
            AgentResponse with the clarification
        """
        # Collect all streaming updates
        response_messages: list[ChatMessage] = []
        response_id = str(uuid.uuid4())

        async for update in self.run_stream(messages, thread=thread, **kwargs):
            if update.contents:
                response_messages.append(
                    ChatMessage(
                        role=update.role or Role.ASSISTANT,
                        contents=update.contents,
                    )
                )

        return AgentResponse(
            messages=response_messages,
            response_id=response_id,
        )

    def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseUpdate]:
        """
        Stream clarification process with human interaction.

        Args:
            messages: The message(s) requiring clarification
            thread: Optional conversation thread
            kwargs: Additional keyword arguments

        Yields:
            AgentRunResponseUpdate objects with clarification progress
        """
        return self._invoke_stream_internal(messages, thread, **kwargs)

    async def _invoke_stream_internal(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None,
        thread: AgentThread | None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseUpdate]:
        """
        Internal streaming implementation.

        1. Sends clarification request via websocket
        2. Waits for human response / timeout
        3. Yields AgentRunResponseUpdate with the clarified answer
        """
        # Normalize messages to string
        message_text = self._extract_message_text(messages)

        logger.info(
            "ProxyAgent: Requesting clarification (thread=%s, user=%s)",
            "present" if thread else "None",
            self.user_id
        )
        logger.debug("ProxyAgent: Message text: %s", message_text[:100])

        clarification_req_text = f"{message_text}"
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
        human_response = await self._wait_for_user_clarification(
            clarification_request.request_id
        )

        if human_response is None:
            # Timeout or cancellation - end silently
            logger.debug(
                "ProxyAgent: No clarification response (timeout/cancel). Ending stream."
            )
            return

        answer_text = (
            human_response.answer
            if human_response.answer
            else "No additional clarification provided."
        )

        # Return just the user's answer directly - no prefix that might confuse orchestrator
        synthetic_reply = answer_text

        logger.info("ProxyAgent: Received clarification: %s", synthetic_reply[:100])

        # Generate consistent IDs for this response
        response_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        # Yield final assistant text update with explicit text content
        # New API: use Content.from_text() or pass text directly to AgentResponseUpdate
        text_update = AgentResponseUpdate(
            role=Role.ASSISTANT,
            text=synthetic_reply,  # New API accepts text directly
            author_name=self.name,
            response_id=response_id,
            message_id=message_id,
        )

        logger.debug("ProxyAgent: Yielding text update (text length=%d)", len(synthetic_reply))
        yield text_update

        # Yield synthetic usage update for consistency
        # Use same message_id to indicate this is part of the same message
        usage_update = AgentResponseUpdate(
            role=Role.ASSISTANT,
            contents=[
                Content.from_usage(
                    UsageDetails(
                        input_token_count=len(message_text.split()),
                        output_token_count=len(synthetic_reply.split()),
                        total_token_count=len(message_text.split()) + len(synthetic_reply.split()),
                    )
                )
            ],
            author_name=self.name,
            response_id=response_id,
            message_id=message_id,  # Same message_id groups with text content
        )

        logger.debug("ProxyAgent: Yielding usage update")
        yield usage_update

        logger.info("ProxyAgent: Completed clarification response")

    # ---------------------------
    # Helper methods
    # ---------------------------

    def _extract_message_text(
        self, messages: str | ChatMessage | list[str] | list[ChatMessage] | None
    ) -> str:
        """Extract text from various message formats."""
        if messages is None:
            return ""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, ChatMessage):
            # Use the .text property which concatenates all TextContent items
            return messages.text or ""
        if isinstance(messages, list):
            if not messages:
                return ""
            if isinstance(messages[0], str):
                return " ".join(messages)
            if isinstance(messages[0], ChatMessage):
                # Use .text property for each message
                return " ".join(msg.text or "" for msg in messages)
        return str(messages)

    async def _wait_for_user_clarification(
        self, request_id: str
    ) -> UserClarificationResponse | None:
        """
        Wait for user clarification with timeout and cancellation handling.
        """
        orchestration_config.set_clarification_pending(request_id)
        try:
            answer = await orchestration_config.wait_for_clarification(request_id)
            return UserClarificationResponse(request_id=request_id, answer=answer)
        except asyncio.TimeoutError:
            await self._notify_timeout(request_id)
            return None
        except asyncio.CancelledError:
            logger.debug("ProxyAgent: Clarification request %s cancelled", request_id)
            orchestration_config.cleanup_clarification(request_id)
            return None
        except KeyError:
            logger.debug("ProxyAgent: Invalid clarification request id %s", request_id)
            return None
        except Exception as ex:
            logger.debug("ProxyAgent: Unexpected error awaiting clarification: %s", ex)
            orchestration_config.cleanup_clarification(request_id)
            return None
        finally:
            # Safety net cleanup
            if (
                request_id in orchestration_config.clarifications
                and orchestration_config.clarifications[request_id] is None
            ):
                orchestration_config.cleanup_clarification(request_id)

    async def _notify_timeout(self, request_id: str) -> None:
        """Send timeout notification to the client."""
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
                "ProxyAgent: Timeout notification sent (request_id=%s user=%s)",
                request_id,
                self.user_id,
            )
        except Exception as ex:
            logger.error("ProxyAgent: Failed to send timeout notification: %s", ex)
        orchestration_config.cleanup_clarification(request_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

async def create_proxy_agent(user_id: str | None = None) -> ProxyAgent:
    """
    Factory for ProxyAgent.

    Args:
        user_id: User ID for websocket communication

    Returns:
        Initialized ProxyAgent instance
    """
    return ProxyAgent(user_id=user_id)

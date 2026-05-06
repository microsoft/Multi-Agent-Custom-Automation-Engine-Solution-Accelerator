"""
ProxyAgent: Human clarification proxy for agent_framework GA (1.2.2).

Carry-forward of v4/magentic_agents/proxy_agent.py with the following changes:
  - Import paths: v4.config.settings → orchestration.connection_config
                  v4.models.messages → models.messages
  - Type mappings (deprecated → GA):
      AgentRunResponse       → AgentResponse
      AgentRunResponseUpdate → AgentResponseUpdate
      ChatMessage            → Message
      AgentThread            → AgentSession
      TextContent(text=x)    → Content.from_text(x)
      UsageContent(...)      → Content.from_usage(UsageDetails(...))
      Role.ASSISTANT         → "assistant"  (Role is a NewType[str] in v1.2.2)
      run_stream() signature → run(*, stream=True) style preserved via ResponseStream
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterable

from agent_framework import (AgentResponse, AgentResponseUpdate, AgentSession,
                             BaseAgent, Content, Message, ResponseStream,
                             UsageDetails)
from orchestration.connection_config import (connection_config,
                                             orchestration_config)
from v4.models.messages import (TimeoutNotification, UserClarificationRequest,
                                UserClarificationResponse,
                                WebsocketMessageType)

logger = logging.getLogger(__name__)


class ProxyAgent(BaseAgent):
    """Human-in-the-loop clarification agent extending agent_framework's BaseAgent.

    Mediates human clarification requests rather than calling an LLM.
    Implements the agent_framework run() / run_stream() protocol so the Magentic
    orchestrator can treat it identically to any other agent in the team.
    """

    def __init__(
        self,
        user_id: str | None = None,
        name: str = "ProxyAgent",
        description: str = (
            "Clarification agent. Ask this when instructions are unclear or "
            "additional user details are required."
        ),
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, description=description, **kwargs)
        self.user_id = user_id or ""
        self._timeout = timeout_seconds or orchestration_config.default_timeout

    # ------------------------------------------------------------------
    # AgentProtocol — required by agent_framework BaseAgent
    # ------------------------------------------------------------------

    def create_session(self, *, session_id: str | None = None, **kwargs: Any) -> AgentSession:
        """Create a new AgentSession (replaces get_new_thread / AgentThread in v4)."""
        return AgentSession(session_id=session_id)

    def run(
        self,
        messages: str | Message | list[str] | list[Message] | None = None,
        *,
        stream: bool = False,
        session: AgentSession | None = None,
        **kwargs: Any,
    ) -> "Any":
        """Dispatch to streaming or non-streaming implementation.

        Returns:
            ResponseStream when ``stream=True``, otherwise an awaitable AgentResponse.
        """
        if stream:
            return ResponseStream(
                self._invoke_stream_internal(messages, session),
                finalizer=lambda updates: AgentResponse.from_updates(updates),
            )
        return self._run_non_streaming(messages, session)

    async def _run_non_streaming(
        self,
        messages: str | Message | list[str] | list[Message] | None,
        session: AgentSession | None,
    ) -> AgentResponse:
        """Non-streaming wrapper — collects all updates into a single AgentResponse."""
        response_messages: list[Message] = []
        response_id = str(uuid.uuid4())

        async for update in self._invoke_stream_internal(messages, session):
            if update.contents:
                response_messages.append(
                    Message(role=update.role or "assistant", contents=update.contents)
                )

        return AgentResponse(messages=response_messages, response_id=response_id)

    async def _invoke_stream_internal(
        self,
        messages: str | Message | list[str] | list[Message] | None,
        session: AgentSession | None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseUpdate]:
        """Core streaming implementation.

        1. Sends a clarification request to the user via WebSocket.
        2. Waits for the human response (with timeout / cancellation handling).
        3. Yields an AgentResponseUpdate with the clarification answer.
        """
        message_text = self._extract_message_text(messages)

        logger.info(
            "ProxyAgent: requesting clarification (session=%s, user=%s).",
            session.session_id if session else "None",
            self.user_id,
        )
        logger.debug("ProxyAgent: message text: %.100s", message_text)

        clarification_request = UserClarificationRequest(
            question=message_text,
            request_id=str(uuid.uuid4()),
        )

        await connection_config.send_status_update_async(
            {
                "type": WebsocketMessageType.USER_CLARIFICATION_REQUEST,
                "data": clarification_request,
            },
            user_id=self.user_id,
            message_type=WebsocketMessageType.USER_CLARIFICATION_REQUEST,
        )

        human_response = await self._wait_for_user_clarification(
            clarification_request.request_id
        )

        if human_response is None:
            logger.debug(
                "ProxyAgent: no clarification response (timeout/cancel). Ending stream."
            )
            return

        answer_text = human_response.answer or "No additional clarification provided."
        logger.info("ProxyAgent: received clarification: %.100s", answer_text)

        response_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        # Text update
        yield AgentResponseUpdate(
            role="assistant",
            contents=[Content.from_text(answer_text)],
            author_name=self.name,
            response_id=response_id,
            message_id=message_id,
        )

        # Usage update (same message_id groups with text content)
        yield AgentResponseUpdate(
            role="assistant",
            contents=[
                Content.from_usage(
                    UsageDetails(
                        input_token_count=len(message_text.split()),
                        output_token_count=len(answer_text.split()),
                        total_token_count=len(message_text.split()) + len(answer_text.split()),
                    )
                )
            ],
            author_name=self.name,
            response_id=response_id,
            message_id=message_id,
        )

        logger.info("ProxyAgent: completed clarification response.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_message_text(
        self,
        messages: str | Message | list[str] | list[Message] | None,
    ) -> str:
        """Extract a single string from various input message formats."""
        if messages is None:
            return ""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, Message):
            return messages.text or ""
        if isinstance(messages, list):
            if not messages:
                return ""
            if isinstance(messages[0], str):
                return " ".join(messages)
            # list[Message]
            return " ".join(msg.text or "" for msg in messages if isinstance(msg, Message))
        return str(messages)

    async def _wait_for_user_clarification(
        self, request_id: str
    ) -> UserClarificationResponse | None:
        """Wait for user clarification with timeout and cancellation handling."""
        orchestration_config.set_clarification_pending(request_id)
        try:
            answer = await orchestration_config.wait_for_clarification(request_id)
            return UserClarificationResponse(request_id=request_id, answer=answer)
        except asyncio.TimeoutError:
            await self._notify_timeout(request_id)
            return None
        except asyncio.CancelledError:
            logger.debug("ProxyAgent: clarification request %s cancelled.", request_id)
            orchestration_config.cleanup_clarification(request_id)
            return None
        except KeyError:
            logger.debug("ProxyAgent: invalid clarification request id %s.", request_id)
            return None
        except Exception as exc:
            logger.debug("ProxyAgent: unexpected error awaiting clarification: %s", exc)
            orchestration_config.cleanup_clarification(request_id)
            return None
        finally:
            # Safety-net cleanup for stale pending entries
            pending = getattr(orchestration_config, "clarifications", {})
            if request_id in pending and pending[request_id] is None:
                orchestration_config.cleanup_clarification(request_id)

    async def _notify_timeout(self, request_id: str) -> None:
        """Send a timeout notification to the client via WebSocket."""
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
                "ProxyAgent: timeout notification sent (request_id=%s, user=%s).",
                request_id,
                self.user_id,
            )
        except Exception as exc:
            logger.error("ProxyAgent: failed to send timeout notification: %s", exc)
        orchestration_config.cleanup_clarification(request_id)

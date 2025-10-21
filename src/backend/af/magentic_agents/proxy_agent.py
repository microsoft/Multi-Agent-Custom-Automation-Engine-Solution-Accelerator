# Copyright (c) Microsoft. All rights reserved.
"""Proxy agent that prompts for human clarification."""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterable
from typing import AsyncIterator, Optional

from pydantic import Field
from semantic_kernel.agents import (  # pylint: disable=no-name-in-module
    AgentResponseItem,
    AgentThread,
)
from semantic_kernel.agents.agent import Agent
from semantic_kernel.contents import (
    AuthorRole,
    ChatMessageContent,
    StreamingChatMessageContent,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.history_reducer.chat_history_reducer import (
    ChatHistoryReducer,
)
from semantic_kernel.exceptions.agent_exceptions import AgentThreadOperationException
from typing_extensions import override
from v3.callbacks.response_handlers import (agent_response_callback,
                                            streaming_agent_response_callback)
from v3.config.settings import connection_config, orchestration_config
from v3.models.messages import (UserClarificationRequest,
                                UserClarificationResponse, WebsocketMessageType)

# Initialize logger for the module
logger = logging.getLogger(__name__)


class DummyAgentThread(AgentThread):
    """Dummy thread implementation for proxy agent."""

    def __init__(
        self, chat_history: ChatHistory | None = None, thread_id: str | None = None
    ):
        super().__init__()
        self._chat_history = chat_history if chat_history is not None else ChatHistory()
        self._id: str = thread_id or f"thread_{uuid.uuid4().hex}"
        self._is_deleted = False
        self.logger = logging.getLogger(__name__)

    @override
    async def _create(self) -> str:
        """Starts the thread and returns its ID."""
        return self._id

    @override
    async def _delete(self) -> None:
        """Ends the current thread."""
        self._chat_history.clear()

    @override
    async def _on_new_message(self, new_message: str | ChatMessageContent) -> None:
        """Called when a new message has been contributed to the chat."""
        if isinstance(new_message, str):
            new_message = ChatMessageContent(role=AuthorRole.USER, content=new_message)

        if (
            not new_message.metadata
            or "thread_id" not in new_message.metadata
            or new_message.metadata["thread_id"] != self._id
        ):
            self._chat_history.add_message(new_message)

    async def get_messages(self) -> AsyncIterable[ChatMessageContent]:
        """Retrieve the current chat history.

        Returns:
            An async iterable of ChatMessageContent.
        """
        if self._is_deleted:
            raise AgentThreadOperationException(
                "Cannot retrieve chat history, since the thread has been deleted."
            )
        if self._id is None:
            await self.create()
        for message in self._chat_history.messages:
            yield message

    async def reduce(self) -> ChatHistory | None:
        """Reduce the chat history to a smaller size."""
        if self._id is None:
            raise AgentThreadOperationException(
                "Cannot reduce chat history, since the thread is not currently active."
            )
        if not isinstance(self._chat_history, ChatHistoryReducer):
            return None
        return await self._chat_history.reduce()


class ProxyAgentResponseItem:
    """Response item wrapper for proxy agent responses."""

    def __init__(self, message: ChatMessageContent, thread: AgentThread):
        self.message = message
        self.thread = thread
        self.logger = logging.getLogger(__name__)


class ProxyAgent(Agent):
    """Simple proxy agent that prompts for human clarification."""

    # Declare as Pydantic field
    user_id: str = Field(
        default=None, description="User ID for WebSocket messaging"
    )

    def __init__(self, user_id: str, **kwargs):
        # Get user_id from parameter, fallback to empty string
        effective_user_id = user_id or ""
        super().__init__(
            name="ProxyAgent",
            description="Call this agent when you need to clarify requests by asking the human user for more information. Ask it for more details about any unclear requirements, missing information, or if you need the user to elaborate on any aspect of the task.",
            user_id=effective_user_id,
            **kwargs,
        )
        self.instructions = ""

    def _create_message_content(
        self, content: str, thread_id: str = None
    ) -> ChatMessageContent:
        """Create a ChatMessageContent with proper metadata."""
        return ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content=content,
            name=self.name,
            metadata={"thread_id": thread_id} if thread_id else {},
        )

    async def _trigger_response_callbacks(self, message_content: ChatMessageContent):
        """Manually trigger the same response callbacks used by other agents."""
        # Get current user_id dynamically instead of using stored value
        current_user = self.user_id or ""

        # Trigger the standard agent response callback
        agent_response_callback(message_content, current_user)

    async def _trigger_streaming_callbacks(self, content: str, is_final: bool = False):
        """Manually trigger streaming callbacks for real-time updates."""
        # Get current user_id dynamically instead of using stored value
        current_user = self.user_id or ""
        streaming_message = StreamingChatMessageContent(
            role=AuthorRole.ASSISTANT, content=content, name=self.name, choice_index=0
        )
        await streaming_agent_response_callback(
            streaming_message, is_final, current_user
        )

    async def invoke(
        self, message: str, *, thread: AgentThread | None = None, **kwargs
    ) -> AsyncIterator[ChatMessageContent]:
        """Ask human user for clarification about the message."""

        thread = await self._ensure_thread_exists_with_messages(
            messages=message,
            thread=thread,
            construct_thread=lambda: DummyAgentThread(),
            expected_type=DummyAgentThread,
        )

        # Send clarification request via streaming callbacks
        clarification_request = f"I need clarification about: {message}"

        clarification_message = UserClarificationRequest(
            question=clarification_request,
            request_id=str(uuid.uuid4()),  # Unique ID for the request
        )

        # Send the approval request to the user's WebSocket
        await connection_config.send_status_update_async(
            {
                "type": WebsocketMessageType.USER_CLARIFICATION_REQUEST,
                "data": clarification_message,
            },
            user_id=self.user_id,
            message_type=WebsocketMessageType.USER_CLARIFICATION_REQUEST,
        )

        # Get human input
        human_response = await self._wait_for_user_clarification(
            clarification_message.request_id
        )

        # Handle silent timeout/cancellation
        if human_response is None:
            # Process was terminated silently - don't yield any response
            logger.debug("Clarification process terminated silently - ending invoke")
            return

        # Extract the answer from the response
        answer = human_response.answer if human_response else "No additional clarification provided."

        response = f"Human clarification: {answer}"

        chat_message = self._create_message_content(response, thread.id)

        yield AgentResponseItem(message=chat_message, thread=thread)

    async def invoke_stream(
        self, messages, thread=None, **kwargs
    ) -> AsyncIterator[ProxyAgentResponseItem]:
        """Stream version - handles thread management for orchestration."""

        thread = await self._ensure_thread_exists_with_messages(
            messages=messages,
            thread=thread,
            construct_thread=lambda: DummyAgentThread(),
            expected_type=DummyAgentThread,
        )

        # Extract message content
        if isinstance(messages, list) and messages:
            message = (
                messages[-1].content
                if hasattr(messages[-1], "content")
                else str(messages[-1])
            )
        elif isinstance(messages, str):
            message = messages
        else:
            message = str(messages)

        # Send clarification request via streaming callbacks
        clarification_request = f"I need clarification about: {message}"

        clarification_message = UserClarificationRequest(
            question=clarification_request,
            request_id=str(uuid.uuid4()),  # Unique ID for the request
        )

        # Send the approval request to the user's WebSocket
        # The user_id will be automatically retrieved from context
        await connection_config.send_status_update_async(
            {
                "type": WebsocketMessageType.USER_CLARIFICATION_REQUEST,
                "data": clarification_message,
            },
            user_id=self.user_id,
            message_type=WebsocketMessageType.USER_CLARIFICATION_REQUEST,
        )

        # Get human input - replace with websocket call when available
        human_response = await self._wait_for_user_clarification(
            clarification_message.request_id
        )

        # Handle silent timeout/cancellation
        if human_response is None:
            # Process was terminated silently - don't yield any response
            logger.debug("Clarification process terminated silently - ending invoke_stream")
            return

        # Extract the answer from the response
        answer = human_response.answer if human_response else "No additional clarification provided."

        response = f"Human clarification: {answer}"

        chat_message = self._create_message_content(response, thread.id)

        yield AgentResponseItem(message=chat_message, thread=thread)

    async def _wait_for_user_clarification(
        self, request_id: str
    ) -> Optional[UserClarificationResponse]:
        """
        Wait for user clarification response using event-driven pattern with timeout handling.

        Args:
            request_id: The request ID to wait for clarification

        Returns:
            UserClarificationResponse: Clarification result with request ID and answer

        Raises:
            asyncio.TimeoutError: If timeout is exceeded (300 seconds default)
        """
        # logger.info(f"Waiting for user clarification for request: {request_id}")

        # Initialize clarification as pending using the new event-driven method
        orchestration_config.set_clarification_pending(request_id)

        try:
            # Wait for clarification with timeout using the new event-driven method
            answer = await orchestration_config.wait_for_clarification(request_id)

            # logger.info(f"Clarification received for request {request_id}: {answer}")
            return UserClarificationResponse(
                request_id=request_id,
                answer=answer,
            )
        except asyncio.TimeoutError:
            # Enhanced timeout handling - notify user via WebSocket and cleanup
            logger.debug(f"Clarification timeout for request {request_id} - notifying user and terminating process")

            # Create timeout notification message
            from v3.models.messages import TimeoutNotification, WebsocketMessageType
            timeout_notification = TimeoutNotification(
                timeout_type="clarification",
                request_id=request_id,
                message=f"User clarification request timed out after {orchestration_config.default_timeout} seconds. Please try again.",
                timestamp=time.time(),
                timeout_duration=orchestration_config.default_timeout
            )

            # Send timeout notification to user via WebSocket
            try:
                await connection_config.send_status_update_async(
                    message=timeout_notification,
                    user_id=self.user_id,
                    message_type=WebsocketMessageType.TIMEOUT_NOTIFICATION,
                )
                logger.info(f"Timeout notification sent to user {self.user_id} for clarification {request_id}")
            except Exception as e:
                logger.error(f"Failed to send timeout notification: {e}")

            # Clean up this specific request
            orchestration_config.cleanup_clarification(request_id)

            # Return None to indicate silent termination
            # The timeout naturally stops this specific wait operation without affecting other tasks
            return None

        except KeyError as e:
            # Silent error handling for invalid request IDs
            logger.debug(f"Request ID not found: {e} - terminating process silently")
            return None

        except asyncio.CancelledError:
            # Handle task cancellation gracefully
            logger.debug(f"Clarification request {request_id} was cancelled")
            orchestration_config.cleanup_clarification(request_id)
            return None

        except Exception as e:
            # Silent error handling for unexpected errors
            logger.debug(f"Unexpected error waiting for clarification: {e} - terminating process silently")
            orchestration_config.cleanup_clarification(request_id)
            return None
        finally:
            # Ensure cleanup happens for any incomplete requests
            # This provides an additional safety net for resource cleanup
            if (request_id in orchestration_config.clarifications and orchestration_config.clarifications[request_id] is None):
                logger.debug(f"Final cleanup for pending clarification request {request_id}")
                orchestration_config.cleanup_clarification(request_id)

    async def get_response(self, chat_history, **kwargs):
        """Get response from the agent - required by Agent base class."""
        # Extract the latest user message
        latest_message = (
            chat_history.messages[-1].content if chat_history.messages else ""
        )

        # Use our invoke method to get the response
        async for response in self.invoke(latest_message, **kwargs):
            return response

        # Fallback if no response generated
        return ChatMessageContent(
            role=AuthorRole.ASSISTANT, content="No clarification provided."
        )


async def create_proxy_agent(user_id: str = None):
    """Factory function for human proxy agent."""
    return ProxyAgent(user_id=user_id)

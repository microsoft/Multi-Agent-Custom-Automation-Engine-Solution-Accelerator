"""ImageAgent: Calls Azure OpenAI image generation and pushes the image directly to the user via WebSocket."""

from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncIterable, Awaitable

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    BaseAgent,
    Message,
    Content,
    UsageDetails,
    AgentSession,
)
from agent_framework._types import ResponseStream
from azure.identity import get_bearer_token_provider
from openai import AsyncAzureOpenAI

from common.config.app_config import config
from v4.config.settings import connection_config
from v4.models.messages import AgentMessage, WebsocketMessageType

logger = logging.getLogger(__name__)

# API version required for gpt-image-1
_IMAGE_API_VERSION = "2025-04-01-preview"


class ImageAgent(BaseAgent):
    """
    Agent that generates images via Azure OpenAI's images API and returns
    the result as a markdown inline image for rendering on the frontend.

    Expected content format returned to the orchestrator:
        ![Generated Image](data:image/png;base64,<b64_data>)
    """

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        deployment_name: str,
        user_id: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(name=agent_name, description=agent_description, **kwargs)
        self.agent_name = agent_name
        self.deployment_name = deployment_name
        self.user_id = user_id or ""
        self._openai_client: AsyncAzureOpenAI | None = None

    def _get_client(self) -> AsyncAzureOpenAI:
        """Lazily create and cache the Azure OpenAI async client."""
        if self._openai_client is None:
            token_provider = get_bearer_token_provider(
                config.get_azure_credential(config.AZURE_CLIENT_ID),
                "https://cognitiveservices.azure.com/.default",
            )
            self._openai_client = AsyncAzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
                api_version=_IMAGE_API_VERSION,
            )
        return self._openai_client

    def create_session(self, *, session_id: str | None = None, **kwargs: Any) -> AgentSession:
        return AgentSession(session_id=session_id, **kwargs)

    def run(
        self,
        messages: str | Message | list[str] | list[Message] | None = None,
        *,
        stream: bool = False,
        session: AgentSession | None = None,
        **kwargs: Any,
    ) -> Awaitable[AgentResponse] | ResponseStream[AgentResponseUpdate, AgentResponse]:
        if stream:
            return ResponseStream(
                self._invoke_stream(messages),
                finalizer=lambda updates: AgentResponse.from_updates(updates),
            )

        async def _run_non_streaming() -> AgentResponse:
            response_messages: list[Message] = []
            response_id = str(uuid.uuid4())
            async for update in self._invoke_stream(messages):
                if update.contents:
                    response_messages.append(
                        Message(role=update.role or "assistant", contents=update.contents)
                    )
            return AgentResponse(messages=response_messages, response_id=response_id)

        return _run_non_streaming()

    async def _invoke_stream(
        self,
        messages: str | Message | list[str] | list[Message] | None,
    ) -> AsyncIterable[AgentResponseUpdate]:
        prompt = self._extract_message_text(messages)
        response_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        logger.info(
            "ImageAgent '%s': generating image with deployment '%s', prompt length=%d",
            self.agent_name,
            self.deployment_name,
            len(prompt),
        )

        try:
            client = self._get_client()
            result = await client.images.generate(
                model=self.deployment_name,
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="b64_json",
            )

            b64_data = result.data[0].b64_json
            if not b64_data:
                raise ValueError("Image generation returned empty b64_json")

            logger.info(
                "ImageAgent '%s': image generated successfully (%d base64 chars)",
                self.agent_name,
                len(b64_data),
            )

            # Send the image DIRECTLY to the user via WebSocket.
            # The base64 string is ~100K tokens — far too large to pass back through
            # the agent conversation context (the manager LLM would hit its context window).
            # By pushing it straight to the WebSocket we guarantee the user sees the image
            # while the orchestrator only receives a short acknowledgement.
            image_markdown = f"![Generated Marketing Image](data:image/png;base64,{b64_data})"
            if self.user_id:
                try:
                    img_msg = AgentMessage(
                        agent_name=self.agent_name,
                        timestamp=str(__import__("time").time()),
                        content=image_markdown,
                    )
                    await connection_config.send_status_update_async(
                        img_msg,
                        self.user_id,
                        message_type=WebsocketMessageType.AGENT_MESSAGE,
                    )
                    logger.info("ImageAgent '%s': image sent to user '%s' via WebSocket", self.agent_name, self.user_id)
                except Exception as ws_exc:
                    logger.error("ImageAgent '%s': failed to send image via WebSocket: %s", self.agent_name, ws_exc)

            # Return a short acknowledgement to the orchestrator — NOT the raw base64.
            content_text = (
                "✅ Marketing image generated successfully. "
                "The image has been displayed to the user. "
                "Please proceed with compliance validation of the campaign content."
            )

        except Exception as exc:
            logger.error("ImageAgent '%s': image generation failed: %s", self.agent_name, exc)
            content_text = (
                f"I was unable to generate the image due to an error: {exc}. "
                "Please check that the image generation model is deployed and accessible."
            )

        yield AgentResponseUpdate(
            role="assistant",
            contents=[Content.from_text(content_text)],
            author_name=self.agent_name,
            response_id=response_id,
            message_id=message_id,
        )

    def _extract_message_text(
        self, messages: str | Message | list[str] | list[Message] | None
    ) -> str:
        """Extract a single text string from various message formats."""
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
            if isinstance(messages[0], Message):
                return " ".join(msg.text or "" for msg in messages)
        return str(messages)

"""ImageAgent: Calls Azure OpenAI image generation and pushes the image directly to the user via WebSocket."""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any, AsyncIterable, Awaitable

import aiohttp
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
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.storage.blob import ContentSettings

from common.config.app_config import config
from v4.config.settings import connection_config
from v4.models.messages import AgentMessage, WebsocketMessageType

logger = logging.getLogger(__name__)

# API version required for gpt-image-1
_IMAGE_API_VERSION = "2025-04-01-preview"


async def _upload_image_to_blob(png_bytes: bytes, image_id: str) -> str | None:
    """
    Upload PNG bytes to Azure Blob Storage and return the blob path (not a public URL).
    Returns the blob name on success, None on failure.
    """
    blob_url = config.AZURE_STORAGE_BLOB_URL
    container = config.AZURE_STORAGE_IMAGES_CONTAINER
    if not blob_url:
        logger.warning("AZURE_STORAGE_BLOB_URL not configured; skipping blob upload")
        return None
    try:
        credential = config.get_azure_credential(config.AZURE_CLIENT_ID)
        async with AsyncBlobServiceClient(account_url=blob_url.rstrip("/"), credential=credential) as blob_service:
            container_client = blob_service.get_container_client(container)
            # Create container if it doesn't exist
            try:
                await container_client.create_container()
                logger.info("Created blob container '%s'", container)
            except Exception:
                pass  # Already exists
            blob_name = f"{image_id}.png"
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.upload_blob(
                png_bytes,
                overwrite=True,
                content_settings=ContentSettings(content_type="image/png"),
            )
        logger.info("Uploaded image '%s' to blob container '%s'", blob_name, container)
        return blob_name
    except Exception as exc:
        logger.error("Failed to upload image to blob: %s", exc)
        return None


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
        self._token_provider = get_bearer_token_provider(
            config.get_azure_credential(config.AZURE_CLIENT_ID),
            "https://cognitiveservices.azure.com/.default",
        )

    def _get_image_url(self) -> str:
        """Build the Azure OpenAI images/generations URL for this deployment."""
        endpoint = config.AZURE_OPENAI_ENDPOINT.rstrip("/")
        return (
            f"{endpoint}/openai/deployments/{self.deployment_name}"
            f"/images/generations?api-version={_IMAGE_API_VERSION}"
        )

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
            token = self._token_provider()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            body = {"prompt": prompt, "n": 1, "size": "1024x1024"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._get_image_url(), json=body, headers=headers
                ) as resp:
                    if not resp.ok:
                        error_text = await resp.text()
                        raise ValueError(f"Error code: {resp.status} - {error_text}")
                    result_json = await resp.json()

            b64_data = result_json["data"][0].get("b64_json") or result_json["data"][0].get("b64")
            if not b64_data:
                raise ValueError(f"Image generation returned no b64 data. Response: {result_json}")

            logger.info(
                "ImageAgent '%s': image generated successfully (%d base64 chars)",
                self.agent_name,
                len(b64_data),
            )

            # Upload to blob and send a backend proxy URL instead of raw base64
            image_id = str(uuid.uuid4())
            png_bytes = base64.b64decode(b64_data)
            blob_name = await _upload_image_to_blob(png_bytes, image_id)

            if blob_name:
                backend_url = config.FRONTEND_SITE_NAME.replace(
                    config.FRONTEND_SITE_NAME,
                    (config.FRONTEND_SITE_NAME or "").rstrip("/"),
                )
                # Build the image URL pointing at the backend proxy endpoint
                backend_base = (config.AZURE_AI_AGENT_ENDPOINT or "").rstrip("/")
                # Use BACKEND_URL env var if available, fall back to deriving from endpoint
                import os
                backend_origin = os.environ.get("BACKEND_URL", "").rstrip("/")
                if not backend_origin:
                    backend_origin = backend_base
                image_src = f"{backend_origin}/api/v4/images/{blob_name}"
                image_content = f"![Generated Marketing Image]({image_src})"
            else:
                # Fallback: embed base64 directly
                image_content = f"![Generated Marketing Image](data:image/png;base64,{b64_data})"

            # Send the image URL to the user via WebSocket.
            if self.user_id:
                try:
                    img_msg = AgentMessage(
                        agent_name=self.agent_name,
                        timestamp=str(__import__("time").time()),
                        content=image_content,
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

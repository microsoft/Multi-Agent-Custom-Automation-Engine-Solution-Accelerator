"""
Image generation MCP tools service.

Generates images via Azure OpenAI's images/generations endpoint (gpt-5-mini),
uploads the resulting PNG to Azure Blob Storage, and returns a public URL that
Foundry-hosted agents can embed in their markdown responses.
"""

import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, get_bearer_token_provider
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    PublicAccess,
    generate_blob_sas,
)

from config.settings import config
from core.factory import Domain, MCPToolBase

logger = logging.getLogger(__name__)

_IMAGE_API_VERSION = "2025-04-01-preview"
_SAS_VALIDITY_DAYS = 7


def _get_credential():
    """Return a credential, preferring user-assigned MI when a client id is set."""
    if config.azure_client_id:
        return ManagedIdentityCredential(client_id=config.azure_client_id)
    return DefaultAzureCredential()


def _ensure_public_container(blob_service: BlobServiceClient, container_name: str) -> None:
    """Create the container with blob-level public read access if missing."""
    container_client = blob_service.get_container_client(container_name)
    try:
        container_client.create_container(public_access=PublicAccess.BLOB)
        logger.info("Created public blob container '%s'", container_name)
    except Exception:
        # Container already exists — leave its access level alone.
        pass


def _upload_png_and_get_url(png_bytes: bytes) -> str:
    """Upload PNG bytes to blob storage, return the public URL."""
    if not config.azure_storage_blob_url:
        raise RuntimeError("AZURE_STORAGE_BLOB_URL is not configured on the MCP server")

    account_url = config.azure_storage_blob_url.rstrip("/")
    container_name = config.azure_storage_images_container
    blob_name = f"{uuid.uuid4()}.png"

    credential = _get_credential()
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    _ensure_public_container(blob_service, container_name)

    blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(
        png_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type="image/png"),
    )

    blob_url = f"{account_url}/{container_name}/{blob_name}"
    try:
        now = datetime.now(timezone.utc)
        # User-delegation key requires MI/AAD auth; valid up to 7 days.
        delegation_key = blob_service.get_user_delegation_key(
            key_start_time=now - timedelta(minutes=5),
            key_expiry_time=now + timedelta(days=_SAS_VALIDITY_DAYS),
        )
        sas = generate_blob_sas(
            account_name=blob_service.account_name,
            container_name=container_name,
            blob_name=blob_name,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=now + timedelta(days=_SAS_VALIDITY_DAYS),
            start=now - timedelta(minutes=5),
        )
        return f"{blob_url}?{sas}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to generate user-delegation SAS, returning bare URL: %s", exc)
        return blob_url


class ImageService(MCPToolBase):
    """Image-generation tools backed by Azure OpenAI gpt-5-mini."""

    def __init__(self):
        super().__init__(Domain.IMAGE)

    def register_tools(self, mcp) -> None:
        @mcp.tool(tags={self.domain.value})
        async def generate_marketing_image(prompt: str, size: str = "1024x1024") -> str:
            """Generate a marketing image from a text prompt.

            Use this tool whenever the user asks for an image, picture, photo, banner,
            or visual asset. Pass a detailed description of the scene, subject, style,
            lighting, and composition. The tool returns a public HTTPS URL to the
            generated PNG. Embed the URL in your response using markdown image syntax,
            for example: ![Generated image](<url>).

            Args:
                prompt: A detailed description of the image to generate.
                size: One of "1024x1024", "1024x1792", or "1792x1024". Defaults to square.

            Returns:
                A public HTTPS URL to the generated PNG image.
            """
            if not config.azure_openai_endpoint:
                raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured on the MCP server")

            deployment = config.azure_openai_image_deployment
            endpoint = config.azure_openai_endpoint.rstrip("/")
            url = (
                f"{endpoint}/openai/deployments/{deployment}"
                f"/images/generations?api-version={_IMAGE_API_VERSION}"
            )

            token_provider = get_bearer_token_provider(
                _get_credential(), "https://cognitiveservices.azure.com/.default"
            )
            headers = {
                "Authorization": f"Bearer {token_provider()}",
                "Content-Type": "application/json",
            }
            body = {"prompt": prompt, "n": 1, "size": size}

            logger.info("Generating image (deployment=%s, size=%s, prompt_len=%d)", deployment, size, len(prompt))
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                if resp.status_code >= 400:
                    raise RuntimeError(f"Image generation failed: {resp.status_code} {resp.text}")
                result_json = resp.json()

            data = result_json.get("data") or []
            if not data:
                raise RuntimeError(f"Image generation returned no data: {result_json}")
            b64_data = data[0].get("b64_json") or data[0].get("b64")
            if not b64_data:
                raise RuntimeError(f"Image generation returned no b64 data: {result_json}")

            png_bytes = base64.b64decode(b64_data)
            public_url = _upload_png_and_get_url(png_bytes)
            logger.info("Image uploaded: %s", public_url)
            return public_url

    @property
    def tool_count(self) -> int:
        return 1

"""
Tests for the image-generation MCP service.

Guards that ``generate_marketing_image`` sends the configurable ``quality``
parameter (default ``high``) alongside the requested ``size`` in the outgoing
Azure OpenAI request body, with every Azure touchpoint mocked so no network or
blob access occurs.
"""

from typing import Self

import pytest

pytest.importorskip("fastmcp", reason="fastmcp not installed in backend venv; run with mcp_server venv")

from services import image_service as image_service_mod
from services.image_service import ImageService

# Minimal valid 1x1 PNG. The tool base64-decodes this; upload is mocked so the
# resulting bytes are never persisted.
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
)


class _FakeResponse:
    """Stand-in httpx response with a fixed status code and JSON payload."""

    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self.text = ""
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    """Async-context-manager stand-in for ``httpx.AsyncClient``.

    Captures the ``json=`` body of the POST so the test can assert on it and
    returns a canned successful response.
    """

    def __init__(self, captured: dict, payload: dict) -> None:
        self._captured = captured
        self._payload = payload

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def post(self, url: str, json: dict | None = None, headers: dict | None = None) -> _FakeResponse:
        self._captured["url"] = url
        self._captured["body"] = json
        self._captured["headers"] = headers
        return _FakeResponse(200, self._payload)


@pytest.mark.asyncio
async def test_generate_marketing_image_sends_quality(mock_mcp_server, monkeypatch) -> None:
    """The outgoing request body carries the configured quality and requested size."""
    captured: dict = {}
    payload = {"data": [{"b64_json": _TINY_PNG_B64}]}

    # Mock every Azure touchpoint so no network or blob access happens.
    # ``object`` is callable and returns a fresh dummy credential per call.
    monkeypatch.setattr(image_service_mod, "_get_credential", object)
    monkeypatch.setattr(
        image_service_mod,
        "get_bearer_token_provider",
        lambda *args, **kwargs: (lambda: "dummy-token"),
    )
    monkeypatch.setattr(
        image_service_mod,
        "_upload_png_and_get_url",
        lambda png_bytes: "https://example/img.png",
    )
    monkeypatch.setattr(
        image_service_mod.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(captured, payload),
    )
    monkeypatch.setattr(
        image_service_mod.config,
        "azure_openai_endpoint",
        "https://example-aoai.openai.azure.com",
    )

    # Register the tool on the mock server and locate it by name.
    ImageService().register_tools(mock_mcp_server)
    generate_tool = next(
        tool["func"]
        for tool in mock_mcp_server.tools
        if tool["func"].__name__ == "generate_marketing_image"
    )

    result = await generate_tool("A friendly team celebrating a work anniversary")

    assert captured["body"]["quality"] == "high"
    assert captured["body"]["size"] == "1024x1024"
    assert result.startswith("![")

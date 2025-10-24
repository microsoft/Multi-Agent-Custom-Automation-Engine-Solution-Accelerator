from typing import Any, Dict, Optional

from common.config.app_config import config

from .base_api_service import BaseAPIService


class MCPService(BaseAPIService):
    """Service for interacting with an MCP server.

    Base URL is taken from AppConfig.MCP_SERVER_ENDPOINT if present,
    otherwise falls back to v3 MCP default in settings or localhost.
    """

    def __init__(self, base_url: str, *, token: Optional[str] = None, **kwargs):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        super().__init__(base_url, default_headers=headers, **kwargs)

    @classmethod
    def from_app_config(cls, **kwargs) -> "MCPService":
        # Prefer explicit MCP endpoint if defined; otherwise use the v3 settings default.
        endpoint = config.MCP_SERVER_ENDPOINT
        if not endpoint:
            # fall back to typical local dev default
            return None  # or handle the error appropriately
        token = None  # add token retrieval if you enable auth later
        return cls(endpoint, token=token, **kwargs)

    async def health(self) -> Dict[str, Any]:
        return await self.get_json("health")

    async def invoke_tool(
        self, tool_name: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.post_json(f"tools/{tool_name}", json=payload)

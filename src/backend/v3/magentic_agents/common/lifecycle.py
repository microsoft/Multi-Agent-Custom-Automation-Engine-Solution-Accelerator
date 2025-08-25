import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from azure.ai.projects.aio import AIProjectClient
from azure.identity import InteractiveBrowserCredential
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
from v3.magentic_agents.models.agent_models import MCPConfig


class MCPEnabledBase:
    """
    Base that owns an AsyncExitStack and, if configured, enters the MCP plugin
    as an async context. Subclasses build the actual agent in _after_open().
    """

    def __init__(self, mcp: MCPConfig | None = None) -> None:
        self._stack: AsyncExitStack | None = None
        self.mcp_cfg: MCPConfig = mcp or MCPConfig.from_env()
        self.mcp_plugin: MCPStreamableHttpPlugin | None = None
        self._agent: Any | None = None  # delegate target

    async def open(self) -> "MCPEnabledBase":
        if self._stack is not None:
            return self
        self._stack = AsyncExitStack()
        await self._enter_mcp_if_configured()
        await self._after_open()
        return self

    async def close(self) -> None:
        if self._stack is None:
            return
        try:
            self.cred.close()
            await self._stack.aclose()
        finally:
            self._stack = None
            self.mcp_plugin = None
            self._agent = None

    # Context manager
    async def __aenter__(self) -> "MCPEnabledBase":
        return await self.open()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # Delegate attributes to the built agent
    def __getattr__(self, name: str) -> Any:
        if self._agent is not None:
            return getattr(self._agent, name)
        raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")

    # Hooks
    async def _after_open(self) -> None:
        """Subclasses must build self._agent here."""
        raise NotImplementedError

    # Internals
    def _build_mcp_headers(self) -> dict:
        if not self.mcp_cfg.client_id:
            return {}
        self.cred = InteractiveBrowserCredential(
            tenant_id=self.mcp_cfg.tenant_id or None,
            client_id=self.mcp_cfg.client_id,
        )
        tok = self.cred.get_token(f"api://{self.mcp_cfg.client_id}/access_as_user")
        return {
            "Authorization": f"Bearer {tok.token}",
            "Content-Type": "application/json",
        }

    async def _enter_mcp_if_configured(self) -> None:
        if not self.mcp_cfg.url:
            return
        # Note: had this commented out in my testing because I don't have
        # access to your resources
        headers = self._build_mcp_headers()
        plugin = MCPStreamableHttpPlugin(
            name=self.mcp_cfg.name,
            description=self.mcp_cfg.description,
            url=self.mcp_cfg.url,
            headers=headers,
        )
        # Enter MCP async context via the stack to ensure correct LIFO cleanup
        if self._stack is None:
            self._stack = AsyncExitStack()
        self.mcp_plugin = await self._stack.enter_async_context(plugin)


class AzureAgentBase(MCPEnabledBase):
    """
    Extends MCPEnabledBase with Azure async contexts that many agents need:
    - DefaultAzureCredential (async)
    - AzureAIAgent.create_client(...) (async)
    Subclasses then create an AzureAIAgent definition and bind plugins.
    """

    def __init__(self, mcp: MCPConfig | None = None) -> None:
        super().__init__(mcp=mcp)
        self.creds: DefaultAzureCredential | None = None
        self.client: AIProjectClient | None = None

    async def open(self) -> "AzureAgentBase":
        if self._stack is not None:
            return self
        self._stack = AsyncExitStack()
        # Azure async contexts
        self.creds = DefaultAzureCredential()
        await self._stack.enter_async_context(self.creds)
        self.client = AzureAIAgent.create_client(credential=self.creds)
        await self._stack.enter_async_context(self.client)

        # MCP async context if requested
        await self._enter_mcp_if_configured()

        # Build the agent
        await self._after_open()
        return self

    async def close(self) -> None:
        await self.creds.close()
        await super().close()
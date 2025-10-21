from __future__ import annotations

import os
from contextlib import AsyncExitStack
from typing import Any, Optional

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

from agent_framework.azure import AzureAIAgentClient
from agent_framework import HostedMCPTool

from af.magentic_agents.models.agent_models import MCPConfig
from af.config.agent_registry import agent_registry


class MCPEnabledBase:
    """
    Base that owns an AsyncExitStack and (optionally) prepares an MCP tool
    for subclasses to attach to ChatOptions (agent_framework style).
    Subclasses must implement _after_open() and assign self._agent.
    """

    def __init__(self, mcp: MCPConfig | None = None) -> None:
        self._stack: AsyncExitStack | None = None
        self.mcp_cfg: MCPConfig | None = mcp
        self.mcp_tool: HostedMCPTool | None = None
        self._agent: Any | None = None  # delegate target (e.g., AzureAIAgentClient)

    async def open(self) -> "MCPEnabledBase":
        if self._stack is not None:
            return self
        self._stack = AsyncExitStack()
        self._prepare_mcp_tool()
        await self._after_open()
        return self

    async def close(self) -> None:
        if self._stack is None:
            return
        try:
            # Attempt to close the underlying agent/client if it exposes close()
            if self._agent and hasattr(self._agent, "close"):
                try:
                    await self._agent.close()  # AzureAIAgentClient has async close
                except Exception:  # noqa: BLE001
                    pass
            # Unregister from registry if present
            try:
                agent_registry.unregister_agent(self)
            except Exception:  # noqa: BLE001
                pass
            await self._stack.aclose()
        finally:
            self._stack = None
            self.mcp_tool = None
            self._agent = None

    # Context manager
    async def __aenter__(self) -> "MCPEnabledBase":
        return await self.open()

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        await self.close()

    # Delegate to underlying agent
    def __getattr__(self, name: str) -> Any:
        if self._agent is not None:
            return getattr(self._agent, name)
        raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")

    async def _after_open(self) -> None:
        """Subclasses must build self._agent here."""
        raise NotImplementedError

    def _prepare_mcp_tool(self) -> None:
        """Translate MCPConfig to a HostedMCPTool (agent_framework construct)."""
        if not self.mcp_cfg:
            return
        try:
            self.mcp_tool = HostedMCPTool(
                name=self.mcp_cfg.name,
                description=self.mcp_cfg.description,
                server_label=self.mcp_cfg.name.replace(" ", "_"),
                url="",  # URL will be resolved via MCPConfig in HostedMCPTool
            )
        except Exception:  # noqa: BLE001
            self.mcp_tool = None


class AzureAgentBase(MCPEnabledBase):
    """
    Extends MCPEnabledBase with Azure credential + AIProjectClient contexts.
    Subclasses:
      - create or attach an Azure AI Agent definition
      - instantiate an AzureAIAgentClient and assign to self._agent
      - optionally register themselves via agent_registry
    """

    def __init__(self, mcp: MCPConfig | None = None) -> None:
        super().__init__(mcp=mcp)
        self.creds: Optional[DefaultAzureCredential] = None
        self.client: Optional[AIProjectClient] = None
        self.project_endpoint: Optional[str] = None
        self._created_ephemeral: bool = False  # reserved if you add ephemeral agent cleanup

    async def open(self) -> "AzureAgentBase":
        if self._stack is not None:
            return self
        self._stack = AsyncExitStack()

        # Resolve Azure AI Project endpoint (mirrors old SK env var usage)
        self.project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        if not self.project_endpoint:
            raise RuntimeError(
                "AZURE_AI_PROJECT_ENDPOINT environment variable is required for AzureAgentBase."
            )

        # Acquire credential
        self.creds = DefaultAzureCredential()
        await self._stack.enter_async_context(self.creds)

        # Create AIProjectClient
        self.client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=self.creds,
        )
        await self._stack.enter_async_context(self.client)

        # Prepare MCP
        self._prepare_mcp_tool()

        # Let subclass build agent client
        await self._after_open()

        # Register agent (best effort)
        try:
            agent_registry.register_agent(self)
        except Exception:  # noqa: BLE001
            pass

        return self

    async def close(self) -> None:
        """
        Close agent client and Azure resources.
        If you implement ephemeral agent creation in subclasses, you can
        optionally delete the agent definition here.
        """
        try:
            # Example optional clean up of an agent id:
            # if self._agent and isinstance(self._agent, AzureAIAgentClient) and self._agent._should_delete_agent:
            #     try:
            #         if self.client and self._agent.agent_id:
            #             await self.client.agents.delete_agent(self._agent.agent_id)
            #     except Exception:
            #         pass

            # Close underlying client via base close
            if self._agent and hasattr(self._agent, "close"):
                try:
                    await self._agent.close()
                except Exception:  # noqa: BLE001
                    pass

            # Unregister from registry
            try:
                agent_registry.unregister_agent(self)
            except Exception:  # noqa: BLE001
                pass

            # Close credential and project client
            if self.client:
                try:
                    await self.client.close()
                except Exception:  # noqa: BLE001
                    pass
            if self.creds:
                try:
                    await self.creds.close()
                except Exception:  # noqa: BLE001
                    pass

        finally:
            await super().close()
            self.client = None
            self.creds = None
            self.project_endpoint = None

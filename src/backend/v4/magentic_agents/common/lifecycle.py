from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import Any, Optional

from agent_framework import (
    ChatAgent,
    HostedMCPTool,
    MCPStreamableHTTPTool,
)

# from agent_framework.azure import AzureAIClient
from agent_framework_azure_ai import AzureAIClient
from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import DefaultAzureCredential
from common.database.database_base import DatabaseBase
from common.models.messages_af import CurrentTeamAgent, TeamConfiguration
from common.utils.utils_agents import (
    generate_assistant_id,
    get_database_team_agent_id,
)
from v4.common.services.team_service import TeamService
from v4.config.agent_registry import agent_registry
from v4.magentic_agents.models.agent_models import MCPConfig


class MCPEnabledBase:
    """
    Base that owns an AsyncExitStack and (optionally) prepares an MCP tool
    for subclasses to attach to ChatOptions (agent_framework style).
    Subclasses must implement _after_open() and assign self._agent.
    """

    def __init__(
        self,
        mcp: MCPConfig | None = None,
        team_service: TeamService | None = None,
        team_config: TeamConfiguration | None = None,
        project_endpoint: str | None = None,
        memory_store: DatabaseBase | None = None,
        agent_name: str | None = None,
        agent_description: str | None = None,
        agent_instructions: str | None = None,
        model_deployment_name: str | None = None,
        project_client=None,
    ) -> None:
        self._stack: AsyncExitStack | None = None
        self.mcp_cfg: MCPConfig | None = mcp
        self.mcp_tool: HostedMCPTool | None = None
        self._agent: ChatAgent | None = None
        self.team_service: TeamService | None = team_service
        self.team_config: TeamConfiguration | None = team_config
        self.client: Optional[AzureAIClient] = None
        self.project_endpoint = project_endpoint
        self.creds: Optional[DefaultAzureCredential] = None
        self.memory_store: Optional[DatabaseBase] = memory_store
        self.agent_name: str | None = agent_name
        self.agent_description: str | None = agent_description
        self.agent_instructions: str | None = agent_instructions
        self.model_deployment_name: str | None = model_deployment_name
        self.project_client = project_client
        self.logger = logging.getLogger(__name__)

    async def open(self) -> "MCPEnabledBase":
        if self._stack is not None:
            return self
        self._stack = AsyncExitStack()

        # Acquire credential
        self.creds = DefaultAzureCredential()
        if self._stack:
            await self._stack.enter_async_context(self.creds)
        # Create AgentsClient
        self.client = AgentsClient(
            endpoint=self.project_endpoint,
            credential=self.creds,
        )
        if self._stack:
            await self._stack.enter_async_context(self.client)
        # Prepare MCP
        await self._prepare_mcp_tool()

        # Let subclass build agent client
        await self._after_open()

        # Register agent (best effort)
        try:
            agent_registry.register_agent(self)
        except Exception as exc:
            # Best-effort registration; log and continue without failing open()
            self.logger.warning(
                "Failed to register agent %s in agent_registry: %s",
                type(self).__name__,
                exc,
                exc_info=True,
            )

        return self

    async def close(self) -> None:
        if self._stack is None:
            return
        try:
            # Attempt to close the underlying agent/client if it exposes close()
            if self._agent and hasattr(self._agent, "close"):
                try:
                    await self._agent.close()  # AzureAIClient has async close
                except Exception as exc:
                    # Best-effort close; log failure but continue teardown
                    self.logger.warning(
                        "Error while closing underlying agent %s: %s",
                        type(self._agent).__name__ if self._agent else "Unknown",
                        exc,
                        exc_info=True,
                    )
            # Unregister from registry if present
            try:
                agent_registry.unregister_agent(self)
            except Exception as exc:
                # Best-effort unregister; log and continue teardown
                self.logger.warning(
                    "Failed to unregister agent %s from agent_registry: %s",
                    type(self).__name__,
                    exc,
                    exc_info=True,
                )
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

    def get_chat_client(self, chat_client) -> AzureAIClient:
        """Return the underlying ChatClientProtocol (AzureAIClient)."""
        if chat_client:
            return chat_client
        if (
            self._agent
            and self._agent.chat_client
        ):
            return self._agent.chat_client  # type: ignore
        chat_client = AzureAIClient(
            project_endpoint=self.project_endpoint,
            model_deployment_name=self.model_deployment_name,
            credential=self.creds,
        )
        self.logger.info(
            "Created new AzureAIClient for get chat client",
        )
        return chat_client

    async def resolve_agent_id(self, agent_id: str) -> Optional[str]:
        """Resolve agent ID via Projects SDK first (for RAI agents), fallback to AgentsClient.

        Args:
            agent_id: The agent ID to resolve

        Returns:
            The resolved agent ID if found, None otherwise
        """
        # Try Projects SDK first (RAI agents were created via project_client)
        try:
            if self.project_client:
                agent = await self.project_client.agents.get_agent(agent_id)
                if agent and agent.id:
                    self.logger.info(
                        "RAI.AgentReuseSuccess: Resolved agent via Projects SDK (id=%s)",
                        agent.id,
                    )
                    return agent.id
        except Exception as ex:
            self.logger.warning(
                "RAI.AgentReuseMiss: Projects SDK get_agent failed (reason=ProjectsGetFailed, id=%s): %s",
                agent_id,
                ex,
            )

        # Fallback via AgentsClient (endpoint)
        try:
            if self.client:
                agent = await self.client.get_agent(agent_id=agent_id)
                if agent and agent.id:
                    self.logger.info(
                        "RAI.AgentReuseSuccess: Resolved agent via AgentsClient (id=%s)",
                        agent.id,
                    )
                    return agent.id
        except Exception as ex:
            self.logger.warning(
                "RAI.AgentReuseMiss: AgentsClient get_agent failed (reason=EndpointGetFailed, id=%s): %s",
                agent_id,
                ex,
            )

        self.logger.error(
            "RAI.AgentReuseMiss: Agent ID not resolvable via any client (reason=ClientMismatch, id=%s)",
            agent_id,
        )
        return None

    def get_agent_id(self, chat_client) -> str:
        """Return the underlying agent ID or generate a new one.
        
        Note: The new AzureAIClient doesn't expose agent_id directly.
        We generate a new ID if not available.
        """
        # Generate a new agent ID since AzureAIClient doesn't expose agent_id
        id = generate_assistant_id()
        self.logger.info("Generated new agent ID: %s", id)
        return id

    async def get_database_team_agent(self) -> Optional[AzureAIClient]:
        """Retrieve existing team agent from database, if any."""
        chat_client = None
        try:
            agent_id = await get_database_team_agent_id(
                self.memory_store, self.team_config, self.agent_name
            )

            if not agent_id:
                self.logger.info(
                    "RAI reuse: no stored agent id (agent_name=%s)", self.agent_name
                )
                return None

            # Use resolve_agent_id to try Projects SDK first, then AgentsClient
            resolved = await self.resolve_agent_id(agent_id)
            if not resolved:
                self.logger.error(
                    "RAI.AgentReuseMiss: stored id %s not resolvable (agent_name=%s)",
                    agent_id,
                    self.agent_name,
                )
                return None

            # Create client with resolved ID, preferring project_client for RAI agents
            if self.agent_name == "RAIAgent" and self.project_client:
                chat_client = AzureAIClient(
                    project_client=self.project_client,
                    agent_id=resolved,
                    credential=self.creds,
                )
                self.logger.info(
                    "RAI.AgentReuseSuccess: Created AzureAIClient via Projects SDK (id=%s)",
                    resolved,
                )
            else:
                chat_client = AzureAIClient(
                    project_endpoint=self.project_endpoint,
                    agent_id=resolved,
                    model_deployment_name=self.model_deployment_name,
                    credential=self.creds,
                )
                self.logger.info(
                    "Created AzureAIClient via endpoint (id=%s)", resolved
                )

        except Exception as ex:
            self.logger.error(
                "Failed to initialize Get database team agent (agent_name=%s): %s",
                self.agent_name,
                ex,
            )
        return chat_client

    async def save_database_team_agent(self) -> None:
        """Save current team agent to database (only if truly new or changed)."""
        try:
            if self._agent.id is None:
                self.logger.error("Cannot save database team agent: agent_id is None")
                return

            # Check if stored ID matches current ID
            stored_id = await get_database_team_agent_id(
                self.memory_store, self.team_config, self.agent_name
            )
            if stored_id == self._agent.chat_client.agent_id:
                self.logger.info(
                    "RAI reuse: id unchanged (id=%s); skip save.", self._agent.id
                )
                return

            currentAgent = CurrentTeamAgent(
                team_id=self.team_config.team_id,
                team_name=self.team_config.name,
                agent_name=self.agent_name,
                agent_foundry_id=self._agent.chat_client.agent_id,
                agent_description=self.agent_description,
                agent_instructions=self.agent_instructions,
            )
            await self.memory_store.add_team_agent(currentAgent)
            self.logger.info(
                "Saved team agent to database (agent_name=%s, id=%s)",
                self.agent_name,
                self._agent.id,
            )

        except Exception as ex:
            self.logger.error("Failed to save database: %s", ex)

    async def _prepare_mcp_tool(self) -> None:
        """Translate MCPConfig to a HostedMCPTool (agent_framework construct)."""
        if not self.mcp_cfg:
            return
        try:
            mcp_tool = MCPStreamableHTTPTool(
                name=self.mcp_cfg.name,
                description=self.mcp_cfg.description,
                url=self.mcp_cfg.url,
            )
            await self._stack.enter_async_context(mcp_tool)
            self.mcp_tool = mcp_tool  # Store for later use
        except Exception:
            self.mcp_tool = None


class AzureAgentBase(MCPEnabledBase):
    """
    Extends MCPEnabledBase with Azure credential + AzureAIClient contexts.
    Subclasses:
      - create or attach an Azure AI Agent definition
      - instantiate an AzureAIClient and assign to self._agent
      - optionally register themselves via agent_registry
    """

    def __init__(
        self,
        mcp: MCPConfig | None = None,
        model_deployment_name: str | None = None,
        project_endpoint: str | None = None,
        team_service: TeamService | None = None,
        team_config: TeamConfiguration | None = None,
        memory_store: DatabaseBase | None = None,
        agent_name: str | None = None,
        agent_description: str | None = None,
        agent_instructions: str | None = None,
        project_client=None,
    ) -> None:
        super().__init__(
            mcp=mcp,
            team_service=team_service,
            team_config=team_config,
            project_endpoint=project_endpoint,
            memory_store=memory_store,
            agent_name=agent_name,
            agent_description=agent_description,
            agent_instructions=agent_instructions,
            model_deployment_name=model_deployment_name,
            project_client=project_client,
        )

        self._created_ephemeral: bool = (
            False  # reserved if you add ephemeral agent cleanup
        )

    # async def open(self) -> "AzureAgentBase":
    #     if self._stack is not None:
    #         return self
    #     self._stack = AsyncExitStack()

    #     # Acquire credential
    #     self.creds = DefaultAzureCredential()
    #     if self._stack:
    #         await self._stack.enter_async_context(self.creds)
    #     # Create AgentsClient
    #     self.client = AgentsClient(
    #         endpoint=self.project_endpoint,
    #         credential=self.creds,
    #     )
    #     if self._stack:
    #         await self._stack.enter_async_context(self.client)
    #     # Prepare MCP
    #     await self._prepare_mcp_tool()

    #     # Let subclass build agent client
    #     await self._after_open()

    #     # Register agent (best effort)
    #     try:
    #         agent_registry.register_agent(self)
    #     except Exception:
    #         pass

    #     return self

    async def close(self) -> None:
        """
        Close agent client and Azure resources.
        If you implement ephemeral agent creation in subclasses, you can
        optionally delete the agent definition here.
        """
        try:

            # Close underlying client via base close
            if self._agent and hasattr(self._agent, "close"):
                try:
                    await self._agent.close()
                except Exception as exc:
                    logging.warning("Failed to close underlying agent %r: %s", self._agent, exc, exc_info=True)

            # Unregister from registry
            try:
                agent_registry.unregister_agent(self)
            except Exception as exc:
                logging.warning("Failed to unregister agent %r from registry: %s", self, exc, exc_info=True)

            # Close credential and project client
            if self.client:
                try:
                    await self.client.close()
                except Exception as exc:
                    logging.warning("Failed to close Azure AgentsClient %r: %s", self.client, exc, exc_info=True)
            if self.creds:
                try:
                    await self.creds.close()
                except Exception as exc:
                    logging.warning("Failed to close credentials %r: %s", self.creds, exc, exc_info=True)

        finally:
            await super().close()
            self.client = None
            self.creds = None
            self.project_endpoint = None

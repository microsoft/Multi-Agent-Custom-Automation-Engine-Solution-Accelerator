from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import Any, Optional

from agent_framework import (
    ChatAgent,
    HostedMCPTool,
    MCPStreamableHTTPTool,
)

# from agent_framework.azure import AzureAIAgentClient
from agent_framework_azure_ai import AzureAIAgentClient
from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import DefaultAzureCredential
from common.config.app_config import config
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
    ) -> None:
        self._stack: AsyncExitStack | None = None
        self.mcp_cfg: MCPConfig | None = mcp
        self.mcp_tool: HostedMCPTool | None = None
        self._agent: ChatAgent | None = None
        self.team_service: TeamService | None = team_service
        self.team_config: TeamConfiguration | None = team_config
        self.client: Optional[AzureAIAgentClient] = None
        self.project_endpoint = project_endpoint
        self.creds: Optional[DefaultAzureCredential] = None
        self.memory_store: Optional[DatabaseBase] = memory_store
        self.agent_name: str | None = agent_name
        self.agent_description: str | None = agent_description
        self.agent_instructions: str | None = agent_instructions
        self.model_deployment_name: str | None = model_deployment_name
        self.logger = logging.getLogger(__name__)
        # Initialize project_client for RAI agent reuse (used in resolve_agent_id)
        self.project_client = None

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

        # Initialize project_client for RAI agent reuse (Projects SDK)
        # This is used by resolve_agent_id to retrieve agents created via Projects SDK
        if not self.project_client:
            try:
                self.project_client = config.get_ai_project_client()
                self.logger.info("Initialized project_client for RAI agent reuse.")
            except Exception as ex:
                self.logger.warning("Failed to initialize project_client: %s", ex)

        # Prepare MCP
        await self._prepare_mcp_tool()

        # Let subclass build agent client
        await self._after_open()

        # Register agent (best effort)
        try:
            agent_registry.register_agent(self)
        except Exception:
            pass

        return self

    async def close(self) -> None:
        if self._stack is None:
            return
        try:
            # Attempt to close the underlying agent/client if it exposes close()
            if self._agent and hasattr(self._agent, "close"):
                try:
                    await self._agent.close()  # AzureAIAgentClient has async close
                except Exception:
                    pass
            # Unregister from registry if present
            try:
                agent_registry.unregister_agent(self)
            except Exception:
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

    def get_chat_client(self, chat_client) -> AzureAIAgentClient:
        """Return the underlying ChatClientProtocol (AzureAIAgentClient)."""
        if chat_client:
            return chat_client
        if (
            self._agent
            and self._agent.chat_client
            and self._agent.chat_client.agent_id is not None
        ):
            return self._agent.chat_client  # type: ignore
        chat_client = AzureAIAgentClient(
            project_endpoint=self.project_endpoint,
            model_deployment_name=self.model_deployment_name,
            async_credential=self.creds,
        )
        self.logger.info(
            "Created new AzureAIAgentClient for  get chat client",
            extra={"agent_id": chat_client.agent_id},
        )
        return chat_client

    async def resolve_agent_id(self, agent_id: str) -> Optional[str]:
        """Resolve agent ID via Projects SDK first, fallback to AgentsClient.

        RAI agents are created via Projects SDK (project_client), so we try that first.
        If that fails, fall back to the endpoint-based AgentsClient.

        Returns:
            Resolved agent ID if found, None otherwise.
        """
        # Try Projects SDK first (for RAI agents created via project_client)
        if hasattr(self, "project_client") and self.project_client:
            try:
                agent = await self.project_client.agents.get_agent(agent_id)
                if agent and agent.id:
                    self.logger.info(
                        "RAI.AgentReuseSuccess: Resolved agent via Projects SDK (agent_id=%s)",
                        agent.id,
                    )
                    return agent.id
            except Exception as ex:
                self.logger.warning(
                    "RAI.AgentReuseMiss: Projects SDK get_agent failed (agent_id=%s): %s. Reason=ProjectsGetFailed",
                    agent_id,
                    ex,
                )

        # Fallback to AgentsClient (endpoint-based)
        if self.client:
            try:
                agent = await self.client.get_agent(agent_id=agent_id)
                if agent and agent.id:
                    self.logger.info(
                        "RAI.AgentReuseSuccess: Resolved agent via AgentsClient (agent_id=%s)",
                        agent.id,
                    )
                    return agent.id
            except Exception as ex:
                self.logger.warning(
                    "RAI.AgentReuseMiss: AgentsClient get_agent failed (agent_id=%s): %s. Reason=EndpointGetFailed",
                    agent_id,
                    ex,
                )

        self.logger.error(
            "RAI.AgentReuseMiss: Could not resolve agent_id=%s via any client. Reason=ClientMismatch",
            agent_id,
        )
        return None

    def get_agent_id(self, chat_client) -> str:
        """Return the underlying agent ID."""
        if chat_client and chat_client.agent_id is not None:
            return chat_client.agent_id
        if (
            self._agent
            and self._agent.chat_client
            and self._agent.chat_client.agent_id is not None
        ):
            return self._agent.chat_client.agent_id  # type: ignore

        # This should not happen if server-side agent creation is working properly
        if self.agent_name and "RAI" in self.agent_name.upper():
            self.logger.error(
                "RAI.AgentReuseMiss: No valid agent_id found for RAI agent. Reason=NoValidChatClient (This indicates server-side agent creation failed)"
            )
            raise RuntimeError(
                f"RAI agent '{self.agent_name}' has no valid agent_id. Server-side agent creation may have failed."
            )

        # For non-RAI agents, continue normal flow
        id = generate_assistant_id()
        self.logger.info("Generated new agent ID: %s", id)
        return id

    async def get_database_team_agent(self) -> Optional[AzureAIAgentClient]:
        """Retrieve existing team agent from database, if any."""
        chat_client = None
        try:
            agent_id = await get_database_team_agent_id(
                self.memory_store, self.team_config, self.agent_name
            )

            if not agent_id:
                self.logger.info(
                    "RAI.AgentReuseMiss: No stored agent_id found in database. Reason=NoStoredId (agent_name=%s)",
                    self.agent_name,
                )
                return None

            # Use resolve_agent_id for dual-client fallback (Projects SDK → AgentsClient)
            resolved_id = await self.resolve_agent_id(agent_id)
            if not resolved_id:
                self.logger.error(
                    "RAI.AgentReuseMiss: Stored agent_id=%s could not be resolved via any client. Clearing stale DB entry.",
                    agent_id,
                )
                # Clear the stale agent ID from database so we can create a fresh one
                try:
                    await self._clear_stale_agent_from_db(agent_id)
                except Exception as clear_ex:
                    self.logger.warning("Failed to clear stale agent from DB: %s", clear_ex)
                return None

            # Create AzureAIAgentClient with resolved agent ID
            # For RAI agents created via Projects SDK, use project_client if available
            if hasattr(self, "project_client") and self.project_client:
                chat_client = AzureAIAgentClient(
                    project_client=self.project_client,
                    agent_id=resolved_id,
                    async_credential=self.creds,
                )
                self.logger.info(
                    "RAI.AgentReuseSuccess: Created AzureAIAgentClient with Projects SDK (agent_id=%s)",
                    resolved_id,
                )
            else:
                # Fallback to endpoint-based client
                chat_client = AzureAIAgentClient(
                    project_endpoint=self.project_endpoint,
                    agent_id=resolved_id,
                    model_deployment_name=self.model_deployment_name,
                    async_credential=self.creds,
                )
                self.logger.info(
                    "RAI.AgentReuseSuccess: Created AzureAIAgentClient with endpoint (agent_id=%s)",
                    resolved_id,
                )

        except Exception as ex:
            self.logger.error(
                "RAI.AgentReuseMiss: Failed to retrieve database team agent: %s. Reason=Exception",
                ex,
            )
        return chat_client

    async def _clear_stale_agent_from_db(self, stale_agent_id: str) -> None:
        """Clear a stale agent ID from the database."""
        try:
            # Note: This is a placeholder - the actual implementation depends on your DB API
            # You may need to call a delete method on memory_store
            self.logger.info(
                "RAI: Clearing stale agent_id=%s from database for agent_name=%s",
                stale_agent_id,
                self.agent_name,
            )
            # If your DatabaseBase has a delete method, call it here
            # await self.memory_store.delete_team_agent(self.team_config.team_id, self.agent_name)
        except Exception as ex:
            self.logger.error("Failed to clear stale agent from database: %s", ex)

    async def save_database_team_agent(self) -> None:
        """Save current team agent to database."""
        try:
            if self._agent.id is None:
                self.logger.error("Cannot save database team agent: agent_id is None")
                return

            # Check if agent already exists in DB to prevent overwriting during reuse
            stored_id = await get_database_team_agent_id(
                self.memory_store, self.team_config, self.agent_name
            )

            if stored_id == self._agent.id:
                self.logger.info(
                    "RAI.AgentReuseSuccess: Agent ID unchanged (agent_id=%s); skipping save to prevent overwrite.",
                    self._agent.id,
                )
                return

            if stored_id and stored_id != self._agent.id:
                self.logger.warning(
                    "RAI: Overwriting existing agent_id=%s with new agent_id=%s (This may indicate reuse failure)",
                    stored_id,
                    self._agent.id,
                )

            currentAgent = CurrentTeamAgent(
                team_id=self.team_config.team_id,
                team_name=self.team_config.name,
                agent_name=self.agent_name,
                agent_foundry_id=self._agent.id,
                agent_description=self.agent_description,
                agent_instructions=self.agent_instructions,
            )
            await self.memory_store.add_team_agent(currentAgent)
            self.logger.info(
                "RAI: Saved agent to database (agent_id=%s, agent_name=%s)",
                self._agent.id,
                self.agent_name,
            )

        except Exception as ex:
            self.logger.error("Failed to save save database: %s", ex)

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
    Extends MCPEnabledBase with Azure credential + AzureAIAgentClient contexts.
    Subclasses:
      - create or attach an Azure AI Agent definition
      - instantiate an AzureAIAgentClient and assign to self._agent
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
                except Exception:
                    pass

            # Unregister from registry
            try:
                agent_registry.unregister_agent(self)
            except Exception:
                pass

            # Close credential and project client
            if self.client:
                try:
                    await self.client.close()
                except Exception:
                    pass
            if self.creds:
                try:
                    await self.creds.close()
                except Exception:
                    pass

        finally:
            await super().close()
            self.client = None
            self.creds = None
            self.project_endpoint = None

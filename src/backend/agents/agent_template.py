"""AgentTemplate: GA agent_framework 1.2.2 implementation using FoundryChatClient + Agent.

Replaces v4/magentic_agents/foundry_agent.py which used the deprecated
AzureAIAgentClient + ChatAgent pattern from agent_framework_azure_ai.

Tool configuration:
  - MCP path     : MCPStreamableHTTPTool (local tool, connects to external MCP HTTP server)
  - Azure Search : configured server-side in Foundry portal; use FoundryAgent(agent_name=...)
  - Code Interp  : configured server-side in Foundry portal; use FoundryAgent(agent_name=...)
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import AsyncGenerator, Optional

from agent_framework import (Agent, AgentResponseUpdate, Content,
                             MCPStreamableHTTPTool, Message)
from agent_framework_foundry import FoundryAgent, FoundryChatClient
from azure.identity.aio import DefaultAzureCredential
from common.database.database_base import DatabaseBase
from common.models.messages import CurrentTeamAgent, TeamConfiguration
from common.utils.agent_utils import get_database_team_agent_id
from config.agent_registry import agent_registry
from config.mcp_config import MCPConfig, SearchConfig


class AgentTemplate:
    """Foundry agent using agent_framework GA (1.2.2) FoundryChatClient + Agent.

    Two runtime paths:

    1. Azure Search path (use_rag=True + search_config.index_name is set):
       Uses ``FoundryAgent(agent_name=...)`` — the agent must be pre-configured in
       the Foundry portal with the Azure AI Search tool attached to the correct index.
       Instruction overrides are passed at construction time.

    2. MCP / no-tool path:
       Uses ``FoundryChatClient`` + ``Agent(tools=[MCPStreamableHTTPTool(...)])``
       so that no portal setup is required for the MCP HTTP server connection.
    """

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        use_reasoning: bool,
        model_deployment_name: str,
        project_endpoint: str,
        enable_code_interpreter: bool = False,
        mcp_config: MCPConfig | None = None,
        search_config: SearchConfig | None = None,
        team_config: TeamConfiguration | None = None,
        memory_store: DatabaseBase | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.use_reasoning = use_reasoning
        self.model_deployment_name = model_deployment_name
        self.project_endpoint = project_endpoint
        self.enable_code_interpreter = enable_code_interpreter
        self.mcp_cfg = mcp_config
        self.search_config = search_config
        self.team_config = team_config
        self.memory_store = memory_store

        self.logger = logging.getLogger(__name__)

        self._credential: Optional[DefaultAzureCredential] = None
        self._stack: Optional[AsyncExitStack] = None
        # Either an Agent (MCP path) or a FoundryAgent (Azure Search path)
        self._agent: Optional[Agent | FoundryAgent] = None
        self._use_azure_search: bool = self._is_azure_search_requested()

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------

    def _is_azure_search_requested(self) -> bool:
        """Return True when the Azure AI Search path should be used."""
        if not self.search_config:
            return False
        has_index = bool(getattr(self.search_config, "index_name", None))
        if has_index:
            self.logger.info(
                "Azure AI Search requested (index=%s).",
                self.search_config.index_name,
            )
        return has_index

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def open(self) -> "AgentTemplate":
        """Initialize the agent and register it in the global registry."""
        if self._stack is not None:
            return self

        self._stack = AsyncExitStack()
        self._credential = DefaultAzureCredential()
        await self._stack.enter_async_context(self._credential)

        try:
            if self._use_azure_search:
                await self._open_azure_search_path()
            else:
                await self._open_mcp_path()
        except Exception as exc:
            self.logger.error(
                "Failed to initialize agent '%s': %s", self.agent_name, exc
            )
            await self._stack.aclose()
            self._stack = None
            raise

        # Register (best-effort)
        try:
            agent_registry.register_agent(self)
        except Exception as exc:
            self.logger.warning(
                "Failed to register agent '%s': %s", self.agent_name, exc
            )

        # Persist to Cosmos DB (best-effort)
        await self._save_team_agent()

        return self

    async def _open_azure_search_path(self) -> None:
        """Azure Search path: FoundryAgent reads tool config from the Foundry portal.

        The agent must be pre-configured in the Foundry portal with:
          - Model deployment matching ``self.model_deployment_name``
          - Azure AI Search tool attached to ``self.search_config.index_name``
        """
        self.logger.info(
            "Opening agent '%s' via FoundryAgent (Azure Search path).",
            self.agent_name,
        )
        foundry_agent = FoundryAgent(
            project_endpoint=self.project_endpoint,
            agent_name=self.agent_name,
            credential=self._credential,
            # Pass instruction override so portal-configured instructions can be
            # extended at runtime without re-deploying the portal agent definition.
            instructions=self.agent_instructions if self.agent_instructions else None,
        )
        # FoundryAgent supports async context manager; entering it resolves the
        # agent definition lazily on the first run() call.
        self._agent = await self._stack.enter_async_context(foundry_agent)

    async def _open_mcp_path(self) -> None:
        """MCP / no-tool path: Agent + FoundryChatClient (programmatic)."""
        self.logger.info(
            "Opening agent '%s' via FoundryChatClient + Agent (MCP path).",
            self.agent_name,
        )
        tools = []

        if self.mcp_cfg:
            mcp_tool = MCPStreamableHTTPTool(
                name=self.mcp_cfg.name,
                description=self.mcp_cfg.description,
                url=self.mcp_cfg.url,
            )
            # MCPStreamableHTTPTool manages an HTTP connection; enter its context.
            await self._stack.enter_async_context(mcp_tool)
            tools.append(mcp_tool)
            self.logger.info("Attached MCPStreamableHTTPTool '%s'.", self.mcp_cfg.name)

        chat_client = FoundryChatClient(
            project_endpoint=self.project_endpoint,
            model=self.model_deployment_name,
            credential=self._credential,
        )

        agent = Agent(
            client=chat_client,
            instructions=self.agent_instructions,
            name=self.agent_name,
            description=self.agent_description,
            tools=tools if tools else None,
        )
        self._agent = await self._stack.enter_async_context(agent)

    async def close(self) -> None:
        """Unregister the agent and release all resources."""
        if self._stack is None:
            return

        try:
            agent_registry.unregister_agent(self)
        except Exception as exc:
            self.logger.warning(
                "Failed to unregister agent '%s': %s", self.agent_name, exc
            )

        try:
            await self._stack.aclose()
        finally:
            self._stack = None
            self._agent = None
            self._credential = None

    # Context manager support
    async def __aenter__(self) -> "AgentTemplate":
        return await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Invocation (streaming)
    # ------------------------------------------------------------------

    async def invoke(self, prompt: str) -> AsyncGenerator[AgentResponseUpdate, None]:
        """Stream model output for a user prompt.

        Yields ``AgentResponseUpdate`` objects from the underlying agent run.
        """
        if not self._agent:
            raise RuntimeError(
                f"Agent '{self.agent_name}' not initialized; call open() first."
            )

        message = Message(role="user", contents=[Content.from_text(prompt)])
        async for update in self._agent.run(message, stream=True):
            yield update

    # ------------------------------------------------------------------
    # Cosmos DB persistence
    # ------------------------------------------------------------------

    async def _save_team_agent(self) -> None:
        """Persist agent metadata to Cosmos DB (best-effort)."""
        if not self.memory_store or not self.team_config:
            return
        try:
            # In the new pattern, agent_foundry_id stores the agent name (no runtime ID).
            stored_name = await get_database_team_agent_id(
                self.memory_store, self.team_config, self.agent_name
            )
            if stored_name == self.agent_name:
                self.logger.debug(
                    "Agent '%s' already in Cosmos DB; skip save.", self.agent_name
                )
                return

            record = CurrentTeamAgent(
                team_id=self.team_config.team_id,
                team_name=self.team_config.name,
                agent_name=self.agent_name,
                agent_foundry_id=self.agent_name,  # name-based identity in GA pattern
                agent_description=self.agent_description,
                agent_instructions=self.agent_instructions,
            )
            await self.memory_store.add_team_agent(record)
            self.logger.info(
                "Saved team agent to Cosmos DB (agent_name=%s).", self.agent_name
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to save team agent to Cosmos DB (agent_name=%s): %s",
                self.agent_name,
                exc,
            )

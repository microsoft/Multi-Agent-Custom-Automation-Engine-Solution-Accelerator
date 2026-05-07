"""AgentTemplate: MAF 1.0 section 6 pattern — get-or-create portal agent + per-agent Toolbox.

Single code path:
  1. Get-or-create Foundry portal agent (bootstrap from team JSON on first run;
     portal edits to instructions/model take effect on container restart).
  2. Build per-agent Toolbox (``macae-{agent_name}-tools``) with whichever of
     MCP, Azure AI Search, and Code Interpreter are enabled for this agent.
  3. ``Agent(client=FoundryChatClient(...), instructions=portal_agent.instructions,
             tools=[toolbox])`` — FoundryAgent is never used so Magentic / Handoff
     always works.

Replaces the two-path design that used FoundryAgent for Azure Search (which blocked
Magentic) and FoundryChatClient + Agent with MCPStreamableHTTPTool for MCP.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import AsyncGenerator, Optional

from agent_framework import Agent, AgentResponseUpdate, Content, Message
from agent_framework_foundry import FoundryChatClient
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (AISearchIndexResource,
                                      AzureAISearchTool,
                                      AzureAISearchToolResource,
                                      CodeInterpreterTool, MCPTool,
                                      PromptAgentDefinition)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from common.database.database_base import DatabaseBase
from common.models.messages import CurrentTeamAgent, TeamConfiguration
from common.utils.agent_utils import get_database_team_agent_id
from config.agent_registry import agent_registry
from config.mcp_config import MCPConfig, SearchConfig


class AgentTemplate:
    """MAF 1.0 agent using get-or-create Foundry portal agent + per-agent Toolbox.

    All tool types (MCP, Azure AI Search, Code Interpreter) go through a Toolbox so
    that they appear in the Foundry portal alongside the agent definition.  Context
    stays client-side (``FoundryChatClient``) so that Magentic and Handoff work.
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
        self._agent: Optional[Agent] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def open(self) -> "AgentTemplate":
        """Get-or-create portal agent, build Toolbox, wire FoundryChatClient + Agent."""
        if self._stack is not None:
            return self

        self._stack = AsyncExitStack()
        self._credential = DefaultAzureCredential()
        await self._stack.enter_async_context(self._credential)

        try:
            # Step 1 — Get-or-create the Foundry Prompt Agent.
            #
            # SDK 2.1.0 API:
            #   agents.get(agent_name)            -> AgentDetails
            #   agents.create_version(agent_name,
            #       definition=PromptAgentDefinition(model=..., instructions=...))
            #                                     -> AgentVersionDetails
            #
            # AgentDetails.versions.latest.definition holds the
            # PromptAgentDefinition (with .model and .instructions).
            project_client = AIProjectClient(
                endpoint=self.project_endpoint,
                credential=self._credential,
            )
            await self._stack.enter_async_context(project_client)

            try:
                agent_details = await project_client.agents.get(self.agent_name)
                definition = agent_details.versions.latest.definition
                self.logger.info(
                    "Found existing agent '%s' — using portal definition.",
                    self.agent_name,
                )
            except ResourceNotFoundError:
                # First run: bootstrap a Prompt Agent from the team JSON config.
                definition = PromptAgentDefinition(
                    model=self.model_deployment_name,
                    instructions=self.agent_instructions,
                )
                try:
                    await project_client.agents.create_version(
                        agent_name=self.agent_name,
                        definition=definition,
                        description=self.agent_description,
                    )
                    self.logger.info("Created agent '%s'.", self.agent_name)
                except HttpResponseError as exc:
                    if exc.status_code == 409:
                        # Agent was created between the get and create calls.
                        self.logger.info(
                            "Agent '%s' already exists — reusing.",
                            self.agent_name,
                        )
                        agent_details = await project_client.agents.get(
                            self.agent_name
                        )
                        definition = agent_details.versions.latest.definition
                    else:
                        raise

            # Step 2 — Create per-agent Toolbox (only when the agent has tools).
            toolbox_name = f"macae-{self.agent_name}-tools"
            tools = self._build_tools()

            if tools:
                try:
                    await project_client.beta.toolboxes.create_version(
                        name=toolbox_name,
                        description=f"Tools for {self.agent_name}",
                        tools=tools,
                    )
                    self.logger.info(
                        "Created toolbox '%s' with %d tool(s).",
                        toolbox_name,
                        len(tools),
                    )
                except HttpResponseError as exc:
                    if exc.status_code == 409:
                        self.logger.info(
                            "Toolbox '%s' already exists \u2014 reusing.",
                            toolbox_name,
                        )
                    else:
                        raise

            # Step 3 — FoundryChatClient + Agent (single path, FoundryAgent never used).
            # definition.model and definition.instructions come from the portal
            # agent (if it already existed) or from the bootstrap we just created.
            chat_client = FoundryChatClient(
                project_endpoint=self.project_endpoint,
                model=definition.model,
                credential=self._credential,
            )

            maf_tools = None
            if tools:
                toolbox = await chat_client.get_toolbox(toolbox_name)
                # Workaround: ToolboxVersionObject.tools contains azure-ai-projects
                # SDK model objects that are MutableMapping but NOT JSON-serializable
                # when shallow-copied via dict(). Deep-convert each tool to a plain
                # dict so the OpenAI Responses API can serialize them.
                # See bugs/toolbox-search-tool-serialization.md
                maf_tools = [
                    t.as_dict() if hasattr(t, "as_dict") else t
                    for t in toolbox.tools
                ]

            agent = Agent(
                client=chat_client,
                name=self.agent_name,
                instructions=definition.instructions or self.agent_instructions,
                description=self.agent_description,
                tools=maf_tools,
            )
            self._agent = await self._stack.enter_async_context(agent)

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

    def _build_tools(self) -> list:
        """Return Toolbox tool instances based on this agent's config flags."""
        tools = []

        if self.mcp_cfg:
            mcp_kwargs: dict = {
                "server_label": self.mcp_cfg.name,
                "server_url": self.mcp_cfg.url,
                "require_approval": "never",
            }
            if self.mcp_cfg.connection_id:
                mcp_kwargs["project_connection_id"] = self.mcp_cfg.connection_id
            tools.append(MCPTool(**mcp_kwargs))
            self.logger.debug("Added MCPTool '%s'.", self.mcp_cfg.name)

        if self.search_config and self.search_config.index_name:
            # Workaround: convert to plain dict via as_dict() because
            # agent_framework_foundry shallow-copies Mapping tools with dict(),
            # leaving nested SDK models (AzureAISearchToolResource) that are
            # not JSON-serializable for the Responses API.
            # See bugs/toolbox-search-tool-serialization.md
            tools.append(
                AzureAISearchTool(
                    azure_ai_search=AzureAISearchToolResource(
                        indexes=[
                            AISearchIndexResource(
                                project_connection_id=self.search_config.connection_name,
                                index_name=self.search_config.index_name,
                                query_type=self.search_config.search_query_type,
                            )
                        ]
                    )
                ).as_dict()
            )
            self.logger.debug(
                "Added AzureAISearchTool (index=%s).", self.search_config.index_name
            )

        if self.enable_code_interpreter:
            tools.append(CodeInterpreterTool())
            self.logger.debug("Added CodeInterpreterTool.")

        return tools

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

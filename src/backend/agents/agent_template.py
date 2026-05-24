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

from agent_framework import (Agent, AgentResponseUpdate, ChatOptions, Content,
                             MCPStreamableHTTPTool, Message)
from agent_framework_azure_ai_search import AzureAISearchContextProvider
from agent_framework_foundry import FoundryChatClient
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (AISearchIndexResource, AzureAISearchTool,
                                      AzureAISearchToolResource,
                                      CodeInterpreterTool, FileSearchTool,
                                      MCPTool, PromptAgentDefinition)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from common.database.database_base import DatabaseBase
from common.models.messages import CurrentTeamAgent, TeamConfiguration
from common.utils.agent_utils import get_database_team_agent_id
from config.agent_registry import agent_registry
from config.mcp_config import (KnowledgeBaseConfig, MCPConfig, SearchConfig,
                               VectorStoreConfig)


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
        vector_store_config: VectorStoreConfig | None = None,
        kb_config: KnowledgeBaseConfig | None = None,
        temperature: float | None = None,
        team_config: TeamConfiguration | None = None,
        memory_store: DatabaseBase | None = None,
        extra_tools: list | None = None,
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
        self.vector_store_config = vector_store_config
        self.kb_config = kb_config
        self.temperature = temperature
        self.team_config = team_config
        self.memory_store = memory_store
        self.extra_tools = extra_tools or []

        self.logger = logging.getLogger(__name__)

        self._credential: Optional[DefaultAzureCredential] = None
        self._stack: Optional[AsyncExitStack] = None
        self._agent: Optional[Agent] = None
        self._resolved_vector_store_id: str | None = None
        self._kb_provider: AzureAISearchContextProvider | None = None

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
                # Include MCPTool for KB so it shows in the portal.
                bootstrap_tools = None
                if self.kb_config:
                    kb_mcp_url = (
                        f"{self.kb_config.search_endpoint}/knowledgebases/"
                        f"{self.kb_config.knowledge_base_name}/mcp"
                        f"?api-version=2025-11-01-preview"
                    )
                    bootstrap_tools = [
                        MCPTool(
                            server_label=self.kb_config.knowledge_base_name,
                            server_url=kb_mcp_url,
                            project_connection_id=self.kb_config.search_connection_name,
                        )
                    ]

                definition = PromptAgentDefinition(
                    model=self.model_deployment_name,
                    instructions=self.agent_instructions,
                    tools=bootstrap_tools,
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

            # Step 1b — Resolve vector store name → ID (for FileSearchTool).
            self._resolved_vector_store_id: str | None = None
            if self.vector_store_config and self.vector_store_config.vector_store_name:
                oai = project_client.get_openai_client()
                vs_name = self.vector_store_config.vector_store_name
                page = await oai.vector_stores.list()
                for vs in page.data:
                    if vs.name == vs_name:
                        self._resolved_vector_store_id = vs.id
                        self.logger.info(
                            "Resolved vector store '%s' → %s.",
                            vs_name,
                            vs.id,
                        )
                        break
                if not self._resolved_vector_store_id:
                    raise ValueError(
                        f"Vector store '{vs_name}' not found. "
                        f"Run scripts/seed_vector_stores.py to create it."
                    )

            # Step 1c — Create AzureAISearchContextProvider for Foundry IQ KB.
            # Team JSON kb_config is authoritative for KB assignment.
            # If the portal definition has a stale MCPTool (different KB name),
            # update the portal to match.
            self._kb_provider = None
            kb_endpoint: str | None = None
            kb_name: str | None = None

            # Determine desired KB from team JSON config.
            if self.kb_config:
                kb_endpoint = self.kb_config.search_endpoint
                kb_name = self.kb_config.knowledge_base_name

            # Check if portal MCPTool matches; update if stale.
            if kb_name and definition.tools:
                portal_kb_name: str | None = None
                for tool_def in definition.tools:
                    if isinstance(tool_def, MCPTool) and tool_def.server_url:
                        url = tool_def.server_url
                        if "/knowledgebases/" in url:
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            parts = parsed.path.split("/knowledgebases/")
                            if len(parts) == 2:
                                portal_kb_name = parts[1].split("/")[0]
                            break

                if portal_kb_name and portal_kb_name != kb_name:
                    self.logger.warning(
                        "Portal agent '%s' has stale KB '%s' — updating to '%s'.",
                        self.agent_name, portal_kb_name, kb_name,
                    )
                    # Rebuild tools list with corrected MCPTool.
                    kb_mcp_url = (
                        f"{self.kb_config.search_endpoint}/knowledgebases/"
                        f"{kb_name}/mcp?api-version=2025-11-01-preview"
                    )
                    new_tools = [
                        t for t in definition.tools
                        if not (isinstance(t, MCPTool) and t.server_url
                                and "/knowledgebases/" in t.server_url)
                    ]
                    new_tools.append(MCPTool(
                        server_label=kb_name,
                        server_url=kb_mcp_url,
                        project_connection_id=self.kb_config.search_connection_name,
                    ))
                    definition = PromptAgentDefinition(
                        model=definition.model,
                        instructions=definition.instructions,
                        tools=new_tools,
                    )
                    await project_client.agents.create_version(
                        agent_name=self.agent_name,
                        definition=definition,
                        description=self.agent_description,
                    )
                    self.logger.info(
                        "Updated agent '%s' portal definition with KB '%s'.",
                        self.agent_name, kb_name,
                    )
            elif kb_name and not definition.tools:
                # Agent exists but has no tools — add the MCPTool.
                kb_mcp_url = (
                    f"{self.kb_config.search_endpoint}/knowledgebases/"
                    f"{kb_name}/mcp?api-version=2025-11-01-preview"
                )
                definition = PromptAgentDefinition(
                    model=definition.model,
                    instructions=definition.instructions,
                    tools=[MCPTool(
                        server_label=kb_name,
                        server_url=kb_mcp_url,
                        project_connection_id=self.kb_config.search_connection_name,
                    )],
                )
                await project_client.agents.create_version(
                    agent_name=self.agent_name,
                    definition=definition,
                    description=self.agent_description,
                )
                self.logger.info(
                    "Added KB MCPTool '%s' to existing agent '%s'.",
                    kb_name, self.agent_name,
                )

            if kb_endpoint and kb_name:
                self._kb_provider = AzureAISearchContextProvider(
                    endpoint=kb_endpoint,
                    knowledge_base_name=kb_name,
                    credential=self._credential,
                    mode="agentic",
                )
                await self._stack.enter_async_context(self._kb_provider)
                self.logger.info(
                    "Created AzureAISearchContextProvider (kb=%s, endpoint=%s).",
                    kb_name,
                    kb_endpoint,
                )

            # Step 2 — Create per-agent Toolbox (only when the agent has tools).
            toolbox_name = f"macae-{self.agent_name}-tools"
            tools = self._build_tools()

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
                # Filter out domain MCP tools — those are handled client-side
                # via MCPStreamableHTTPTool.  KEEP KB MCP tools (server-side,
                # executed by the Responses API).
                def _is_domain_mcp_tool(t) -> bool:
                    d = t.as_dict() if hasattr(t, "as_dict") else t
                    if not isinstance(d, dict):
                        return False
                    if str(d.get("type", "")).lower() != "mcp":
                        return False
                    url = str(d.get("server_url", "") or "")
                    return "/knowledgebases/" not in url

                # Try reading tools from the Toolbox API so that portal edits
                # (e.g. adding CodeInterpreter) are reflected at runtime.
                # If the toolbox doesn't exist yet, create it.  If it exists
                # but tools haven't propagated (eventual consistency), fall
                # back to locally-built tools immediately — no retries.
                #
                # KB MCP tools use project_connection_id for auth.  The
                # Responses API resolves this server-side when the toolbox
                # stores the tool definition with the connection reference.
                toolbox_tools = None
                toolbox_exists = False
                try:
                    toolbox = await chat_client.get_toolbox(toolbox_name)
                    toolbox_exists = True
                    if toolbox and toolbox.tools:
                        toolbox_tools = toolbox.tools
                except Exception as _tb_exc:
                    self.logger.debug(
                        "get_toolbox('%s') failed: %s", toolbox_name, _tb_exc,
                    )

                if not toolbox_exists:
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
                        if exc.status_code != 409:
                            raise
                        self.logger.debug(
                            "Toolbox '%s' already exists (race).", toolbox_name
                        )

                # Build maf_tools: use toolbox for non-domain-MCP tools
                # (search, code interpreter, KB MCP).  The Toolbox stores
                # project_connection_id and the Responses API resolves auth
                # server-side when the tool is invoked.
                maf_tools = []

                if toolbox_tools:
                    # From toolbox: take everything except domain MCP tools
                    # (those are handled client-side via MCPStreamableHTTPTool)
                    maf_tools = [
                        t.as_dict() if hasattr(t, "as_dict") else t
                        for t in toolbox_tools
                        if not _is_domain_mcp_tool(t)
                    ]
                    self.logger.info(
                        "Agent '%s' tools from toolbox: %d.",
                        self.agent_name,
                        len(maf_tools),
                    )
                else:
                    # Toolbox not ready — use local non-domain-MCP tools
                    maf_tools = [
                        t.as_dict() if hasattr(t, "as_dict") else t
                        for t in tools
                        if not _is_domain_mcp_tool(t)
                    ]
                    self.logger.info(
                        "Agent '%s' toolbox not ready — local tools: %d.",
                        self.agent_name,
                        len(maf_tools),
                    )

            # Step 2b — Client-side MCP tool.  MCPStreamableHTTPTool connects
            # from *this* process so localhost URLs work (unlike the Toolbox
            # MCPTool which is executed server-side by the Responses API).
            mcp_tool = None
            if self.mcp_cfg:
                mcp_tool = MCPStreamableHTTPTool(
                    name=self.mcp_cfg.name,
                    url=self.mcp_cfg.url,
                )
                await self._stack.enter_async_context(mcp_tool)
                self.logger.info(
                    "Connected to MCP server '%s' at %s.",
                    self.mcp_cfg.name,
                    self.mcp_cfg.url,
                )

            # Combine Toolbox tools (Search, CodeInterpreter) + client-side MCP + extra tools.
            all_tools: list = []
            if maf_tools:
                all_tools.extend(maf_tools)
            if mcp_tool:
                all_tools.append(mcp_tool)
            # Extra tools (e.g. approval-gated clarification tool) injected by
            # AgentFactory for agents with user_responses=true.
            if self.extra_tools:
                all_tools.extend(self.extra_tools)

            agent = Agent(
                client=chat_client,
                name=self.agent_name,
                instructions=definition.instructions or self.agent_instructions,
                description=self.agent_description,
                tools=all_tools if all_tools else None,
                context_providers=[self._kb_provider] if self._kb_provider else None,
                default_options=ChatOptions(temperature=self.temperature) if self.temperature is not None else None,
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
        """Return Toolbox tool instances for portal visibility.

        An ``MCPTool`` is always added when ``mcp_cfg`` is present so the
        Foundry portal / Playground displays the MCP server alongside the
        agent.  In deployed environments ``project_connection_id`` allows
        server-side execution via the Responses API; locally it may be None
        but the toolbox entry still provides discoverability.

        Client-side ``MCPStreamableHTTPTool`` is **always** created in
        ``open()`` for Magentic orchestration regardless; Toolbox-originated
        MCP tools are filtered out of ``maf_tools`` to avoid duplicates.
        """
        tools = []

        # MCPTool for portal visibility — always add when mcp_cfg is present.
        # In deployed environments project_connection_id enables server-side
        # execution; locally client-side MCPStreamableHTTPTool handles it.
        if self.mcp_cfg:
            mcp_tool_kwargs = {
                "server_label": self.mcp_cfg.name,
                "server_url": self.mcp_cfg.url,
                "server_description": self.mcp_cfg.description,
            }
            if self.mcp_cfg.connection_id:
                mcp_tool_kwargs["project_connection_id"] = self.mcp_cfg.connection_id
            tools.append(MCPTool(**mcp_tool_kwargs))
            self.logger.debug(
                "Added MCPTool for toolbox (connection_id=%s).",
                self.mcp_cfg.connection_id,
            )

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

        if self._resolved_vector_store_id:
            tools.append(
                FileSearchTool(
                    vector_store_ids=[self._resolved_vector_store_id]
                ).as_dict()
            )
            self.logger.debug(
                "Added FileSearchTool (vector_store=%s).",
                self._resolved_vector_store_id,
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
            # --- DIAGNOSTIC: log each update type ---
            self.logger.warning(
                ">>> [%s] update type=%s data_type=%s",
                self.agent_name,
                type(update).__name__,
                getattr(update, 'data_type', None),
            )
            if hasattr(update, 'content') and update.content:
                self.logger.warning(
                    ">>> [%s] content preview: %s",
                    self.agent_name,
                    str(update.content)[:200],
                )
            # --- END DIAGNOSTIC ---
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

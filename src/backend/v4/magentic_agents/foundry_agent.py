"""Agent template for building Foundry agents with Azure AI Search, optional MCP tool, and Code Interpreter (agent_framework version)."""

import logging
import os

from agent_framework import Agent, Message
from agent_framework_azure_ai import AzureAIClient, AzureAIProjectAgentOptions
from agent_framework_openai import OpenAIChatOptions
from azure.ai.projects.models import (
    AISearchIndexResource,
    AzureAISearchTool,
    AzureAISearchToolResource,
    PromptAgentDefinition,
)

from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages_af import TeamConfiguration
from v4.common.services.team_service import TeamService
from v4.config.agent_registry import agent_registry
from v4.magentic_agents.common.lifecycle import (
    _FOUNDRY_REGISTERED_AGENT_NAMES,
    AzureAgentBase,
)
from v4.magentic_agents.common.self_heal_middleware import SelfHealToolMiddleware
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig

_TOOL_EXCHANGE_TYPES = frozenset({"function_call", "function_result"})


def _without_tool_exchange(update):
    """What leaves the agent for the workflow is the agent's voice, not its
    exchange with the tools.

    The executor merges the yielded updates into messages and the Magentic
    orchestrator appends those messages to the shared history that every
    participant receives as input. A ``function_call`` that reaches that
    history without its ``function_call_output`` makes the Responses API
    reject the next agent's turn: "No tool output found for function call"
    (prod rev 134, 2026-09-22 07:05, CheckpointValidationAgent's first turn
    after RepositoryValidationAgent's five workspace_exec calls; the plan
    failed). The exchange already happened in the agent's own thread; the
    UI does not render tool messages (PlanPage only logs them).
    Returns the update with the exchange removed, or ``None`` if nothing
    else was in it."""
    contents = getattr(update, "contents", None)
    if not isinstance(contents, list) or not contents:
        return update
    kept = [c for c in contents if getattr(c, "type", None) not in _TOOL_EXCHANGE_TYPES]
    if len(kept) == len(contents):
        return update
    if not kept:
        return None
    update.contents = kept
    return update


CHAT_HISTORY_WINDOW: int = 60


class FoundryAgentTemplate(AzureAgentBase):
    """Agent that uses Azure AI Search (raw tool) OR MCP tool + optional Code Interpreter.

    Priority:
      1. Azure AI Search (if search_config contains required Azure Search fields)
      2. MCP tool (legacy path)
    Code Interpreter is only attached on the MCP path (unless you want it also with Azure Search—currently skipped for incompatibility per request).
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
        enable_bing: bool = False,
        enable_file_search: bool = False,
        enable_web_search: bool = False,
        enable_image_generation: bool = False,
        enable_azure_functions: bool = False,
        enable_sharepoint: bool = False,
        enable_browser_automation: bool = False,
        enable_fabric: bool = False,
        enable_bing_custom_search: bool = False,
        mcp_config: MCPConfig | None = None,
        search_config: SearchConfig | None = None,
        team_service: TeamService | None = None,
        team_config: TeamConfiguration | None = None,
        memory_store: DatabaseBase | None = None,
        ephemeral: bool = False,
        user_id: str = "",
        session_id: str = "",
        runtime_tools_enabled: bool = True,
        user_access_token: str | None = None,
    ) -> None:
        # Get project_client before calling super().__init__
        # Pass user_access_token for OBO flow support
        project_client = config.get_ai_project_client(
            user_access_token=user_access_token
        )

        super().__init__(
            mcp=mcp_config,
            model_deployment_name=model_deployment_name,
            project_endpoint=project_endpoint,
            team_service=team_service,
            team_config=team_config,
            memory_store=memory_store,
            agent_name=agent_name,
            agent_description=agent_description,
            agent_instructions=agent_instructions,
            project_client=project_client,
            user_access_token=user_access_token,  # Pass for OBO flow
        )

        self.enable_code_interpreter = enable_code_interpreter
        self.enable_bing = enable_bing
        self.enable_file_search = enable_file_search
        self.enable_web_search = enable_web_search
        self.enable_image_generation = enable_image_generation
        self.enable_azure_functions = enable_azure_functions
        self.enable_sharepoint = enable_sharepoint
        self.enable_browser_automation = enable_browser_automation
        self.enable_fabric = enable_fabric
        self.enable_bing_custom_search = enable_bing_custom_search
        self.search = search_config
        self.logger = logging.getLogger(__name__)

        # Decide early whether Azure Search mode should be activated
        self._use_azure_search = self._is_azure_search_requested()
        self.use_reasoning = use_reasoning

        self._ephemeral = ephemeral
        self._user_id = user_id
        self._session_id = session_id
        self.runtime_tools_enabled = runtime_tools_enabled

        # Placeholder for server-created Azure AI agent id (if Azure Search path)
        self._azure_server_agent_id: str | None = None

    # -------------------------
    # Mode detection
    # -------------------------
    def _is_azure_search_requested(self) -> bool:
        """Determine if Azure AI Search raw tool path should be used."""
        if not self.search:
            return False
        # Minimal heuristic: presence of required attributes
        has_index = hasattr(self.search, "index_name") and bool(self.search.index_name)
        if has_index:
            self.logger.info(
                "Azure AI Search requested (connection_id=%s, index=%s).",
                getattr(self.search, "connection_name", None),
                getattr(self.search, "index_name", None),
            )
            return True
        return False

    async def _collect_tools(self) -> list:
        """Collect tool definitions for Agent (MCP path only)."""
        tools: list = []

        if self.enable_code_interpreter:
            self.logger.info(
                "Code Interpreter requested — handled server-side by AzureAIClient."
            )

        # MCP Tool (from base class)
        if self.mcp_tool:
            tools.append(self.mcp_tool)
            self.logger.info("Added MCP tool: %s", self.mcp_tool.name)

        # NOTE: Foundry IQ Knowledge Base is NOT attached as a runtime tool.
        # It is associated server-side to the published agent in Foundry
        # (Portal → Agent → Knowledge → attach kb-knowledgebase550-lrm9b).
        # When using AzureAIClient with use_latest_version=True, the published
        # agent already has the KB available — no client-side bridge needed.

        self.logger.info("Total tools collected (MCP path): %d", len(tools))
        return tools

    # -------------------------
    # Azure Search helper
    # -------------------------
    async def _create_azure_search_enabled_client(self) -> AzureAIClient | None:
        """
        Create a server-side Azure AI agent with Azure AI Search tool using create_version.

        This uses the AIProjectClient.agents.create_version() approach with:
        - PromptAgentDefinition for agent configuration
        - AzureAISearchTool with AzureAISearchToolResource for search capability
        - AISearchIndexResource for index configuration with project_connection_id

        Requirements:
          - An Azure AI Project Connection for Azure AI Search
          - search_config.index_name must exist in the Search service.
          - search_config.connection_name should match the AI Project connection name

        Returns:
            AzureAIClient | None
        """
        if not self.search:
            self.logger.error("Search configuration missing.")
            return None

        # Get connection name - this is used as project_connection_id in create_version
        connection_name = getattr(self.search, "connection_name", None)
        if not connection_name:
            # Fallback to environment variable
            connection_name = config.AZURE_AI_SEARCH_CONNECTION_NAME
            self.logger.info(
                "Using connection_name from environment: %s", connection_name
            )

        index_name = getattr(self.search, "index_name", "")
        query_type = getattr(self.search, "search_query_type", "semantic")
        top_k = getattr(self.search, "top_k", 5)

        if not index_name:
            self.logger.error(
                "index_name not provided in search_config; aborting Azure Search path."
            )
            return None

        if not connection_name:
            self.logger.error(
                "connection_name not provided; aborting Azure Search path."
            )
            return None

        self.logger.info(
            "Resolving Azure AI Search agent: name=%s, connection_name=%s, index=%s, query_type=%s, top_k=%s",
            self.agent_name,
            connection_name,
            index_name,
            query_type,
            top_k,
        )

        try:
            if not self.model_deployment_name:
                self.logger.error(
                    "model_deployment_name is required for Azure AI Search agent creation."
                )
                raise ValueError(
                    "model_deployment_name must be provided to create Azure AI Search agent."
                )

            if self.project_client is None:
                self.logger.error(
                    "project_client is None; cannot create Azure AI Search agent."
                )
                raise ValueError(
                    "project_client must be initialized to create Azure AI Search agent."
                )

            # ── Reuse-first: same pattern as _register_in_foundry() in lifecycle.py ──
            # If the agent already exists in Foundry by name, attach to it
            # (use_latest_version=True). Only call create_version when the agent
            # doesn't exist OR MACAE_FORCE_AGENT_PUBLISH=1 is set. This prevents
            # version sprawl on every backend restart / new session.
            force_republish = os.getenv("MACAE_FORCE_AGENT_PUBLISH", "").lower() in (
                "1",
                "true",
                "yes",
            )

            # Process-level cache hit → skip the list call entirely
            if (
                self.agent_name in _FOUNDRY_REGISTERED_AGENT_NAMES
                and not force_republish
            ):
                self.logger.info(
                    "✅ Azure-Search agent '%s' already cached for this process. NO creating new version.",
                    self.agent_name,
                )
                return AzureAIClient(
                    project_client=self.project_client,
                    agent_name=self.agent_name,
                    use_latest_version=True,
                    model_deployment_name=self.model_deployment_name,
                )

            existing_agent = None
            if not force_republish:
                self.logger.info(
                    "🔍 Checking if Azure-Search agent '%s' already exists in Foundry to avoid creating new version...",
                    self.agent_name,
                )
                async for agent in self.project_client.agents.list():
                    if getattr(agent, "name", None) == self.agent_name:
                        existing_agent = agent
                        break

            if existing_agent is not None and not force_republish:
                self._azure_server_agent_id = getattr(existing_agent, "id", None)
                if self.agent_name:
                    _FOUNDRY_REGISTERED_AGENT_NAMES.add(self.agent_name)
                self.logger.info(
                    "✅ Azure-Search agent '%s' ALREADY EXISTS in Foundry "
                    "(id=%s, version=%s). REUSING existing agent - NO NEW VERSION CREATED. "
                    "Set MACAE_FORCE_AGENT_PUBLISH=1 only if you need to update definition.",
                    self.agent_name,
                    getattr(existing_agent, "id", "unknown"),
                    getattr(existing_agent, "version", "unknown"),
                )
                return AzureAIClient(
                    project_client=self.project_client,
                    agent_name=self.agent_name,
                    use_latest_version=True,
                    model_deployment_name=self.model_deployment_name,
                )

            if force_republish:
                self.logger.warning(
                    "⚠️ Force-publishing Azure-Search agent '%s' (MACAE_FORCE_AGENT_PUBLISH=1). Creating NEW version...",
                    self.agent_name,
                )
            else:
                self.logger.warning(
                    "⚠️ Azure-Search agent '%s' does NOT exist in Foundry. Creating NEW version...",
                    self.agent_name,
                )

            # ── Only create when missing or forced ────────────────────────────
            enhanced_instructions = (
                f"{self.agent_instructions} "
                "Always use the Azure AI Search tool and configured index for knowledge retrieval."
            )

            azure_agent = await self.project_client.agents.create_version(
                agent_name=self.agent_name,
                definition=PromptAgentDefinition(
                    model=self.model_deployment_name,
                    instructions=enhanced_instructions,
                    tools=[
                        AzureAISearchTool(
                            azure_ai_search=AzureAISearchToolResource(
                                indexes=[
                                    AISearchIndexResource(
                                        project_connection_id=connection_name,
                                        index_name=index_name,
                                        query_type=query_type,
                                        top_k=top_k,
                                    )
                                ]
                            )
                        )
                    ],
                ),
            )

            self._azure_server_agent_id = azure_agent.id
            if self.agent_name:
                _FOUNDRY_REGISTERED_AGENT_NAMES.add(self.agent_name)

            self.logger.info(
                "🆕 CREATED NEW Azure AI Search agent version (name=%s, id=%s, version=%s).",
                azure_agent.name,
                azure_agent.id,
                azure_agent.version,
            )

            chat_client = AzureAIClient(
                project_client=self.project_client,
                agent_name=azure_agent.name,
                agent_version=azure_agent.version,
                model_deployment_name=self.model_deployment_name,
            )
            return chat_client

        except Exception as ex:
            self.logger.error(
                "Failed to resolve Azure Search enabled agent (connection=%s, index=%s): %s",
                connection_name,
                index_name,
                ex,
            )
            return None

    # -------------------------
    # Agent lifecycle
    # -------------------------
    async def _after_open(self) -> None:
        """Initialize ChatAgent after connections are established."""
        if self.use_reasoning:
            self.logger.info("Initializing agent in Reasoning mode.")
            # Modelos de razonamiento: el control que cambia el comportamiento
            # es reasoning.effort (medido: low → 0 tokens de razonamiento,
            # medium → 25); temperature no se envía.
            inference: dict = {"reasoning": {"effort": config.AGENT_REASONING_EFFORT}}
        else:
            self.logger.info("Initializing agent in Foundry mode.")
            inference = {"temperature": config.AGENT_TEMPERATURE}

        try:
            if self._use_azure_search:
                # Azure Search mode (skip MCP + Code Interpreter due to incompatibility)
                self.logger.info(
                    "Initializing agent '%s' in Azure AI Search mode (exclusive) with index=%s.",
                    self.agent_name,
                    getattr(self.search, "index_name", "N/A") if self.search else "N/A",
                )
                chat_client = await self._create_azure_search_enabled_client()
                if not chat_client:
                    raise RuntimeError(
                        "Azure AI Search mode requested but setup failed."
                    )

                self._agent = Agent(
                    id=self.get_agent_id(),
                    client=chat_client,
                    instructions=self.agent_instructions,
                    name=self.agent_name,
                    description=self.agent_description,
                    default_options=AzureAIProjectAgentOptions(
                        store=False,
                        tool_choice="required",
                        **inference,
                    ),
                )
            else:
                self.logger.info("Initializing agent in MCP mode.")

                if self.runtime_tools_enabled:
                    tools = await self._collect_tools()
                else:
                    tools = []

                if self.enable_code_interpreter and not tools:
                    # Code Interpreter is server-side in Foundry portal.
                    # Must use AzureAIClient to access it — ResponsesClient
                    # cannot reach server-side tools configured in the portal.
                    #
                    # Agents from agent_teams/*.json are pre-configured in the
                    # portal manually. Agents composed dynamically by the Router
                    # (coding_tools=True) are new: publish them with
                    # CodeInterpreterTool NOW so AzureAIClient finds the tool
                    # server-side. _register_in_foundry reuse-first: if the
                    # agent already exists in Foundry the publish is skipped.
                    if not self._ephemeral:
                        await self._register_in_foundry()
                    self.logger.info(
                        "Using AzureAIClient for '%s' (server-side Code Interpreter).",
                        self.agent_name,
                    )
                    self._agent = Agent(
                        id=self.get_agent_id(),
                        client=self.get_chat_client(),
                        instructions=self.agent_instructions,
                        name=self.agent_name,
                        description=self.agent_description,
                        default_options=AzureAIProjectAgentOptions(
                            store=True,
                            tool_choice="auto",
                            **inference,
                        ),
                    )
                elif tools:
                    # Runtime MCP tools present → AzureOpenAIResponsesClient
                    # supports dynamic MCP tools passed at runtime.
                    responses_client = self.get_responses_client()
                    if self.enable_code_interpreter:
                        # Runtime MCP (the mounted workspace) and Code
                        # Interpreter must coexist: neither is sacrificed for
                        # the other. AzureAIClient cannot carry runtime tools,
                        # so the interpreter rides here as the Responses
                        # API's hosted tool, next to MCP.
                        tools = [
                            *tools,
                            responses_client.get_code_interpreter_tool(),
                        ]
                    if self.enable_web_search:
                        # Web search is server-side on AzureAIClient's published
                        # definition, which this path does NOT use. Attach it as
                        # the Responses API's hosted web search tool so a
                        # workspace/MCP specialist that also asked for live web
                        # keeps both, next to MCP.
                        tools = [
                            *tools,
                            responses_client.get_web_search_tool(),
                        ]
                    self.logger.info(
                        "Using AzureOpenAIResponsesClient for '%s' (runtime tools%s%s).",
                        self.agent_name,
                        " + hosted Code Interpreter"
                        if self.enable_code_interpreter
                        else "",
                        " + hosted Web Search" if self.enable_web_search else "",
                    )
                    self._agent = Agent(
                        id=self.get_agent_id(),
                        client=responses_client,
                        instructions=self.agent_instructions,
                        name=self.agent_name,
                        description=self.agent_description,
                        tools=tools,
                        # Runtime tools (MCPStreamableHTTPTool) execute in-process
                        # inside the function-invocation loop, so a recoverable
                        # tool failure can be returned to the model for in-turn
                        # retry instead of crashing the request.
                        middleware=[SelfHealToolMiddleware()],
                        # The Responses client's options type is OpenAIChatOptions —
                        # generic ChatOptions is not assignable to it (Pylance).
                        default_options=OpenAIChatOptions(
                            store=True,
                            tool_choice="auto",
                            **inference,
                        ),
                    )
                else:
                    # No runtime tools → AzureAIClient with published
                    # Foundry agent (server-side KB + tools).
                    #
                    # Web search is a server-side tool: AzureAIClient reaches it
                    # only through the published definition (use_latest_version).
                    # A Router-composed web-only specialist is new, so publish
                    # NOW with WebSearchTool or the request runs blind to live
                    # web. _register_in_foundry is reuse-first: an identical
                    # existing definition is left untouched.
                    if self.enable_web_search and not self._ephemeral:
                        await self._register_in_foundry()
                    self.logger.info(
                        "Using AzureAIClient for '%s' (published agent, server-side tools).",
                        self.agent_name,
                    )
                    self._agent = Agent(
                        id=self.get_agent_id(),
                        client=self.get_chat_client(),
                        instructions=self.agent_instructions,
                        name=self.agent_name,
                        description=self.agent_description,
                        default_options=AzureAIProjectAgentOptions(
                            store=True,
                            tool_choice="auto",
                            **inference,
                        ),
                    )

                if tools and not self._ephemeral:
                    await self._register_in_foundry()

            self.logger.info("Initialized Agent '%s'", self.agent_name)

        except Exception as ex:
            self.logger.error("Failed to initialize Agent: %s", ex)
            raise

        # Register agent globally
        try:
            agent_registry.register_agent(self)
            self.logger.info(
                "Registered agent '%s' in global registry.", self.agent_name
            )
        except Exception as reg_ex:
            self.logger.warning(
                "Could not register agent '%s': %s", self.agent_name, reg_ex
            )

    # -------------------------
    # Invocation (streaming)
    # -------------------------
    async def invoke(
        self,
        prompt: str,
        session_id: str = "",
        user_id: str = "",
        file_ids: list[str] | None = None,
    ):
        """Stream model output for a prompt, with session context.

        Args:
            prompt: The user message.
            session_id: Optional session ID for history loading.
            user_id: Optional user ID for history loading.
            file_ids: Optional list of Foundry file IDs (uploaded via /chat/upload-file).
                      Files are attached to the thread message with code_interpreter access.
        """
        if not self._agent:
            raise RuntimeError("Agent not initialized; call open() first.")

        messages: list[Message] = []

        # Load recent session messages from Cosmos for conversational continuity
        sid = session_id or self._session_id
        uid = user_id or self._user_id
        if sid and uid:
            try:
                from common.services.chat_cosmos_service import get_chat_cosmos_service

                chat_svc = await get_chat_cosmos_service()
                session = await chat_svc.get_session(sid, uid)
                if session and session.get("messages"):
                    for m in session["messages"][-CHAT_HISTORY_WINDOW:]:
                        role = "user" if m.get("role") == "user" else "assistant"
                        content = m.get("content", "")
                        if content:
                            messages.append(Message(role=role, text=content))
            except Exception:
                pass  # No history available, proceed with just the prompt

        if file_ids:
            from agent_framework import Content

            user_contents: list = [Content.from_text(prompt)]
            for fid in file_ids:
                user_contents.append(Content.from_hosted_file(file_id=fid))
            messages.append(Message(role="user", contents=user_contents))

            self.logger.info(
                "Invoking agent with %d hosted file(s): %s",
                len(file_ids),
                file_ids,
            )
            async for update in self._agent.run(messages, stream=True):
                voice = _without_tool_exchange(update)
                if voice is not None:
                    yield voice
        else:
            messages.append(Message(role="user", text=prompt))
            async for update in self._agent.run(messages, stream=True):
                voice = _without_tool_exchange(update)
                if voice is not None:
                    yield voice

    # -------------------------
    # Cleanup (optional override if you want to delete server-side agent)
    # -------------------------


# -------------------------
# Factory
# -------------------------
# async def create_foundry_agent(
#     agent_name: str,
#     agent_description: str,
#     agent_instructions: str,
#     model_deployment_name: str,
#     mcp_config: MCPConfig | None,
#     search_config: SearchConfig | None,
# ) -> FoundryAgentTemplate:
#     """Factory to create and open a FoundryAgentTemplate."""
#     agent = FoundryAgentTemplate(
#         agent_name=agent_name,
#         agent_description=agent_description,
#         agent_instructions=agent_instructions,
#         model_deployment_name=model_deployment_name,
#         enable_code_interpreter=True,
#         mcp_config=mcp_config,
#         search_config=search_config,

#     )
#     await agent.open()
#     return agent

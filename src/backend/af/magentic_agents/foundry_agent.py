"""Agent template for building Foundry agents with Azure AI Search, optional MCP tool, and Code Interpreter (agent_framework version)."""

import logging
from typing import List, Optional

from azure.ai.agents.models import (
    Agent,
    AzureAISearchTool,
    CodeInterpreterToolDefinition,
)

from agent_framework import (
    ChatMessage,
    Role,
    ChatOptions,
    HostedMCPTool,
    AggregateContextProvider,
    ChatAgent,
    ChatClientProtocol,
    ChatMessageStoreProtocol,
    ContextProvider,
    Middleware,
    ToolMode,
    ToolProtocol,
)
from af.magentic_agents.common.lifecycle import AzureAgentBase
from af.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from af.config.agent_registry import agent_registry

# Broad exception flag
# pylint: disable=w0718


class FoundryAgentTemplate(AzureAgentBase):
    """Agent that uses Azure AI Search (RAG) and optional MCP tool via agent_framework."""

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        model_deployment_name: str,
        enable_code_interpreter: bool = False,
        mcp_config: MCPConfig | None = None,
        search_config: SearchConfig | None = None,
    ) -> None:
        super().__init__(mcp=mcp_config)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.model_deployment_name = model_deployment_name
        self.enable_code_interpreter = enable_code_interpreter
        self.mcp = mcp_config
        self.search = search_config

        self._search_connection = None
        self.logger = logging.getLogger(__name__)

        if self.model_deployment_name in {"o3", "o4-mini"}:
            raise ValueError(
                "Foundry agents do not support reasoning models in this implementation."
            )

    # -------------------------
    # Tool construction helpers
    # -------------------------
    async def _make_azure_search_tool(self) -> Optional[AzureAISearchTool]:
        """Create Azure AI Search tool (RAG capability)."""
        if not (
            self.client
            and self.search
            and self.search.connection_name
            and self.search.index_name
        ):
            self.logger.info(
                "Azure AI Search tool not enabled (missing config or client)."
            )
            return None

        try:
            self._search_connection = await self.client.connections.get(
                name=self.search.connection_name
            )
            self.logger.info(
                "Found Azure AI Search connection: %s", self._search_connection.id
            )

            return AzureAISearchTool(
                index_connection_id=self._search_connection.id,
                index_name=self.search.index_name,
            )
        except Exception as ex:
            self.logger.error(
                "Azure AI Search tool creation failed: %s | connection=%s | index=%s",
                ex,
                getattr(self.search, "connection_name", None),
                getattr(self.search, "index_name", None),
            )
            return None

    async def _collect_tools_and_resources(self) -> tuple[List, dict]:
        """Collect tool definitions + tool_resources for agent definition creation."""
        tools: List = []
        tool_resources: dict = {}

        # Search tool
        if self.search and self.search.connection_name and self.search.index_name:
            search_tool = await self._make_azure_search_tool()
            if search_tool:
                tools.extend(search_tool.definitions)
                tool_resources = search_tool.resources
                self.logger.info(
                    "Added %d Azure AI Search tool definitions.",
                    len(search_tool.definitions),
                )
            else:
                self.logger.warning("Azure AI Search tool not configured properly.")

        # Code Interpreter
        if self.enable_code_interpreter:
            try:
                tools.append(CodeInterpreterToolDefinition())
                self.logger.info("Added Code Interpreter tool definition.")
            except ImportError as ie:
                self.logger.error("Code Interpreter dependency missing: %s", ie)

        self.logger.info("Total tool definitions collected: %d", len(tools))
        return tools, tool_resources

    # -------------------------
    # Agent lifecycle override
    # -------------------------
    async def _after_open(self) -> None:
        # Instantiate persistent AzureAIAgentClient bound to existing agent_id
        try:
            # AzureAIAgentClient(
            #     project_client=self.client,
            #     agent_id=str(definition.id),
            #     agent_name=self.agent_name,
            # )
            tools, tool_resources = await self._collect_tools_and_resources()
            self._agent = ChatAgent(
                chat_client=self.client,
                instructions=self.agent_description + " " + self.agent_instructions,
                name=self.agent_name,
                description=self.agent_description,
                tools=tools if tools else None,
                tool_choice="auto" if tools else "none",
                allow_multiple_tool_calls=True,
                temperature=0.7,
            )

        except Exception as ex:
            self.logger.error("Failed to initialize AzureAIAgentClient: %s", ex)
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
    # Definition compatibility
    # -------------------------
    async def _check_connection_compatibility(self, existing_definition: Agent) -> bool:
        """Verify existing Azure AI Search connection matches current config."""
        try:
            if not (self.search and self.search.connection_name):
                self.logger.info("No search config provided; assuming compatibility.")
                return True

            tool_resources = getattr(existing_definition, "tool_resources", None)
            if not tool_resources:
                self.logger.info(
                    "Existing agent has no tool resources; incompatible with search requirement."
                )
                return False

            azure_search = tool_resources.get("azure_ai_search", {})
            indexes = azure_search.get("indexes", [])
            if not indexes:
                self.logger.info(
                    "Existing agent has no Azure AI Search indexes; incompatible."
                )
                return False

            existing_conn_id = indexes[0].get("index_connection_id")
            if not existing_conn_id:
                self.logger.info(
                    "Existing agent missing index_connection_id; incompatible."
                )
                return False

            current_connection = await self.client.connections.get(
                name=self.search.connection_name
            )
            same = existing_conn_id == current_connection.id
            if same:
                self.logger.info("Search connection compatible: %s", existing_conn_id)
            else:
                self.logger.info(
                    "Search connection mismatch: existing=%s current=%s",
                    existing_conn_id,
                    current_connection.id,
                )
            return same
        except Exception as ex:
            self.logger.error("Error during connection compatibility check: %s", ex)
            return False

    async def _get_azure_ai_agent_definition(self, agent_name: str) -> Agent | None:
        """Return existing agent definition by name or None."""
        try:
            async for agent in self.client.agents.list_agents():
                if agent.name == agent_name:
                    self.logger.info(
                        "Found existing agent '%s' (id=%s).", agent_name, agent.id
                    )
                    return await self.client.agents.get_agent(agent.id)
            return None
        except Exception as e:
            if "ResourceNotFound" in str(e) or "404" in str(e):
                self.logger.info("Agent '%s' not found; will create new.", agent_name)
            else:
                self.logger.warning(
                    "Unexpected error listing agent '%s': %s; will attempt creation.",
                    agent_name,
                    e,
                )
            return None

    # -------------------------
    # Diagnostics helper
    # -------------------------
    async def fetch_run_details(self, thread_id: str, run_id: str) -> None:
        """Log run diagnostics for a failed run."""
        try:
            run = await self.client.agents.runs.get(thread=thread_id, run=run_id)
            self.logger.error(
                "Run failure | status=%s | id=%s | last_error=%s | usage=%s",
                getattr(run, "status", None),
                run_id,
                getattr(run, "last_error", None),
                getattr(run, "usage", None),
            )
        except Exception as ex:
            self.logger.error(
                "Failed fetching run details (thread=%s run=%s): %s",
                thread_id,
                run_id,
                ex,
            )

    # -------------------------
    # Invocation (streaming)
    # -------------------------
    async def invoke(self, prompt: str):
        """
        Stream model output for a prompt.

        Yields ChatResponseUpdate objects:
          - update.text for incremental text
          - update.contents for tool calls / usage events
        """
        if not self._agent:
            raise RuntimeError("Agent client not initialized; call open() first.")

        messages = [ChatMessage(role=Role.USER, text=prompt)]

        tools = []
        # Use mcp_tool prepared in AzureAgentBase
        if self.mcp_tool and isinstance(self.mcp_tool, HostedMCPTool):
            tools.append(self.mcp_tool)

        chat_options = ChatOptions(
            model_id=self.model_deployment_name,
            tools=tools if tools else None,
            tool_choice="auto" if tools else "none",
            allow_multiple_tool_calls=True,
            temperature=0.7,
        )

        async for update in self._agent.run_stream(
            messages=messages,
           # chat_options=chat_options,
           # instructions=self.agent_instructions,
        ):
            yield update


# -------------------------
# Factory
# -------------------------
async def create_foundry_agent(
    agent_name: str,
    agent_description: str,
    agent_instructions: str,
    model_deployment_name: str,
    mcp_config: MCPConfig | None,
    search_config: SearchConfig | None,
) -> FoundryAgentTemplate:
    """Factory to create and open a FoundryAgentTemplate (agent_framework version)."""
    agent = FoundryAgentTemplate(
        agent_name=agent_name,
        agent_description=agent_description,
        agent_instructions=agent_instructions,
        model_deployment_name=model_deployment_name,
        enable_code_interpreter=True,
        mcp_config=mcp_config,
        search_config=search_config,
    )
    await agent.open()
    return agent

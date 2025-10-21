"""Agent template for building foundry agents with Azure AI Search, Bing, and MCP plugins (agent_framework version)."""

import logging
from typing import List, Optional

from azure.ai.agents.models import Agent, AzureAISearchTool, CodeInterpreterToolDefinition
from agent_framework.azure import AzureAIAgentClient
from agent_framework import ChatMessage, Role, ChatOptions, HostedMCPTool  # HostedMCPTool for MCP plugin mapping

from v3.magentic_agents.common.lifecycle import AzureAgentBase
from v3.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from v3.config.agent_registry import agent_registry

# exception too broad warning
# pylint: disable=w0718


class FoundryAgentTemplate(AzureAgentBase):
    """Agent that uses Azure AI Search (RAG) and optional MCP tools via agent_framework."""

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        model_deployment_name: str,
        enable_code_interpreter: bool = False,
        mcp_config: MCPConfig | None = None,
        # bing_config: BingConfig | None = None,
        search_config: SearchConfig | None = None,
    ) -> None:
        super().__init__(mcp=mcp_config)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.model_deployment_name = model_deployment_name
        self.enable_code_interpreter = enable_code_interpreter
        # self.bing = bing_config
        self.mcp = mcp_config
        self.search = search_config
        self._search_connection = None
        self._bing_connection = None
        self.logger = logging.getLogger(__name__)

        if self.model_deployment_name in ["o3", "o4-mini"]:
            raise ValueError(
                "The current version of Foundry agents does not support reasoning models."
            )

    async def _make_azure_search_tool(self) -> Optional[AzureAISearchTool]:
        """Create Azure AI Search tool for RAG capabilities."""
        if not all([self.client, self.search and self.search.connection_name, self.search and self.search.index_name]):
            self.logger.info("Azure AI Search tool not enabled")
            return None

        try:
            self._search_connection = await self.client.connections.get(
                name=self.search.connection_name
            )
            self.logger.info("Found Azure AI Search connection: %s", self._search_connection.id)

            search_tool = AzureAISearchTool(
                index_connection_id=self._search_connection.id,
                index_name=self.search.index_name,
            )
            self.logger.info("Azure AI Search tool created for index: %s", self.search.index_name)
            return search_tool

        except Exception as ex:
            self.logger.error(
                "Azure AI Search tool creation failed: %s | Connection name: %s | Index name: %s | "
                "Ensure the connection exists in Azure AI Foundry portal.",
                ex,
                getattr(self.search, "connection_name", None),
                getattr(self.search, "index_name", None),
            )
            return None

    async def _collect_tools_and_resources(self) -> tuple[List, dict]:
        """Collect all available tools and tool_resources to embed in persistent agent definition."""
        tools: List = []
        tool_resources: dict = {}

        if self.search and self.search.connection_name and self.search.index_name:
            search_tool = await self._make_azure_search_tool()
            if search_tool:
                tools.extend(search_tool.definitions)
                tool_resources = search_tool.resources
                self.logger.info(
                    "Added Azure AI Search tools: %d tool definitions", len(search_tool.definitions)
                )
            else:
                self.logger.error("Azure AI Search tool not configured properly")

        if self.enable_code_interpreter:
            try:
                tools.append(CodeInterpreterToolDefinition())
                self.logger.info("Added Code Interpreter tool")
            except ImportError as ie:
                self.logger.error("Code Interpreter tool requires additional dependencies: %s", ie)

        self.logger.info("Total tools configured in definition: %d", len(tools))
        return tools, tool_resources

    async def _after_open(self) -> None:
        """Build or reuse the Azure AI agent definition; create agent_framework client."""
        definition = await self._get_azure_ai_agent_definition(self.agent_name)

        if definition is not None:
            connection_compatible = await self._check_connection_compatibility(definition)
            if not connection_compatible:
                await self.client.agents.delete_agent(definition.id)
                self.logger.info(
                    "Existing agent '%s' used incompatible connection. Creating new definition.",
                    self.agent_name,
                )
                definition = None

        if definition is None:
            tools, tool_resources = await self._collect_tools_and_resources()
            definition = await self.client.agents.create_agent(
                model=self.model_deployment_name,
                name=self.agent_name,
                description=self.agent_description,
                instructions=self.agent_instructions,
                tools=tools,
                tool_resources=tool_resources,
            )

        try:
            # Wrap existing agent definition with agent_framework client (persistent agent mode)
            self._agent = AzureAIAgentClient(
                project_client=self.client,
                agent_id=str(definition.id),
                agent_name=self.agent_name,
                thread_id=None,  # created dynamically if omitted during invocation
            )
        except Exception as ex:
            self.logger.error("Failed to initialize AzureAIAgentClient: %s", ex)
            raise

        # Register with global registry
        try:
            agent_registry.register_agent(self)
            self.logger.info("📝 Registered agent '%s' with global registry", self.agent_name)
        except Exception as registry_error:
            self.logger.warning(
                "⚠️ Failed to register agent '%s' with registry: %s", self.agent_name, registry_error
            )

    async def fetch_run_details(self, thread_id: str, run_id: str) -> None:
        """Fetch and log run details on failure for diagnostics."""
        try:
            run = await self.client.agents.runs.get(thread=thread_id, run=run_id)
            self.logger.error(
                "Run failure details | status=%s | id=%s | last_error=%s | usage=%s",
                getattr(run, "status", None),
                run_id,
                getattr(run, "last_error", None),
                getattr(run, "usage", None),
            )
        except Exception as ex:
            self.logger.error("Could not fetch run details: %s", ex)

    async def _check_connection_compatibility(self, existing_definition: Agent) -> bool:
        """Ensure existing agent definition's Azure AI Search connection matches current configuration."""
        try:
            if not self.search or not self.search.connection_name:
                self.logger.info("No search configuration provided; treating existing definition as compatible.")
                return True

            if not getattr(existing_definition, "tool_resources", None):
                self.logger.info("Existing definition lacks tool resources.")
                return not self.search.connection_name

            azure_ai_search_resources = existing_definition.tool_resources.get("azure_ai_search", {})
            if not azure_ai_search_resources:
                self.logger.info("Existing definition has no Azure AI Search resources.")
                return False

            indexes = azure_ai_search_resources.get("indexes", [])
            if not indexes:
                self.logger.info("Existing definition search resources contain no indexes.")
                return False

            existing_connection_id = indexes[0].get("index_connection_id")
            if not existing_connection_id:
                self.logger.info("Existing definition missing connection ID.")
                return False

            current_connection = await self.client.connections.get(name=self.search.connection_name)
            current_connection_id = current_connection.id
            compatible = existing_connection_id == current_connection_id

            if compatible:
                self.logger.info("Connection compatible: %s", existing_connection_id)
            else:
                self.logger.info(
                    "Connection mismatch: existing %s vs current %s",
                    existing_connection_id,
                    current_connection_id,
                )
            return compatible
        except Exception as ex:
            self.logger.error("Error checking connection compatibility: %s", ex)
            return False

    async def _get_azure_ai_agent_definition(self, agent_name: str) -> Agent | None:
        """Retrieve an existing Azure AI Agent definition by name if present."""
        try:
            agent_id = None
            agent_list = self.client.agents.list_agents()
            async for agent in agent_list:
                if agent.name == agent_name:
                    agent_id = agent.id
                    break
            if agent_id is not None:
                self.logger.info("Found existing agent definition with ID %s", agent_id)
                return await self.client.agents.get_agent(agent_id)
            return None
        except Exception as e:
            if "ResourceNotFound" in str(e) or "404" in str(e):
                self.logger.info("Agent '%s' not found; will create new definition.", agent_name)
            else:
                self.logger.warning(
                    "Unexpected error retrieving agent '%s': %s. Proceeding to create new definition.",
                    agent_name,
                    e,
                )
            return None

    async def invoke(self, prompt: str):
        """
        Stream model output for a prompt.

        Yields agent_framework ChatResponseUpdate objects:
        - update.text for incremental text
        - update.contents for tool calls / usage events
        """
        if not hasattr(self, "_agent") or self._agent is None:
            raise RuntimeError("Agent client not initialized; call open() first.")

        messages = [ChatMessage(role=Role.USER, text=prompt)]

        tools = []
        # Map MCP plugin (if any) to HostedMCPTool for runtime tool calling
        if self.mcp_plugin:
            # Minimal HostedMCPTool; advanced mapping (approval modes, categories) can be added later.
            tools.append(
                HostedMCPTool(
                    name=self.mcp_plugin.name,
                    server_label=self.mcp_plugin.name.replace(" ", "_"),
                    description=getattr(self.mcp_plugin, "description", ""),
                )
            )

        chat_options = ChatOptions(
            model_id=self.model_deployment_name,
            tools=tools if tools else None,
            tool_choice="auto",
            allow_multiple_tool_calls=True,
            temperature=0.7,
        )

        async for update in self._agent.get_streaming_response(
            messages=messages,
            chat_options=chat_options,
            instructions=self.agent_instructions,
        ):
            yield update


async def create_foundry_agent(
    agent_name: str,
    agent_description: str,
    agent_instructions: str,
    model_deployment_name: str,
    mcp_config: MCPConfig,
    # bing_config: BingConfig,
    search_config: SearchConfig,
) -> FoundryAgentTemplate:
    """Factory function to create and open a FoundryAgentTemplate (agent_framework version)."""
    agent = FoundryAgentTemplate(
        agent_name=agent_name,
        agent_description=agent_description,
        agent_instructions=agent_instructions,
        model_deployment_name=model_deployment_name,
        enable_code_interpreter=True,
        mcp_config=mcp_config,
        # bing_config=bing_config,
        search_config=search_config,
    )
    await agent.open()
    return agent
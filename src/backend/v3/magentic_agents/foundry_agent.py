"""Agent template for building foundry agents with Azure AI Search, Bing, and MCP plugins."""

import logging
from typing import Awaitable, List, Optional

from azure.ai.agents.models import AzureAISearchTool, CodeInterpreterToolDefinition
from semantic_kernel.agents import Agent, AzureAIAgent  # pylint: disable=E0611
from v3.magentic_agents.common.lifecycle import AzureAgentBase
from v3.magentic_agents.models.agent_models import MCPConfig, SearchConfig

from v3.config.agent_registry import agent_registry

# from v3.magentic_agents.models.agent_models import (BingConfig, MCPConfig,
#                                                     SearchConfig)

# exception too broad warning
# pylint: disable=w0718


class FoundryAgentTemplate(AzureAgentBase):
    """Agent that uses Azure AI Search and Bing tools for information retrieval."""

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
        # input validation
        if self.model_deployment_name in ["o3", "o4-mini"]:
            raise ValueError(
                "The current version of Foundry agents do not support reasoning models."
            )

    # Uncomment to enable bing grounding capabilities (requires Bing connection in Foundry and uncommenting other code)
    # async def _make_bing_tool(self) -> Optional[BingGroundingTool]:
    #     """Create Bing search tool for web search."""
    #     if not all([self.client, self.bing.connection_name]):
    #         self.logger.info("Bing tool not enabled")
    #         return None
    #     try:
    #         self._bing_connection = await self.client.connections.get(name=self.bing.connection_name)
    #         bing_tool = BingGroundingTool(connection_id=self._bing_connection.id)
    #         self.logger.info("Bing tool created with connection %s", self._bing_connection.id)
    #         return bing_tool
    #     except Exception as ex:
    #         self.logger.error("Bing tool creation failed: %s", ex)
    #         return None

    async def _make_azure_search_tool(self) -> Optional[AzureAISearchTool]:
        """Create Azure AI Search tool for RAG capabilities."""
        if not all([self.client, self.search.connection_name, self.search.index_name]):
            self.logger.info("Azure AI Search tool not enabled")
            return None

        try:
            # Get the existing connection by name
            self._search_connection = await self.client.connections.get(
                name=self.search.connection_name
            )
            self.logger.info(
                "Found Azure AI Search connection: %s", self._search_connection.id
            )

            # Create the Azure AI Search tool
            search_tool = AzureAISearchTool(
                index_connection_id=self._search_connection.id,  # Try connection_id first
                index_name=self.search.index_name,
            )
            self.logger.info(
                "Azure AI Search tool created for index: %s", self.search.index_name
            )
            return search_tool

        except Exception as ex:
            self.logger.error(
                "Azure AI Search tool creation failed: %s | Connection name: %s | Index name: %s | "
                "Make sure the connection exists in Azure AI Foundry portal",
                ex,
                self.search.connection_name,
                self.search.index_name,
            )
            return None

    async def _collect_tools_and_resources(self) -> tuple[List, dict]:
        """Collect all available tools and their corresponding tool_resources."""
        tools = []
        tool_resources = {}

        # Add Azure AI Search tool FIRST
        if self.search and self.search.connection_name and self.search.index_name:
            search_tool = await self._make_azure_search_tool()
            if search_tool:
                tools.extend(search_tool.definitions)
                tool_resources = search_tool.resources
                self.logger.info(
                    "Added Azure AI Search tools: %d tools",
                    len(search_tool.definitions),
                )
            else:
                self.logger.error(
                    "Something went wrong, Azure AI Search tool not configured"
                )

        # Add Bing search tool
        # if self.bing and self.bing.connection_name:
        #     bing_tool = await self._make_bing_tool()
        #     if bing_tool:
        #         tools.extend(bing_tool.definitions)
        #         self.logger.info("Added Bing search tools: %d tools", len(bing_tool.definitions))
        #     else:
        #         self.logger.error("Something went wrong, Bing tool not configured")

        if self.enable_code_interpreter:
            try:
                tools.append(CodeInterpreterToolDefinition())
                self.logger.info("Added Code Interpreter tool")
            except ImportError as ie:
                self.logger.error(
                    "Code Interpreter tool requires additional dependencies: %s", ie
                )

        self.logger.info("Total tools configured: %d", len(tools))
        return tools, tool_resources

    async def _after_open(self) -> None:
        """Initialize the AzureAIAgent with the collected tools and MCP plugin."""

        # Try to get existing agent definition from Foundry
        definition = await self._get_azure_ai_agent_definition(self.agent_name)

        # Check if existing definition uses the same connection name
        if definition is not None:
            connection_compatible = await self._check_connection_compatibility(definition)
            if not connection_compatible:
                await self.client.agents.delete_agent(definition.id)
                self.logger.info(f"Existing agent '{self.agent_name}' uses different connection. Creating new agent definition.")
                definition = None

        # If not found in Foundry, create a new one
        if definition is None:
            # Collect all tools
            tools, tool_resources = await self._collect_tools_and_resources()

            # Create agent definition with all tools
            definition = await self.client.agents.create_agent(
                model=self.model_deployment_name,
                name=self.agent_name,
                description=self.agent_description,
                instructions=self.agent_instructions,
                tools=tools,
                tool_resources=tool_resources,
            )

        # Add MCP plugins if available
        plugins = [self.mcp_plugin] if self.mcp_plugin else []

        try:
            self._agent = AzureAIAgent(
                client=self.client,
                definition=definition,
                plugins=plugins,
            )
        except Exception as ex:
            self.logger.error("Failed to create AzureAIAgent: %s", ex)
            raise

        # Register agent with global registry for tracking and cleanup
        try:
            agent_registry.register_agent(self)
            self.logger.info(f"📝 Registered agent '{self.agent_name}' with global registry")
        except Exception as registry_error:
            self.logger.warning(f"⚠️ Failed to register agent '{self.agent_name}' with registry: {registry_error}")

        # # After self._agent creation in _after_open:
        # # Diagnostics
        # try:
        #     tool_names = [t.get("function", {}).get("name") for t in (definition.tools or []) if isinstance(t, dict)]
        #     self.logger.info(
        #         "Foundry agent '%s' initialized. Azure tools: %s | MCP plugin: %s",
        #         self.agent_name,
        #         tool_names,
        #         getattr(self.mcp_plugin, 'name', None)
        #     )
        #     if not tool_names and not plugins:
        #         self.logger.warning(
        #             "Foundry agent '%s' has no Azure tool definitions and no MCP plugin. "
        #             "Subsequent tool calls may fail.", self.agent_name
        #         )
        # except Exception as diag_ex:
        #     self.logger.warning("Diagnostics collection failed: %s", diag_ex)

        # self.logger.info("%s initialized with %d tools and %d plugins", self.agent_name, len(tools), len(plugins))

    async def fetch_run_details(self, thread_id: str, run_id: str):
        """Fetch and log run details after a failure."""
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

    async def _check_connection_compatibility(self, existing_definition) -> bool:
        """
        Check if the existing agent definition uses the same connection name as the current configuration.

        Args:
            existing_definition: The existing agent definition from Azure AI Foundry

        Returns:
            bool: True if connections are compatible, False otherwise
        """
        try:
            # Check if we have search configuration to compare
            if not self.search or not self.search.connection_name:
                self.logger.info("No search configuration to compare")
                return True

            # Get tool resources from existing definition
            if not hasattr(existing_definition, 'tool_resources') or not existing_definition.tool_resources:
                self.logger.info("Existing definition has no tool resources")
                return not self.search.connection_name  # Compatible if we also don't need search

            # Check Azure AI Search tool resources
            azure_ai_search_resources = existing_definition.tool_resources.get('azure_ai_search', {})
            if not azure_ai_search_resources:
                self.logger.info("Existing definition has no Azure AI Search resources")
                return not self.search.connection_name  # Compatible if we also don't need search

            # Get connection ID from existing definition
            indexes = azure_ai_search_resources.get('indexes')[0]
            existing_connection_id = indexes.get('index_connection_id')
            if not existing_connection_id:
                self.logger.info("Existing definition has no connection ID")
                return False

            # Get the current connection to compare
            try:
                current_connection = await self.client.connections.get(name=self.search.connection_name)
                current_connection_id = current_connection.id

                # Compare connection IDs
                is_compatible = existing_connection_id == current_connection_id

                if is_compatible:
                    self.logger.info(f"Connection compatible: existing connection ID {existing_connection_id} matches current connection")
                else:
                    self.logger.info(f"Connection mismatch: existing connection ID {existing_connection_id} != current connection ID {current_connection_id}")

                return is_compatible

            except Exception as conn_ex:
                self.logger.error(f"Failed to get current connection '{self.search.connection_name}': {conn_ex}")
                return False

        except Exception as ex:
            self.logger.error(f"Error checking connection compatibility: {ex}")
            return False

    async def _get_azure_ai_agent_definition(
        self, agent_name: str
    ) -> Awaitable[Agent | None]:

        """
        Gets an Azure AI Agent with the specified name and instructions using AIProjectClient if it is already created.
        """
        # # First try to get an existing agent with this name as assistant_id
        try:
            agent_id = None
            agent_list = self.client.agents.list_agents()
            async for agent in agent_list:
                if agent.name == agent_name:
                    agent_id = agent.id
                    break
            # If the agent already exists, we can use it directly
            # Get the existing agent definition
            if agent_id is not None:
                logging.info(f"Agent with ID {agent_id} exists.")

                existing_definition = await self.client.agents.get_agent(agent_id)

                return existing_definition
            else:
                return None
        except Exception as e:
            # The Azure AI Projects SDK throws an exception when the agent doesn't exist
            # (not returning None), so we catch it and proceed to create a new agent
            if "ResourceNotFound" in str(e) or "404" in str(e):
                logging.info(
                    f"Agent with ID {agent_name} not found. Will create a new one."
                )
            else:
                # Log unexpected errors but still try to create a new agent
                logging.warning(
                    f"Unexpected error while retrieving agent {agent_name}: {str(e)}. Attempting to create new agent."
                )


async def create_foundry_agent(
    agent_name: str,
    agent_description: str,
    agent_instructions: str,
    model_deployment_name: str,
    mcp_config: MCPConfig,
    # bing_config:BingConfig,
    search_config: SearchConfig,
) -> FoundryAgentTemplate:
    """Factory function to create and open a ResearcherAgent."""
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

""" Agent template for building foundry agents with Azure AI Search, Bing, and MCP plugins. """

import asyncio
import logging
from typing import List, Optional

from azure.ai.agents.models import (AzureAISearchTool, BingGroundingTool,
                                    CodeInterpreterToolDefinition)
from semantic_kernel.agents import AzureAIAgent  # pylint: disable=E0611
from semantic_kernel.agents import \
    AzureAIAgentSettings  # pylint: disable=E0611
from v3.magentic_agents.common.lifecycle import AzureAgentBase
from v3.magentic_agents.models.agent_models import (BingConfig, MCPConfig,
                                                    SearchConfig)

# pylint: disable=w0718 
# - exception too broad warning

# Log to console
# logging.basicConfig(
#     level=logging.INFO,  # Set the logging level to INFO
#     format='%(asctime)s - %(levelname)s - %(message)s',  # Customize the log format
#     handlers=[
#         logging.StreamHandler()  # Output logs to the console
#     ]
# )

class FoundryAgentTemplate(AzureAgentBase):
    """Agent that uses Azure AI Search and Bing tools for information retrieval."""

    def __init__(self, agent_name: str, 
                 agent_description: str, 
                 agent_instructions: str,
                 model_deployment_name: str,
                 enable_code_interpreter: bool = False, 
                 mcp_config: MCPConfig | None = None,
                 bing_config: BingConfig | None = None,
                 search_config: SearchConfig | None = None) -> None:
        super().__init__(mcp=mcp_config)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.model_deployment_name = model_deployment_name
        self.enable_code_interpreter = enable_code_interpreter
        self.bing = bing_config
        self.mcp = mcp_config
        self.search = search_config
        self._search_connection = None
        self._bing_connection = None
        self.logger = logging.getLogger(__name__)
        # input validation
        if self.model_deployment_name is any(["o3", "o4-mini"]):
            raise ValueError("The current version of Foundry agents do not support reasoning models.")

    async def _make_bing_tool(self) -> Optional[BingGroundingTool]:
        """Create Bing search tool for web search."""
        if not all([self.client, self.bing.connection_name]):
            self.logger.info("Bing tool not enabled")
            return None
        try:
            self._bing_connection = await self.client.connections.get(name=self.bing.connection_name)
            bing_tool = BingGroundingTool(connection_id=self._bing_connection.id)
            self.logger.info("Bing tool created with connection %s", self._bing_connection.id)
            return bing_tool
        except Exception as ex:
            self.logger.error("Bing tool creation failed: %s", ex)
            return None

    async def _make_azure_search_tool(self) -> Optional[AzureAISearchTool]:
        """Create Azure AI Search tool for RAG capabilities."""
        if not all([self.client, self.search.connection_name, self.search.index_name]):
            self.logger.info("Azure AI Search tool not enabled")
            return None

        try:
            # Get the existing connection by name
            self._search_connection = await self.client.connections.get(name=self.search.connection_name)
            self.logger.info("Found Azure AI Search connection: %s", self._search_connection.id)

            # Create the Azure AI Search tool
            search_tool = AzureAISearchTool(
                index_connection_id=self._search_connection.id,  # Try connection_id first
                index_name=self.search.index_name
            )
            self.logger.info("Azure AI Search tool created for index: %s", self.search.index_name)
            return search_tool

        except Exception as ex:
            self.logger.error(f"Azure AI Search tool creation failed: {ex}   Connection name: " /
                              f"{self.search.connection_name}   Index name: {self.search.index_name}" /
                              " Make sure the connection exists in Azure AI Foundry portal")
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
                self.logger.info("Added Azure AI Search tools: %d tools", len(search_tool.definitions))
            else:
                self.logger.error("Something went wrong, Azure AI Search tool not configured")

        # Add Bing search tool
        if self.bing and self.bing.connection_name:
            bing_tool = await self._make_bing_tool()
            if bing_tool:
                tools.extend(bing_tool.definitions)
                self.logger.info("Added Bing search tools: %d tools", len(bing_tool.definitions))
            else:
                self.logger.error("Something went wrong, Bing tool not configured")

        if self.enable_code_interpreter:
            try:
                tools.append(CodeInterpreterToolDefinition())
                self.logger.info("Added Code Interpreter tool")
            except ImportError as ie:
                self.logger.error("Code Interpreter tool requires additional dependencies: %s", ie)

        self.logger.info("Total tools configured: %d", len(tools))
        return tools, tool_resources

    async def _after_open(self) -> None:

        # Collect all tools
        tools, tool_resources = await self._collect_tools_and_resources()

        # Create agent definition with all tools
        definition = await self.client.agents.create_agent(
            model=self.model_deployment_name,
            name=self.agent_name,
            description=self.agent_description,
            instructions=self.agent_instructions,
            tools=tools,
            tool_resources=tool_resources
        )

        # Add MCP plugins if available
        plugins = [self.mcp_plugin] if self.mcp_plugin else []

        self._agent = AzureAIAgent(
            client=self.client,
            definition=definition,
            plugins=plugins,
        )

        self.logger.info("%s initialized with %d tools and %d plugins", self.agent_name, len(tools), len(plugins))


async def create_foundry_agent(agent_name:str,
                               agent_description:str, 
                               agent_instructions:str,
                               model_deployment_name:str, 
                               mcp_config:MCPConfig, 
                               bing_config:BingConfig, 
                               search_config:SearchConfig) -> FoundryAgentTemplate:
    
    """Factory function to create and open a ResearcherAgent."""
    agent = FoundryAgentTemplate(agent_name=agent_name, 
                                 agent_description=agent_description, 
                                 agent_instructions=agent_instructions,
                                 model_deployment_name=model_deployment_name,
                                 enable_code_interpreter=True,
                                 mcp_config=mcp_config,
                                 bing_config=bing_config,
                                 search_config=search_config)
    await agent.open()
    return agent


"""Agent template for building Foundry agents with Azure AI Search, optional MCP tool, and Code Interpreter (agent_framework version)."""

import logging
from typing import List, Optional

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Role,
    HostedFileSearchTool,
    HostedVectorStoreContent,
    HostedCodeInterpreterTool,
)
from v4.magentic_agents.common.lifecycle import AzureAgentBase
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from v4.config.agent_registry import agent_registry


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
        super().__init__(mcp=mcp_config, model_deployment_name=model_deployment_name)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.enable_code_interpreter = enable_code_interpreter
        self.search = search_config
        self.logger = logging.getLogger(__name__)

    # -------------------------
    # Tool construction helpers
    # -------------------------
    async def _make_file_search_tool(self) -> Optional[HostedFileSearchTool]:
        """Create File Search tool (RAG capability) using vector stores."""
        if not self.search or not self.search.vector_store_id:
            self.logger.info("File search tool not enabled (missing vector_store_id).")
            return None

        try:
            # HostedFileSearchTool uses vector stores, not direct Azure AI Search indexes
            file_search_tool = HostedFileSearchTool(
                inputs=[HostedVectorStoreContent(vector_store_id=self.search.vector_store_id)],
                max_results=self.search.max_results if hasattr(self.search, 'max_results') else None,
                description="Search through indexed documents"
            )
            self.logger.info("Created HostedFileSearchTool with vector store: %s", self.search.vector_store_id)
            return file_search_tool
        except Exception as ex:
            self.logger.error("File search tool creation failed: %s", ex)
            return None

    async def _collect_tools(self) -> List:
        """Collect tool definitions for ChatAgent."""
        tools: List = []

        # File Search tool (RAG)
        if self.search:
            search_tool = await self._make_file_search_tool()
            if search_tool:
                tools.append(search_tool)
                self.logger.info("Added File Search tool.")

        # Code Interpreter
        if self.enable_code_interpreter:
            try:
                code_tool = HostedCodeInterpreterTool()
                tools.append(code_tool)
                self.logger.info("Added Code Interpreter tool.")
            except Exception as ie:
                self.logger.error("Code Interpreter tool creation failed: %s", ie)

        # MCP Tool (from base class)
        if self.mcp_tool:
            tools.append(self.mcp_tool)
            self.logger.info("Added MCP tool: %s", self.mcp_tool.name)

        self.logger.info("Total tools collected: %d", len(tools))
        return tools

    # -------------------------
    # Agent lifecycle override
    # -------------------------
    async def _after_open(self) -> None:
        """Initialize ChatAgent after connections are established."""
        try:
            tools = await self._collect_tools()
            
            self._agent = ChatAgent(
                chat_client=self.client,
                instructions=self.agent_instructions,
                name=self.agent_name,
                description=self.agent_description,
                tools=tools if tools else None,
                tool_choice="auto" if tools else "none",
                temperature=0.7,
                model_id=self.model_deployment_name,
            )
            
            self.logger.info("Initialized ChatAgent '%s'", self.agent_name)
        except Exception as ex:
            self.logger.error("Failed to initialize ChatAgent: %s", ex)
            raise

        # Register agent globally
        try:
            agent_registry.register_agent(self)
            self.logger.info("Registered agent '%s' in global registry.", self.agent_name)
        except Exception as reg_ex:
            self.logger.warning("Could not register agent '%s': %s", self.agent_name, reg_ex)

    # -------------------------
    # Invocation (streaming)
    # -------------------------
    async def invoke(self, prompt: str):
        """Stream model output for a prompt."""
        if not self._agent:
            raise RuntimeError("Agent not initialized; call open() first.")

        messages = [ChatMessage(role=Role.USER, text=prompt)]
        
        async for update in self._agent.run_stream(messages=messages):
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
    """Factory to create and open a FoundryAgentTemplate."""
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
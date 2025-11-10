"""Reasoning agent using agent_framework with direct Azure AI Search integration."""

import logging
import os
from typing import Optional

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Role,
)
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential


#from agent_framework.azure import AzureOpenAIChatClient



from v4.magentic_agents.common.lifecycle import MCPEnabledBase
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from v4.config.agent_registry import agent_registry


logger = logging.getLogger(__name__)


class ReasoningAgentTemplate(MCPEnabledBase):
    """
    Reasoning agent using agent_framework with direct Azure AI Search integration.
    
    This agent:
    - Uses reasoning models (o1, o3-mini, etc.)
    - Augments prompts with search results from Azure AI Search
    - Supports optional MCP tools
    - Does NOT use Azure AI Agent service (direct client connection)
    """

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        model_deployment_name: str,
        project_endpoint: str | None = "",
        search_config: SearchConfig | None = None,
        mcp_config: MCPConfig | None = None,
        max_search_docs: int = 3,
    ) -> None:
        """Initialize reasoning agent.
        
        Args:
            agent_name: Name of the agent
            agent_description: Description of the agent's purpose
            agent_instructions: System instructions for the agent
            model_deployment_name: Reasoning model deployment (e.g., "o1", "o3-mini")
            project_endpoint: Azure AI Project endpoint URL
            search_config: Optional search configuration for Azure AI Search
            mcp_config: Optional MCP server configuration
            max_search_docs: Maximum number of search documents to retrieve
        """
        super().__init__(mcp=mcp_config)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.base_instructions = agent_instructions
        self.model_deployment_name = model_deployment_name
        self.project_endpoint = project_endpoint
        self.search_config = search_config
        self.max_search_docs = max_search_docs
        
        # Azure resources
        self._credential: Optional[DefaultAzureCredential] = None
        self._client: Optional[AzureAIAgentClient] = None
        
        
        self.logger = logging.getLogger(__name__)

    async def _after_open(self) -> None:
        """Initialize Azure client and search after base setup."""
        try:
            # Initialize Azure credential
            self._credential = DefaultAzureCredential()
            if self._stack:
                await self._stack.enter_async_context(self._credential)

            # Create AzureAIAgentClient for direct model access
            self._client = AzureAIAgentClient(
                project_endpoint=self.project_endpoint,
                model_deployment_name=self.model_deployment_name,
                async_credential=self._credential,
            )
            if self._stack:
                await self._stack.enter_async_context(self._client)

            self.logger.info(
                "Initialized AzureAIAgentClient for model '%s'",
                self.model_deployment_name
            )


            # Initialize MCP tools (called after stack is ready)
            await self._prepare_mcp_tool()
            
            if self.mcp_tool:
                self.logger.info(
                    "MCP tool '%s' ready with %d functions",
                    self.mcp_tool.name,
                    len(self.mcp_tool.functions) if hasattr(self.mcp_tool, 'functions') else 0
                )

            # Prepare tools for the agent
            tools = self._prepare_tools()

            # Create ChatAgent instance (similar to foundry_agent)
            self._agent = ChatAgent(
                chat_client=self._client,
                instructions=self.base_instructions,
                name=self.agent_name,
                description=self.agent_description,
                tools=tools if tools else None,
                tool_choice="auto" if tools else "none",
                temperature=1.0,  # Reasoning models use fixed temperature
                model_id=self.model_deployment_name,
            )
            # Register agent globally
            try:
                agent_registry.register_agent(self)
                self.logger.info("Registered agent '%s' in global registry.", self.agent_name)
            except Exception as reg_ex:
                self.logger.warning(
                    "Could not register agent '%s': %s",
                    self.agent_name,
                    reg_ex
                )

        except Exception as ex:
            self.logger.error("Failed to initialize ReasoningAgentTemplate: %s", ex)
            raise

    async def close(self) -> None:
        """Close all resources."""
        try:

            # Unregister from registry
            try:
                agent_registry.unregister_agent(self)
            except Exception:  
                pass

        finally:
            await super().close()
            self._client = None
            self._credential = None

    def _prepare_tools(self) -> list:
        """
        Prepare tools for reasoning model invocation.
        
        Returns:
            List of tools (currently only MCP tools supported for reasoning models)
        """
        tools = []
        
        if self.mcp_tool:
            tools.append(self.mcp_tool)
            self.logger.debug("Added MCP tool '%s' to tools list", self.mcp_tool.name)
        
        return tools

    @property
    def client(self) -> Optional[AzureAIAgentClient]:
        """Access to underlying client for compatibility."""
        return self._client


# -------------------------
# Factory
# -------------------------
async def create_reasoning_agent(
    agent_name: str,
    agent_description: str,
    agent_instructions: str,
    model_deployment_name: str,
    azure_ai_project_endpoint: str | None = None,
    search_config: SearchConfig | None = None,
    mcp_config: MCPConfig | None = None,
) -> ReasoningAgentTemplate:
    """
    Factory to create and open a ReasoningAgentTemplate.
    
    Args:
        agent_name: Name of the agent
        agent_description: Description of the agent's purpose
        agent_instructions: System instructions for the agent
        model_deployment_name: Reasoning model deployment (e.g., "o1", "o3-mini")
        azure_ai_project_endpoint: Azure AI Project endpoint (defaults to env var)
        search_config: Optional Azure AI Search configuration
        mcp_config: Optional MCP server configuration
        
    Returns:
        Initialized and opened ReasoningAgentTemplate instance
        
    Example:
        ```python
        from af.magentic_agents.models.agent_models import SearchConfig, MCPConfig
        
        # With search augmentation and MCP tools
        agent = await create_reasoning_agent(
            agent_name="ReasoningAgent",
            agent_description="Agent that uses reasoning models with RAG",
            agent_instructions="You are a helpful reasoning assistant.",
            model_deployment_name="o1",
            search_config=SearchConfig(
                endpoint="https://my-search.search.windows.net",
                index_name="my-index",
                api_key="...",
            ),
            mcp_config=MCPConfig(
                url="https://my-mcp-server.com",
                name="HR Tools",
                description="HR data access tools"
            ),
        )
        
        ```
    """
    # Get endpoint from env if not provided
    endpoint = azure_ai_project_endpoint 
    if not endpoint:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT must be provided or set as environment variable"
        )

    agent = ReasoningAgentTemplate(
        agent_name=agent_name,
        agent_description=agent_description,
        agent_instructions=agent_instructions,
        model_deployment_name=model_deployment_name,
        project_endpoint=endpoint,
        search_config=search_config,
        mcp_config=mcp_config,
    )
    await agent.open()
    return agent
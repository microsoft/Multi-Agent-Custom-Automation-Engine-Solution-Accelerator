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
from v4.magentic_agents.reasoning_search import ReasoningSearch, create_reasoning_search
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
        
        # Search integration
        self.reasoning_search: Optional[ReasoningSearch] = None
        
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

            # Initialize search capabilities if configured
            if self.search_config:
                self.reasoning_search = await create_reasoning_search(self.search_config)
                if self.reasoning_search.is_available():
                    self.logger.info(
                        "Initialized Azure AI Search with index '%s'",
                        self.search_config.index_name
                    )
                else:
                    self.logger.warning("Azure AI Search initialization failed or incomplete config")

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
            # Close reasoning search
            if self.reasoning_search:
                await self.reasoning_search.close()
                self.reasoning_search = None

            # Unregister from registry
            try:
                agent_registry.unregister_agent(self)
            except Exception:  
                pass

        finally:
            await super().close()
            self._client = None
            self._credential = None

    async def _augment_with_search(self, prompt: str) -> str:
        """
        Augment the prompt with relevant search results.
        
        Args:
            prompt: Original user prompt
            
        Returns:
            Augmented instructions including search results
        """
        instructions = self.base_instructions
        
        if not self.reasoning_search or not self.reasoning_search.is_available():
            return instructions

        if not prompt.strip():
            return instructions

        try:
            # Fetch relevant documents
            docs = await self.reasoning_search.search_documents(
                query=prompt,
                limit=self.max_search_docs
            )
            
            if docs:
                # Format documents for inclusion
                doc_context = "\n\n".join(
                    f"[Document {i+1}]\n{doc}" 
                    for i, doc in enumerate(docs)
                )
                
                # Append to instructions
                instructions = (
                    f"{instructions}\n\n"
                    f"**Relevant Reference Documents:**\n{doc_context}\n\n"
                    f"Use the above documents only if they help answer the user's question. "
                    f"Do not mention the documents unless directly relevant."
                )
                
                self.logger.debug(
                    "Augmented prompt with %d search documents",
                    len(docs)
                )
        except Exception as ex:
            self.logger.warning("Search augmentation failed: %s", ex)

        return instructions

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
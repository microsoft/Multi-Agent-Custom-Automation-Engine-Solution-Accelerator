# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from typing import Any, Dict, List, Optional

from azure.ai.agents.models import (AzureAISearchTool, BingGroundingTool,
                                    CodeInterpreterToolDefinition)
from azure.core.credentials import AzureKeyCredential
from azure.identity import InteractiveBrowserCredential
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from semantic_kernel.agents.azure_ai.azure_ai_agent_settings import \
    AzureAIAgentSettings
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
from semantic_kernel.functions import kernel_function

# Environment variables are used in two ways:
# 1. Automatically by AzureAIAgentSettings (AZURE_OPENAI_... variables)
# 2. Directly created below (for bing grounding and MCP capabilities)

class FoundryAgentTemplate:
    """A template agent that manages its own async context for client connections."""

    AGENT_NAME = "EnhancedResearchAgent"
    AGENT_DESCRIPTION = "A comprehensive research assistant with web search, MCP capabilities, and RAG-powered knowledge retrieval."  # Updated
    AGENT_INSTRUCTIONS="""You are an Enhanced Research Agent with access to:
1. Bing web search capabilities for current events and real-time information
2. MCP tools for specialized operations
3. RAG (Retrieval-Augmented Generation) capabilities for accessing indexed knowledge

CRITICAL CAPABILITIES:
- Use Bing search for current events, recent news, or time-sensitive information
- Use knowledge_search for internal documents, policies, procedures, and organizational knowledge
- Examine your available MCP tools and use them where applicable
- Always cite sources and provide URLs when available

RAG SEARCH STRATEGY:
- Use knowledge_search for questions about internal documentation, customers, policies, or procedures
- Include relevant excerpts from retrieved documents in your responses
- Always cite document sources and confidence scores
- Combine RAG results with web search when comprehensive coverage is needed

AUTONOMY: You should make reasonable decisions and proceed without asking for user confirmation unless absolutely critical. When in doubt, choose the most comprehensive approach.

SEARCH STRATEGY:
- Always search for current events, recent news, or dates using Bing
- Use knowledge search for internal/organizational information
- Use specific, targeted search queries with current year (2025)
- Search multiple times with different keywords if needed
- Include dates, locations, and specific terms in searches

DECISION MAKING:
- If multiple approaches are possible, choose the most thorough one
- Don't ask for permission to proceed - just do the work
- Only ask for clarification if the task is genuinely ambiguous

Always use your search tools and MCP tools - do not rely solely on training data for current information.
Provide comprehensive results with URLs and sources when available."""

    initialized = False

    # To do: pass capability parameters in the constructor:
    # To do: pass name, description and instructions in the constructor
    # 1. MCP server endpoint and use
    # 2. Bing grounding option
    # 3. Reasoning model name (some settings are different and cannot be used with bing grounding)
    # 4. Coding skills - CodeInterpreterToolDefinition
    # 5. Grounding Data - requires index endpoint
    # This will allow the factory to create all base models except researcher with bing - this is
    # is coming with a deep research offering soon (preview now in two regions)
    def __init__(self):
        self._agent = None
        self.client = None
        self.creds = None
        self.mcp_plugin = None
        self.search_api_version = os.environ.get("AZURE_AI_SEARCH_API_VERSION", "")
        self.search_service_name = os.environ.get("AZURE_AI_SEARCH_ENDPOINT", "")
        self.search_index_name = os.environ.get("AZURE_AI_SEARCH_INDEX_NAME", "")
        self.search_api_key = os.environ.get("AZURE_AI_SEARCH_API_KEY", "")
        self.bing_tool_name = os.environ.get("BING_CONNECTION_NAME", "")
        self.mcp_srv_endpoint = os.environ.get("MCP_SERVER_ENDPOINT", "")
        self.mcp_srv_name = os.environ.get("MCP_SERVER_NAME", "")
        self.mcp_srv_description = os.environ.get("MCP_SERVER_DESCRIPTION", "")
        self.tenant_id = os.environ.get("TENANT_ID", "")
        self.client_id = os.environ.get("CLIENT_ID", "")

    def __getattr__(self, name):
        """Delegate all attribute access to the wrapped agent."""
        if hasattr(self, '_agent') and self._agent is not None:
            return getattr(self._agent, name)
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    async def __aenter__(self):
        """Initialize the agent and return it within an async context."""
        # Initialize credentials and client
        if not self.initialized:
           await self.create_agent_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the async contexts."""
        await self.close()

    @kernel_function(  # Add this entire method
        name="knowledge_search",
        description="Search internal knowledge base using Azure AI Search for organizational documents, policies, procedures, and internal information."
    )
    async def knowledge_search(self, query: str, top_k: int = 5) -> str:
        """
        Search the knowledge base using Azure AI Search.

        Args:
            query: The search query string
            top_k: Number of top results to return (default: 5)

        Returns:
            Formatted search results with sources and confidence scores
        """
        if not self.search_client:
            return "Knowledge search is not available. Azure Search is not configured."

        try:
            print(f"🔍 Searching for: '{query}'")
            # Perform semantic search
            search_results = await self.search_client.search(
                search_text=query,
                query_type="semantic",
                semantic_configuration_name="default",
                top=top_k,
                select=["content", "title", "source", "metadata"],
                highlight_fields="content",
                include_total_count=True
            )

            results = []
            async for result in search_results:
                score = result.get('@search.score', 0)
                highlights = result.get('@search.highlights', {})
                content = highlights.get('content', [result.get('content', '')])
                if isinstance(content, list):
                    content = ' ... '.join(content)

                result_info = {
                    'title': result.get('title', 'Unknown Title'),
                    'content': content[:500] + '...' if len(str(content)) > 500 else content,
                    'source': result.get('source', 'Unknown Source'),
                    'score': round(score, 3),
                    'metadata': result.get('metadata', {})
                }
                results.append(result_info)

            if not results:
                return f"No relevant documents found for query: '{query}'"

            formatted_results = f"Found {len(results)} relevant documents for '{query}':\n\n"

            for i, result in enumerate(results, 1):
                formatted_results += f"**Result {i} (Score: {result['score']}):**\n"
                formatted_results += f"Title: {result['title']}\n"
                formatted_results += f"Source: {result['source']}\n"
                formatted_results += f"Content: {result['content']}\n"
                if result['metadata']:
                    formatted_results += f"Metadata: {result['metadata']}\n"
                formatted_results += "\n" + "-" * 50 + "\n\n"

            return formatted_results

        except Exception as e:
            error_msg = f"Error searching knowledge base: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    async def _initialize_search_client(self):
        """Initialize Azure Search client if configured."""
        if not all([self.search_service_name, self.search_index_name]):
            print("ℹ️  Azure Search not configured - RAG capabilities disabled")
            print(f"   Missing: AZURE_SEARCH_SERVICE_NAME={bool(self.search_service_name)}, AZURE_SEARCH_INDEX_NAME={bool(self.search_index_name)}")
            return

        try:
            search_endpoint = f"https://{self.search_service_name}.search.windows.net"
            key = AzureKeyCredential(self.search_api_key)

            self.search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=self.search_index_name,
                credential=key
            )

            print(f"✅ Azure Search client created")
            print(f"   Endpoint: {search_endpoint}")
            print(f"   Index: {self.search_index_name}")
            
            # Run debug checks
            await self.debug_search_config()

        except Exception as e:
            print(f"⚠️  Failed to initialize Azure Search client: {e}")
            self.search_client = None

    async def debug_search_config(self):
        """Debug Azure Search configuration and connectivity."""
        print("🔍 DEBUG: Azure Search Configuration")
        print(f"   Service Name: '{self.search_service_name}' (empty: {not self.search_service_name})")
        print(f"   Index Name: '{self.search_index_name}' (empty: {not self.search_index_name})")
        print(f"   Search Client: {self.search_client is not None}")
        
        if self.search_client:
            try:
                # Test basic connectivity
                doc_count = await self.search_client.get_document_count()
                print(f"✅ Connection successful - Index has {doc_count} documents")
                
                # Test search functionality
                test_results = await self.search_client.search("*", top=1)
                result_count = 0
                async for result in test_results:
                    result_count += 1
                    print(f"✅ Sample document fields: {list(result.keys())}")
                    break
                
                if result_count == 0:
                    print("⚠️  Index is empty - no documents found")
                    
            except Exception as e:
                print(f"❌ Search client error: {str(e)}")
                print(f"   Error type: {type(e).__name__}")
        else:
            print("❌ Search client not initialized")

    async def create_agent_async(self):
        """Create the template agent with all tools - must be called within async context."""
        self.initialized = True

        self.creds = DefaultAzureCredential()
        self.client = AzureAIAgent.create_client(credential=self.creds)

        await self._initialize_search_client()

        # Get MCP authentication headers
        headers = await self._get_mcp_auth_headers()

        # Create Bing tools
        bing = None
        try:
            bing_connection = await self.client.connections.get(name=self.bing_tool_name)
            conn_id = bing_connection.id
            print(f"🔍 Attempting Bing tool creation with connection name: {self.bing_tool_name}")
            bing = BingGroundingTool(connection_id=conn_id)
            print(f"🔍 Bing tool created with {conn_id} - {len(bing.definitions)} tools available")
        except Exception as name_error:
            print(f"⚠️  Bing tool creation with {self.bing_tool_name} failed: {name_error}")

        # Create MCP plugin and enter its async context
        try:
            print("🔗 Creating MCP plugin within async context...")
            self.mcp_plugin = MCPStreamableHttpPlugin(
                name=self.mcp_srv_name,
                description=self.mcp_srv_description,
                url=self.mcp_srv_endpoint,
                headers=headers,
            )

            # Enter the MCP plugin's async context
            if hasattr(self.mcp_plugin, '__aenter__'):
                await self.mcp_plugin.__aenter__()
                self._mcp_context_entered = True
                print("✅ MCP plugin async context entered")
            else:
                print("ℹ️  MCP plugin doesn't require async context")

        except Exception as mcp_error:
            print(f"⚠️  MCP plugin creation failed: {mcp_error}")
            self.mcp_plugin = None
            self._mcp_context_entered = False

        # Create agent settings and definition
        ai_agent_settings = AzureAIAgentSettings()
        template_agent_definition = await self.client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            # Name, description and instructions are provided for demonstration purposes
            name=self.AGENT_NAME,
            description=self.AGENT_DESCRIPTION,
            instructions= self.AGENT_INSTRUCTIONS,
            tools=bing.definitions if bing else [],
            # Add Code Interpreter tool for coding capabilities
            # tools=[CodeInterpreterToolDefinition()] if self.mcp_plugin else []
        )

        # Create the final agent
        plugins = [self.mcp_plugin] if self.mcp_plugin else []
        self._agent = AzureAIAgent(
            client=self.client,
            definition=template_agent_definition,
            plugins=plugins
        )

        print("✅ Template agent created successfully!")

    async def close(self):
        """Clean up async resources."""
        if not self.initialized:
            return

        print("🧹 Cleaning up agent resources...")
        if self.mcp_plugin and self._mcp_context_entered:
            try:
                # Exit MCP plugin context first
                if hasattr(self.mcp_plugin, '__aexit__'):
                    #await self.mcp_plugin.__aexit__(None, None, None)
                    self.mcp_plugin = None
                    print("✅ MCP plugin context cleaned up")
                # Getting the following error during cleanup: Attempted to exit a cancel scope that isn't the current tasks's current cancel scope
                # Seems to be related to https://github.com/microsoft/semantic-kernel/issues/12627?
            except Exception as e:
                print(f"⚠️ {self.AGENT_NAME}: Error cleaning up MCP plugin: {e}")
            finally:
                self._mcp_context_entered = False
                self.mcp_plugin = None
            try:
                # Then exit Azure contexts
                if self.client:
                    await self.client.__aexit__(None, None, None)
            except Exception as e:
                print(f"⚠️ {self.AGENT_NAME}: Error cleaning up client: {e}")
            try:
                if self.creds:
                    await self.creds.__aexit__(None, None, None)
            except Exception as e:
                print(f"⚠️ {self.AGENT_NAME}: Error cleaning up credentials: {e}")

            self.initialized = False
            print("✅ Agent cleanup completed")

    # Add __del__ for emergency cleanup
    def __del__(self):
        """Emergency cleanup when object is garbage collected."""
        if self.initialized:
            try:
                # Try to schedule cleanup in the event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except Exception:
                # If we can't schedule cleanup, just warn
                print(f"⚠️  Warning: {self.AGENT_NAME} was not properly cleaned up")

    async def _get_mcp_auth_headers(self) -> dict:
        """Get MCP authentication headers."""
        try:
            interactive_credential = InteractiveBrowserCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id
            )
            token = interactive_credential.get_token(f"api://{self.client_id}/access_as_user")
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json"
            }
            print("✅ Successfully obtained MCP authentication token")
            return headers
        except Exception as e:
            print(f"❌ Failed to get MCP token: {e}")
            return {}


# Factory function for your agent factory
# Add parameters to allow creation of agents with different capabilities
async def create_foundry_agent():
    """Factory function that returns a AzureAiAgentTemplate context manager."""
    return_agent = FoundryAgentTemplate()
    await return_agent.create_agent_async()
    return return_agent


# Test harness
async def test_agent():
    """Simple chat test harness for the agent."""
    print("🤖 Starting agent test harness...")

    try:
        async with FoundryAgentTemplate() as agent:
            print("💬 Type 'quit' or 'exit' to stop\n")

            while True:
                user_input = input("You: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                if not user_input:
                    continue

                try:
                    print("🤖 Agent: ", end="", flush=True)
                    async for message in agent.invoke(user_input):
                        if hasattr(message, 'content'):
                            print(message.content, end="", flush=True)
                        else:
                            print(str(message), end="", flush=True)
                    print()

                except Exception as e:
                    print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Failed to create agent: {e}")


if __name__ == "__main__":
    asyncio.run(test_agent())
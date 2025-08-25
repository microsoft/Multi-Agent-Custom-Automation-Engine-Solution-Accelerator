import logging
import os

from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent  # pylint: disable=E0611
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.azure_ai_search import AzureAISearchCollection
from v3.magentic_agents.common.lifecycle import MCPEnabledBase
from v3.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from v3.magentic_agents.reasoning_search import ReasoningSearch


class ReasoningAgentTemplate(MCPEnabledBase):
    """
    SK ChatCompletionAgent with optional MCP plugin injected as a Kernel plugin.
    No Azure AI Agents client is needed here. We only need a token provider for SK.
    """

    def __init__(self, agent_name: str, 
                 agent_description: str, 
                 agent_instructions: str,
                 model_deployment_name: str,
                 azure_openai_endpoint: str,
                 search_config: SearchConfig | None = None,
                 mcp_config: MCPConfig | None = None) -> None:
        super().__init__(mcp=mcp_config)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self._model_deployment_name = model_deployment_name
        self._openai_endpoint = azure_openai_endpoint
        self.search_config = search_config 
        self.reasoning_search: ReasoningSearch | None = None
        self.logger = logging.getLogger(__name__)

    async def _after_open(self) -> None:
        self.kernel = Kernel()

        # Token provider for SK chat completion
        sync_cred = SyncDefaultAzureCredential()

        def ad_token_provider() -> str:
            token = sync_cred.get_token("https://cognitiveservices.azure.com/.default")
            return token.token

        chat = AzureChatCompletion(
            deployment_name=self._model_deployment_name,
            endpoint=self._openai_endpoint,
            ad_token_provider=ad_token_provider
        )
        self.kernel.add_service(chat)

        # Initialize search capabilities
        if self.search_config:
            self.reasoning_search = ReasoningSearch(self.search_config)
            await self.reasoning_search.initialize(self.kernel)

        # Inject MCP plugin into the SK kernel if available
        if self.mcp_plugin:
            try:
                self.kernel.add_plugin(self.mcp_plugin, plugin_name="mcp_tools")
                self.logger.info("Added MCP plugin")
            except Exception as ex:
                self.logger.exception(f"Could not add MCP plugin to kernel: {ex}")

        self._agent = ChatCompletionAgent(
            kernel=self.kernel,
            name=self.agent_name,
            description=self.agent_description,
            instructions=self.agent_instructions
        )
    
    async def invoke(self, message: str):
        """Invoke the agent with a message."""
        if not self._agent:
            raise RuntimeError("Agent not initialized. Call open() first.")
        
        async for response in self._agent.invoke(message):
            yield response
        
# Backward‑compatible factory
async def create_reasoning_agent(
            agent_name: str, 
            agent_description: str, 
            agent_instructions: str,
            model_deployment_name: str,
            azure_openai_endpoint: str,
            search_config: SearchConfig | None = None,
            mcp_config: MCPConfig | None = None) -> ReasoningAgentTemplate:
    agent = ReasoningAgentTemplate(
        agent_name=agent_name, 
        agent_description=agent_description, 
        agent_instructions=agent_instructions,
        model_deployment_name=model_deployment_name,
        azure_openai_endpoint=azure_openai_endpoint,
        search_config= search_config,
        mcp_config=mcp_config
    )
    await agent.open()
    return agent

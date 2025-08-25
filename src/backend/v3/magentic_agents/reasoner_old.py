# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential
from azure.identity import InteractiveBrowserCredential
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel import Kernel
from semantic_kernel.agents import \
    ChatCompletionAgent  # pylint: disable=no-name-in-module
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from semantic_kernel.connectors.ai.function_choice_behavior import \
    FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin


class CustomAgentTemplate:
    """A template agent that manages its own async context for client connections."""
    
    # To do: pass capability parameters in the constructor:
    # 1. MCP server endpoint and use
    # 2. Bing grounding option
    # 3. Reasoning model name (some settings are different and cannot be used with bing grounding or MCP)
    # 4. Coding skills - CodeInterpreterToolDefinition
    # 5. Grounding Data - requires index endpoint
    # This will allow the factory to create all base models except researcher with bing - this is
    # is coming with a deep research offering soon (preview now in two regions)
    def __init__(self):
        self.agent = None
        self.client = None
        self.creds = None
        self.mcp_plugin = None
        self.mcp_srv_endpoint = os.environ["MCP_SERVER_ENDPOINT"] or ""
        self.mcp_srv_name= os.environ["MCP_SERVER_NAME"] or ""
        self.mcp_srv_description = os.environ["MCP_SERVER_DESCRIPTION"] or ""
        self.tenant_id = os.environ["TENANT_ID"] or ""
        self.client_id = os.environ["CLIENT_ID"] or ""
        self.reasoning_model_name = os.environ["REASONING_MODEL_NAME"] or ""
        self.open_ai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"] or ""

        custom_kernel = Kernel()

        # Create Azure credential for reasoning agent
        sync_credential = SyncDefaultAzureCredential()

        def get_azure_token():
            token = sync_credential.get_token("https://cognitiveservices.azure.com/.default")
            return token.token

        # Add Azure Chat Completion service (reasoning model)
        custom_chat_completion = AzureChatCompletion(
            deployment_name=self.reasoning_model_name,  # reasoning model
            endpoint=self.open_ai_endpoint,
            ad_token_provider=get_azure_token
        )
        custom_kernel.add_service(custom_chat_completion)

                # Configure function choice behavior
        function_choice_behavior = FunctionChoiceBehavior.Auto(auto_invoke=True, filters={"excluded_plugins": []})

        self._agent = CustomReasoningAgent(
            kernel=custom_kernel,
            # Name, description and instructions are provided for demonstration purposes
            name="ReasoningAgent",
            description="An intelligent reasoning assistant powered by reasoning model with MCP access. Excels at complex analysis, logical reasoning, and strategic thinking.",
            instructions="""You are a Reasoning Agent powered by a reasoning model with access to MCP tools.

                IDENTITY: You are a reasoning assistant focused on logical analysis and strategic thinking. Do not reference personal attributes, trivia abilities, or puzzle-solving comparisons to specific individuals or organizations.

                CAPABILITIES:
                - Advanced reasoning and analysis using o3 model
                - Complex problem solving and strategic thinking
                - MCP server functions (greetings, planning)
                - Pattern recognition and logical deduction
                - Multi-step reasoning processes
                
                WORKING WITH TEAM:
                - You work with Research and Coder agents
                - Research agents provide current information via web search
                - Coder agents provide computational analysis
                - Your role is to synthesize information and provide deep insights
                
                TASK EXECUTION:
                - Focus on the specific task or question asked
                - Provide clear, actionable reasoning
                - When asked to execute a step, perform that step directly
                - Do not include unrelated personal attributes or capabilities
                
                When you need current information, request specific searches from the Research agent.
                When you need computational analysis, request it from the Coder agent.
                Focus on reasoning, synthesis, and strategic insights for the specific task at hand.""",
            function_choice_behavior=function_choice_behavior)

    def __getattr__(self, name):
        """Delegate all attribute access to the wrapped agent."""
        return getattr(self._agent, name)
    
    async def __aenter__(self):
        """Initialize the agent and return it within an async context."""
        # Initialize credentials and client
        self.creds = DefaultAzureCredential()
        self.client = AzureAIAgent.create_client(credential=self.creds)
        
        # Enter the Azure contexts
        await self.creds.__aenter__()
        await self.client.__aenter__()
        
        # Create the agent (including MCP plugin within the context)
        await self._create_agent()
        
        return self._agent
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the async contexts."""
        # Exit MCP plugin context first
        self.close()

    async def close(self):
        """Clean up the async contexts."""
        # Exit MCP plugin context first
        if self.mcp_plugin and hasattr(self.mcp_plugin, '__aexit__'):
            #await self.mcp_plugin.__aexit__(exc_type, exc_val, exc_tb)
            self.mcp_plugin = None
        # Then exit Azure contexts
        if self.client:
            await self.client.__aexit__(None, None, None)
        if self.creds:
            await self.creds.__aexit__(None, None, None)
    
    async def _create_agent(self):
        """Create the template agent with all tools - must be called within async context."""
        
        # Get MCP authentication headers
        headers = await self._get_mcp_auth_headers()

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
                print("✅ MCP plugin async context entered")
            else:
                print("ℹ️  MCP plugin doesn't require async context")
                
        except Exception as mcp_error:
            print(f"⚠️  MCP plugin creation failed: {mcp_error}")
            self.mcp_plugin = None

        # Add MCP plugin to reasoning kernel if available
        if self.mcp_plugin:
            try:
                self._agent.kernel.add_plugin(self.mcp_plugin, plugin_name="mcp_tools")
                print("✅ Added MCP plugin to reasoning agent")
            except Exception as e:
                print(f"⚠️  Could not add MCP to reasoning agent: {e}")
        
        print("✅ Template agent created successfully!")
    
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



class CustomReasoningAgent(ChatCompletionAgent):
    """Custom Semantic Kernel agent with reasoning models"""
    
    def __init__(
        self, 
        kernel: Kernel, 
        name: str = "ReasoningAgent",
        description: str = "An intelligent reasoning assistant powered by a reasoning model",
        instructions: str ="You are a Reasoning Agent powered by a reasoning model with access to MCP tools.",
        function_choice_behavior = None
    ):
        # Get the chat completion service from the kernel
        chat_service = kernel.get_service(type=AzureChatCompletion)
        
        # Initialize the base ChatCompletionAgent class
        super().__init__(
            kernel=kernel,
            service=chat_service,
            name=name,
            description=description,
            instructions=instructions,
            function_choice_behavior=function_choice_behavior
        )

# Factory function for your agent factory
# Add parameters to allow creation of agents with different capabilities
async def create_custom_agent():
    """Factory function that returns a AzureAiAgentTemplate context manager."""
    return CustomAgentTemplate()

# Test harness
async def test_agent():
    """Simple chat test harness for the agent."""
    print("🤖 Starting agent test harness...")
    
    try:
        async with CustomAgentTemplate() as agent:
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

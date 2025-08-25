"""Simple test harness to test interactions with the Foundry Agent."""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend path to sys.path so we can import v3 modules
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from v3.magentic_agents.models.agent_models import MCPConfig, SearchConfig
from v3.magentic_agents.reasoning_agent import ReasoningAgentTemplate

mcp_config = MCPConfig().from_env()
search_config = SearchConfig().from_env()

AGENT_NAME="ReasoningAgent"
AGENT_DESCRIPTION="Reasoning agent with MCP access."
AGENT_INSTRUCTIONS=(
    "You are a Reasoning Agent with access to MCP tools and internal documents.\n"
    "When users ask questions, you can search the knowledge base using the knowledge_search-search_documents function.\n"
    "Use the search function when you need information that might be in internal documents.\n"
    "Focus on analysis and synthesis of the information you find.\n"
    "Always cite when you use information from the knowledge base.")
MODEL_DEPLOYMENT_NAME=os.getenv("REASONING_MODEL_NAME")
AZURE_OPENAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT")

# Test harness
async def test_agent():
    """Simple chat test harness for the agent."""
    print("🤖 Starting agent test harness...")
    
    try:
        async with ReasoningAgentTemplate(agent_name=AGENT_NAME,
                                          agent_description=AGENT_DESCRIPTION,
                                          agent_instructions=AGENT_INSTRUCTIONS,
                                          model_deployment_name=MODEL_DEPLOYMENT_NAME,
                                          azure_openai_endpoint=AZURE_OPENAI_ENDPOINT,
                                          search_config= search_config,
                                          mcp_config=mcp_config) as agent:
            
            # Add debugging info
            print(f"✅ Agent created: {agent.agent_name}")
            print(f"🔧 MCP Available: {hasattr(agent, 'mcp_plugin') and agent.mcp_plugin is not None}")
            print(f"🔍 Search Available: {hasattr(agent, 'reasoning_search') and agent.reasoning_search and agent.reasoning_search.is_available()}")

            # Check what plugins are available to the agent
            if hasattr(agent, 'kernel') and agent.kernel:
                plugins = agent.kernel.plugins
                #print(f"🔌 Available plugins: {list(plugins.keys()) if plugins else 'None'}")
                if 'knowledge_search' in plugins:
                    # Fix: Get functions from the KernelPlugin object properly
                    knowledge_plugin = plugins['knowledge_search']
                    functions = list(knowledge_plugin.functions.keys()) if hasattr(knowledge_plugin, 'functions') else []
                    print(f"📚 Knowledge search functions: {functions}")
            
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

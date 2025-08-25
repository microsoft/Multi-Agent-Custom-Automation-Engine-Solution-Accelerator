"""Simple test harness to test interactions with the Foundry Agent."""

import asyncio
import sys
from pathlib import Path

# Add the backend path to sys.path so we can import v3 modules
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from v3.magentic_agents.foundry_agent import FoundryAgentTemplate
from v3.magentic_agents.models.agent_models import (BingConfig, MCPConfig,
                                                    SearchConfig)

# Manual Test harness
AGENT_NAME = "TestFoundryAgent"
AGENT_DESCRIPTION = "A comprehensive research assistant with web search, Azure AI Search RAG, and MCP capabilities."
AGENT_INSTRUCTIONS = (
    "You are an Enhanced Research Agent with multiple information sources:\n"
    "1. Azure AI Search for retail store and customer interaction data. Some of these are in json format, others in .csv\n"
    "2. Bing search for current web information and recent events\n"
    "3. MCP tools for specialized data access\n\n"
    "Search Strategy:\n"
    "- Use Azure AI Search first for internal/proprietary information\n"
    "- Use Bing search for current events, recent news, and public information\n"
    "- Always cite your sources and specify which search method provided the information\n"
    "- Provide comprehensive answers combining multiple sources when relevant\n"
    "- Ask for clarification only if the task is genuinely ambiguous"
)
MODEL_DEPLOYMENT_NAME = "gpt-4.1"
async def test_agent():
    """Simple chat test harness for the agent."""
    print("🤖 Starting agent test harness...")

    try:
        # If environment variables are missing, catch exception and abort
        try:
            mcp_init = MCPConfig().from_env()
            bing_init = BingConfig().from_env()
            search_init = SearchConfig().from_env()
        except ValueError as ve:
            print(f"❌ Configuration error: {ve}")
            return
        async with FoundryAgentTemplate(agent_name=AGENT_NAME,
                                        agent_description=AGENT_DESCRIPTION, 
                                        agent_instructions=AGENT_INSTRUCTIONS, 
                                        model_deployment_name=MODEL_DEPLOYMENT_NAME,
                                        enable_code_interpreter=True,
                                        mcp_config=mcp_init,
                                        bing_config=bing_init,
                                        search_config=search_init) as agent:
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
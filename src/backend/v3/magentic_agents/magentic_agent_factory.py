# Copyright (c) Microsoft. All rights reserved.

from v3.magentic_agents.coder import create_foundry_agent as create_coder
from v3.magentic_agents.proxy_agent import create_proxy_agent
from v3.magentic_agents.researcher import \
    create_foundry_agent as create_researcher

from src.backend.v3.magentic_agents.reasoner_old import \
    create_custom_agent as create_reasoner

_agent_list = []

async def get_agents() -> list:
    """Return the agents used in the Magentic orchestration."""
    researcher = await create_researcher()
    print("Created Enhanced Research Agent (Bing + MCP)")

    coder = await create_coder()
    print("Created Coder Agent (Azure AI + MCP)")

    reasoner = await create_reasoner()
    print("Created Custom Reasoning Agent (SK + MCP)")

    proxy = await create_proxy_agent()
    print("Created Human Proxy Agent (Human-in-loop)")

    global _agent_list
    _agent_list = [researcher, coder, reasoner, proxy]
    return _agent_list

async def cleanup_all_agents():
    """Clean up all created agents."""
    global _agent_list
    for agent in _agent_list:
        try:
            await agent.close()
        except Exception as ex:
            name = getattr(agent, "AGENT_NAME", getattr(agent, "__class__", type("X",(object,),{})).__name__)
            print(f"Error closing agent {name}: {ex}")
    _agent_list.clear()
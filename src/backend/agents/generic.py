from typing import List

from autogen_core.base import AgentId
from autogen_core.components import default_subscription
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, Tool

from agents.base_agent import BaseAgent
from context.cosmos_memory import CosmosBufferedChatCompletionContext


async def dummy_function() -> str:
    # This is a placeholder function, for a proper Azure AI Search RAG process.

    """This is a placeholder"""
    return "This is a placeholder function"


# Create the ProductTools list
def get_generic_tools() -> List[Tool]:
    GenericTools: List[Tool] = [
        FunctionTool(
            dummy_function,
            description="This is a placeholder",
            name="dummy_function",
        ),
    ]
    return GenericTools


@default_subscription
class GenericAgent(BaseAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        generic_tools: List[Tool],
        generic_tool_agent_id: AgentId,
    ) -> None:
        super().__init__(
            "ProductAgent",
            model_client,
            session_id,
            user_id,
            memory,
            generic_tools,
            generic_tool_agent_id,
            "You are a generic agent. You are used to handle generic tasks that a general Large Language Model can assist with. You are being called as a fallback, when no other agents are able to use their specialised functions in order to solve the user's task. Summarize back the user what was done. Do not use any function calling- just use your native LLM response.",
        )

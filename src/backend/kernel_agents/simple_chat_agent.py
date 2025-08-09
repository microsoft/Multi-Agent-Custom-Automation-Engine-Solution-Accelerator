from kernel_agents.generic_agent import GenericAgent
from models.messages_kernel import AgentType


class SimpleChatAgent(GenericAgent):
    """Agent for basic conversational interactions."""

    @staticmethod
    def default_system_message(agent_name: str = AgentType.SIMPLE_CHAT.value) -> str:
        """Get the default system message for the SimpleChatAgent."""
        return "You are a Simple Chat agent that engages in basic conversation and provides helpful responses."

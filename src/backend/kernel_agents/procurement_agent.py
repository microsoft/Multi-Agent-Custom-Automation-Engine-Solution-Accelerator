import logging
from typing import Dict, List, Optional

from kernel_agents.agent_base import BaseAgent
from kernel_tools.procurement_tools import ProcurementTools
from common.models.messages_kernel import AgentType
from semantic_kernel.functions import KernelFunction
from common.database.database_base import DatabaseBase


class ProcurementAgent(BaseAgent):
    """Procurement agent implementation using Semantic Kernel.

    This agent specializes in procurement, purchasing, vendor management, and inventory tasks.
    """

    def __init__(
        self,
        session_id: str,
        user_id: str,
        memory_store: Optional[DatabaseBase] = None,
        tools: Optional[List[KernelFunction]] = None,
        system_message: Optional[str] = None,
        agent_name: str = AgentType.PROCUREMENT.value,
        client=None,
        definition=None,
    ) -> None:
        """Initialize the Procurement Agent.

        Args:
            kernel: The semantic kernel instance
            session_id: The current session identifier
            user_id: The user identifier
            memory_store: The Cosmos memory context
            tools: List of tools available to this agent (optional)
            system_message: Optional system message for the agent
            agent_name: Optional name for the agent (defaults to "ProcurementAgent")
            client: Optional client instance
            definition: Optional definition instance
        """
        # Load configuration if tools not provided
        if not tools:
            # Get tools directly from ProcurementTools class
            tools_dict = ProcurementTools.get_all_kernel_functions()
            tools = [KernelFunction.from_method(func) for func in tools_dict.values()]

            # Use system message from config if not explicitly provided
        if not system_message:
            system_message = self.default_system_message(agent_name)

        # Use agent name from config if available
        agent_name = AgentType.PROCUREMENT.value

        super().__init__(
            agent_name=agent_name,
            session_id=session_id,
            user_id=user_id,
            memory_store=memory_store,
            tools=tools,
            system_message=system_message,
            client=client,
            definition=definition,
        )

    @classmethod
    async def create(
        cls,
        **kwargs: Dict[str, str],
    ) -> None:
        """Asynchronously create the PlannerAgent.

        Creates the Azure AI Agent for planning operations.

        Returns:
            None
        """

        session_id = kwargs.get("session_id")
        user_id = kwargs.get("user_id")
        memory_store = kwargs.get("memory_store")
        tools = kwargs.get("tools", None)
        system_message = kwargs.get("system_message", None)
        agent_name = kwargs.get("agent_name")
        client = kwargs.get("client")

        try:
            logging.info("Initializing ProcurementAgent from async init azure AI Agent")

            # Create the Azure AI Agent using AppConfig with string instructions
            agent_definition = await cls._create_azure_ai_agent_definition(
                agent_name=agent_name,
                instructions=system_message,  # Pass the formatted string, not an object
                temperature=0.0,
                response_format=None,
            )

            return cls(
                session_id=session_id,
                user_id=user_id,
                memory_store=memory_store,
                tools=tools,
                system_message=system_message,
                agent_name=agent_name,
                client=client,
                definition=agent_definition,
            )

        except Exception as e:
            logging.error(f"Failed to create Azure AI Agent for PlannerAgent: {e}")
            raise

    @staticmethod
    def default_system_message(agent_name=None) -> str:
        """Get the default system message for the agent.
        Args:
            agent_name: The name of the agent (optional)
        Returns:
            The default system message for the agent
        """
        return "You are a Procurement agent. You specialize in purchasing, vendor management, supply chain operations, and inventory control. You help with creating purchase orders, managing vendors, tracking orders, and ensuring efficient procurement processes."

    @property
    def plugins(self):
        """Get the plugins for the procurement agent."""
        return ProcurementTools.get_all_kernel_functions()

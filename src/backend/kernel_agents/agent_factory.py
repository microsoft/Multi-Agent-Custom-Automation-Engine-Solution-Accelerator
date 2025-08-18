"""Factory for creating agents in the Multi-Agent Custom Automation Engine."""

import inspect
import logging
from typing import Any, Dict, Optional, Type

# Import the new AppConfig instance
from common.config.app_config import config
from azure.ai.agents.models import (
    ResponseFormatJsonSchema,
    ResponseFormatJsonSchemaType,
)
from kernel_agents.agent_base import BaseAgent
from kernel_agents.generic_agent import GenericAgent
from kernel_agents.group_chat_manager import GroupChatManager

# Import all specialized agent implementations
from kernel_agents.hr_agent import HrAgent
from kernel_agents.human_agent import HumanAgent
from kernel_agents.marketing_agent import MarketingAgent
from kernel_agents.planner_agent import PlannerAgent  # Add PlannerAgent import
from kernel_agents.procurement_agent import ProcurementAgent
from kernel_agents.product_agent import ProductAgent
from kernel_agents.tech_support_agent import TechSupportAgent
from common.models.messages_kernel import AgentType, PlannerResponsePlan

# pylint:disable=E0611
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent

from common.database.database_base import DatabaseBase
from common.database.database_factory import DatabaseFactory

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating agents in the Multi-Agent Custom Automation Engine."""

    # Mapping of agent types to their implementation classes
    _agent_classes: Dict[AgentType, Type[BaseAgent]] = {
        AgentType.HR: HrAgent,
        AgentType.MARKETING: MarketingAgent,
        AgentType.PRODUCT: ProductAgent,
        AgentType.PROCUREMENT: ProcurementAgent,
        AgentType.TECH_SUPPORT: TechSupportAgent,
        AgentType.GENERIC: GenericAgent,
        AgentType.HUMAN: HumanAgent,
        AgentType.PLANNER: PlannerAgent,
        AgentType.GROUP_CHAT_MANAGER: GroupChatManager,  # Add GroupChatManager
    }

    # Mapping of agent types to their string identifiers (for automatic tool loading)
    _agent_type_strings: Dict[AgentType, str] = {
        AgentType.HR: AgentType.HR.value,
        AgentType.MARKETING: AgentType.MARKETING.value,
        AgentType.PRODUCT: AgentType.PRODUCT.value,
        AgentType.PROCUREMENT: AgentType.PROCUREMENT.value,
        AgentType.TECH_SUPPORT: AgentType.TECH_SUPPORT.value,
        AgentType.GENERIC: AgentType.GENERIC.value,
        AgentType.HUMAN: AgentType.HUMAN.value,
        AgentType.PLANNER: AgentType.PLANNER.value,
        AgentType.GROUP_CHAT_MANAGER: AgentType.GROUP_CHAT_MANAGER.value,
    }

    # System messages for each agent type
    _agent_system_messages: Dict[AgentType, str] = {
        AgentType.HR: HrAgent.default_system_message(),
        AgentType.MARKETING: MarketingAgent.default_system_message(),
        AgentType.PRODUCT: ProductAgent.default_system_message(),
        AgentType.PROCUREMENT: ProcurementAgent.default_system_message(),
        AgentType.TECH_SUPPORT: TechSupportAgent.default_system_message(),
        AgentType.GENERIC: GenericAgent.default_system_message(),
        AgentType.HUMAN: HumanAgent.default_system_message(),
        AgentType.PLANNER: PlannerAgent.default_system_message(),
        AgentType.GROUP_CHAT_MANAGER: GroupChatManager.default_system_message(),
    }

    # Cache of agent instances by session_id and agent_type
    _agent_cache: Dict[str, Dict[AgentType, BaseAgent]] = {}

    # Cache of Azure AI Agent instances
    _azure_ai_agent_cache: Dict[str, Dict[str, AzureAIAgent]] = {}

    @classmethod
    async def create_agent(
        cls,
        agent_type: AgentType,
        session_id: str,
        user_id: str,
        temperature: float = 0.0,
        memory_store: Optional[DatabaseBase] = None,
        system_message: Optional[str] = None,
        response_format: Optional[Any] = None,
        client: Optional[Any] = None,
        **kwargs,
    ) -> BaseAgent:
        """Create an agent of the specified type.

        This method creates and initializes an agent instance of the specified type. If an agent
        of the same type already exists for the session, it returns the cached instance. The method
        handles the complete initialization process including:
        1. Creating a memory store for the agent
        2. Setting up the Semantic Kernel
        3. Loading appropriate tools from JSON configuration files
        4. Creating an Azure AI agent definition using the AI Project client
        5. Initializing the agent with all required parameters
        6. Running any asynchronous initialization if needed
        7. Caching the agent for future use

        Args:
            agent_type: The type of agent to create (from AgentType enum)
            session_id: The unique identifier for the current session
            user_id: The user identifier for the current user
            temperature: The temperature parameter for the agent's responses (0.0-1.0)
            system_message: Optional custom system message to override default
            response_format: Optional response format configuration for structured outputs
            **kwargs: Additional parameters to pass to the agent constructor

        Returns:
            An initialized instance of the specified agent type

        Raises:
            ValueError: If the agent type is unknown or initialization fails
        """
        # Check if we already have an agent in the cache
        if (
            session_id in cls._agent_cache
            and agent_type in cls._agent_cache[session_id]
        ):
            logger.info(
                f"Returning cached agent instance for session {session_id} and agent type {agent_type}"
            )
            return cls._agent_cache[session_id][agent_type]

        # Get the agent class
        agent_class = cls._agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Create memory store
        if memory_store is None:
            memory_store = await DatabaseFactory.get_database(user_id=user_id)

        # Use default system message if none provided
        if system_message is None:
            system_message = cls._agent_system_messages.get(
                agent_type,
                f"You are a helpful AI assistant specialized in {cls._agent_type_strings.get(agent_type, 'general')} tasks.",
            )

        # For other agent types, use the standard tool loading mechanism
        agent_type_str = cls._agent_type_strings.get(
            agent_type, agent_type.value.lower()
        )
        tools = None

        # Create the agent instance using the project-based pattern
        try:
            # Filter kwargs to only those accepted by the agent's __init__
            agent_init_params = inspect.signature(agent_class.__init__).parameters
            valid_keys = set(agent_init_params.keys()) - {"self"}
            filtered_kwargs = {
                k: v
                for k, v in {
                    "agent_name": agent_type_str,
                    "session_id": session_id,
                    "user_id": user_id,
                    "memory_store": memory_store,
                    "tools": tools,
                    "system_message": system_message,
                    "client": client,
                    **kwargs,
                }.items()
                if k in valid_keys
            }
            agent = await agent_class.create(**filtered_kwargs)

        except Exception as e:
            logger.error(
                f"Error creating agent of type {agent_type} with parameters: {e}"
            )
            raise

        # Cache the agent instance
        if session_id not in cls._agent_cache:
            cls._agent_cache[session_id] = {}
        cls._agent_cache[session_id][agent_type] = agent

        return agent

    @classmethod
    async def create_all_agents(
        cls,
        session_id: str,
        user_id: str,
        temperature: float = 0.0,
        memory_store: Optional[DatabaseBase] = None,
        client: Optional[Any] = None,
    ) -> Dict[AgentType, BaseAgent]:
        """Create all agent types for a session in a specific order.

        This method creates all agent instances for a session in a multi-phase approach:
        1. First, it creates all basic agent types except for the Planner and GroupChatManager
        2. Then it creates the Planner agent, providing it with references to all other agents
        3. Finally, it creates the GroupChatManager with references to all agents including the Planner

        This ordered creation ensures that dependencies between agents are properly established,
        particularly for the Planner and GroupChatManager which need to coordinate other agents.

        Args:
            session_id: The unique identifier for the current session
            user_id: The user identifier for the current user
            temperature: The temperature parameter for agent responses (0.0-1.0)

        Returns:
            Dictionary mapping agent types (from AgentType enum) to initialized agent instances
        """

        # Create each agent type in two phases
        # First, create all agents except PlannerAgent and GroupChatManager
        agents = {}
        planner_agent_type = AgentType.PLANNER
        group_chat_manager_type = AgentType.GROUP_CHAT_MANAGER

        try:
            if client is None:
                # Create the AIProjectClient instance using the config
                # This is a placeholder; replace with actual client creation logic
                client = config.get_ai_project_client()
        except Exception as client_exc:
            logger.error(f"Error creating AIProjectClient: {client_exc}")
        # Initialize cache for this session if it doesn't exist
        if session_id not in cls._agent_cache:
            cls._agent_cache[session_id] = {}

        # Phase 1: Create all agents except planner and group chat manager
        for agent_type in [
            at
            for at in cls._agent_classes.keys()
            if at != planner_agent_type and at != group_chat_manager_type
        ]:
            agents[agent_type] = await cls.create_agent(
                agent_type=agent_type,
                session_id=session_id,
                user_id=user_id,
                temperature=temperature,
                client=client,
                memory_store=memory_store,
            )

        # Create agent name to instance mapping for the planner
        agent_instances = {}
        for agent_type, agent in agents.items():
            agent_name = agent_type.value

            logging.info(
                f"Creating agent instance for {agent_name} with type {agent_type}"
            )
            agent_instances[agent_name] = agent

        # Log the agent instances for debugging
        logger.info(
            f"Created {len(agent_instances)} agent instances for planner: {', '.join(agent_instances.keys())}"
        )

        # Phase 2: Create the planner agent with agent_instances
        planner_agent = await cls.create_agent(
            agent_type=AgentType.PLANNER,
            session_id=session_id,
            user_id=user_id,
            temperature=temperature,
            agent_instances=agent_instances,  # Pass agent instances to the planner
            client=client,
            response_format=ResponseFormatJsonSchemaType(
                json_schema=ResponseFormatJsonSchema(
                    name=PlannerResponsePlan.__name__,
                    description=f"respond with {PlannerResponsePlan.__name__.lower()}",
                    schema=PlannerResponsePlan.model_json_schema(),
                )
            ),
        )
        agent_instances[AgentType.PLANNER.value] = (
            planner_agent  # to pass it to group chat manager
        )
        agents[planner_agent_type] = planner_agent

        # Phase 3: Create group chat manager with all agents including the planner
        group_chat_manager = await cls.create_agent(
            agent_type=AgentType.GROUP_CHAT_MANAGER,
            session_id=session_id,
            user_id=user_id,
            temperature=temperature,
            client=client,
            agent_instances=agent_instances,  # Pass agent instances to the planner
        )
        agents[group_chat_manager_type] = group_chat_manager

        return agents

    @classmethod
    def get_agent_class(cls, agent_type: AgentType) -> Type[BaseAgent]:
        """Get the agent class for the specified type.

        Args:
            agent_type: The agent type

        Returns:
            The agent class

        Raises:
            ValueError: If the agent type is unknown
        """
        agent_class = cls._agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return agent_class

    @classmethod
    def clear_cache(cls, session_id: Optional[str] = None) -> None:
        """Clear the agent cache.

        Args:
            session_id: If provided, clear only this session's cache
        """
        if session_id:
            if session_id in cls._agent_cache:
                del cls._agent_cache[session_id]
                logger.info(f"Cleared agent cache for session {session_id}")
            if session_id in cls._azure_ai_agent_cache:
                del cls._azure_ai_agent_cache[session_id]
                logger.info(f"Cleared Azure AI agent cache for session {session_id}")
        else:
            cls._agent_cache.clear()
            cls._azure_ai_agent_cache.clear()
            logger.info("Cleared all agent caches")

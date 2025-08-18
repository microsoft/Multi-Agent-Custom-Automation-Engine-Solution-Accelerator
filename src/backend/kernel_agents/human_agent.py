import logging
from typing import Dict, List, Optional

from common.utils.event_utils import track_event_if_configured
from kernel_agents.agent_base import BaseAgent
from common.models.messages_kernel import (
    AgentMessage,
    AgentType,
    ApprovalRequest,
    HumanClarification,
    HumanFeedback,
    StepStatus,
)
from semantic_kernel.functions import KernelFunction

from common.database.database_base import DatabaseBase


class HumanAgent(BaseAgent):
    """Human agent implementation using Semantic Kernel.

    This agent specializes in representing and assisting humans in the multi-agent system.
    """

    def __init__(
        self,
        session_id: str,
        user_id: str,
        memory_store: Optional[DatabaseBase] = None,
        tools: Optional[List[KernelFunction]] = None,
        system_message: Optional[str] = None,
        agent_name: str = AgentType.HUMAN.value,
        client=None,
        definition=None,
    ) -> None:
        """Initialize the Human Agent.

        Args:
            session_id: The current session identifier
            user_id: The user identifier
            memory_store: The Cosmos memory context
            tools: List of tools available to this agent (optional)
            system_message: Optional system message for the agent
            agent_name: Optional name for the agent (defaults to "HumanAgent")
            config_path: Optional path to the Human tools configuration file
            client: Optional client instance
            definition: Optional definition instance
        """

        # Use system message from config if not explicitly provided
        if not system_message:
            system_message = self.default_system_message(agent_name)

            # Use agent name from config if available
            agent_name = AgentType.HUMAN.value

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
            logging.info("Initializing HumanAgent from async init azure AI Agent")

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
        return "You are representing a human user in the conversation. You handle interactions that require human feedback or input, such as providing clarification, approving plans, or giving feedback on steps."

    async def handle_human_feedback(self, human_feedback: HumanFeedback) -> str:
        """Handle human feedback on a step.

        This method processes feedback provided by a human user on a specific step in a plan.
        It updates the step with the feedback, marks the step as completed, and notifies the
        GroupChatManager by creating an ApprovalRequest in the memory store.

        Args:
            human_feedback: The HumanFeedback object containing feedback details
                           including step_id, session_id, and human_feedback text

        Returns:
            Status message indicating success or failure of processing the feedback
        """

        # Get the step
        step = await self._memory_store.get_step(
            human_feedback.step_id, human_feedback.session_id
        )
        if not step:
            return f"Step {human_feedback.step_id} not found"

        # Update the step with the feedback
        step.human_feedback = human_feedback.human_feedback
        step.status = StepStatus.completed

        # Save the updated step
        await self._memory_store.update_step(step)
        await self._memory_store.add_item(
            AgentMessage(
                session_id=human_feedback.session_id,
                user_id=step.user_id,
                plan_id=step.plan_id,
                content=f"Received feedback for step: {step.action}",
                source=AgentType.HUMAN.value,
                step_id=human_feedback.step_id,
            )
        )

        # Track the event
        track_event_if_configured(
            "Human Agent - Received feedback for step and added into the cosmos",
            {
                "session_id": human_feedback.session_id,
                "user_id": self._user_id,
                "plan_id": step.plan_id,
                "content": f"Received feedback for step: {step.action}",
                "source": AgentType.HUMAN.value,
                "step_id": human_feedback.step_id,
            },
        )

        # Notify the GroupChatManager that the step has been completed
        await self._memory_store.add_item(
            ApprovalRequest(
                session_id=human_feedback.session_id,
                user_id=self._user_id,
                plan_id=step.plan_id,
                step_id=human_feedback.step_id,
                agent_id=AgentType.GROUP_CHAT_MANAGER.value,
            )
        )

        # Track the approval request event
        track_event_if_configured(
            "Human Agent - Approval request sent for step and added into the cosmos",
            {
                "session_id": human_feedback.session_id,
                "user_id": self._user_id,
                "plan_id": step.plan_id,
                "step_id": human_feedback.step_id,
                "agent_id": "GroupChatManager",
            },
        )

        return "Human feedback processed successfully"

    async def handle_human_clarification(
        self, human_clarification: HumanClarification
    ) -> str:
        """Provide clarification on a plan.

        This method stores human clarification information for a plan associated with a session.
        It retrieves the plan from memory, updates it with the clarification text, and records
        the event in telemetry.

        Args:
            human_clarification: The HumanClarification object containing the session_id
                                and human_clarification provided by the human user

        Returns:
            Status message indicating success or failure of adding the clarification
        """
        session_id = human_clarification.session_id
        clarification_text = human_clarification.human_clarification

        # Get the plan associated with this session
        plan = await self._memory_store.get_plan_by_session(session_id)
        if not plan:
            return f"No plan found for session {session_id}"

        # Update the plan with the clarification
        plan.human_clarification_response = clarification_text
        await self._memory_store.update_plan(plan)
        await self._memory_store.add_item(
            AgentMessage(
                session_id=session_id,
                user_id=self._user_id,
                plan_id="",
                content=f"{clarification_text}",
                source=AgentType.HUMAN.value,
                step_id="",
            )
        )
        # Track the event
        track_event_if_configured(
            "Human Agent - Provided clarification for plan",
            {
                "session_id": session_id,
                "user_id": self._user_id,
                "plan_id": plan.id,
                "clarification": clarification_text,
                "source": AgentType.HUMAN.value,
            },
        )
        await self._memory_store.add_item(
            AgentMessage(
                session_id=session_id,
                user_id=self._user_id,
                plan_id="",
                content="Thanks. The plan has been updated.",
                source=AgentType.PLANNER.value,
                step_id="",
            )
        )
        track_event_if_configured(
            "Planner - Updated with HumanClarification and added into the cosmos",
            {
                "session_id": session_id,
                "user_id": self._user_id,
                "content": "Thanks. The plan has been updated.",
                "source": AgentType.PLANNER.value,
            },
        )
        return f"Clarification provided for plan {plan.id}"

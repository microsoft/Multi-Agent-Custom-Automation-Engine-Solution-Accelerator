import logging
from datetime import datetime
from typing import Dict, List, Optional

from common.utils.event_utils import track_event_if_configured
from kernel_agents.agent_base import BaseAgent
from common.utils.utils_date import format_date_for_user
from common.models.messages_kernel import (
    ActionRequest,
    AgentMessage,
    AgentType,
    HumanFeedback,
    HumanFeedbackStatus,
    InputTask,
    Plan,
    Step,
    StepStatus,
)

# pylint: disable=E0611
from semantic_kernel.functions.kernel_function import KernelFunction

from common.database.database_base import DatabaseBase


class GroupChatManager(BaseAgent):
    """GroupChatManager agent implementation using Semantic Kernel.

    This agent creates and manages plans based on user tasks, breaking them down into steps
    that can be executed by specialized agents to achieve the user's goal.
    """

    def __init__(
        self,
        session_id: str,
        user_id: str,
        memory_store: Optional[DatabaseBase] = None,
        tools: Optional[List[KernelFunction]] = None,
        system_message: Optional[str] = None,
        agent_name: str = AgentType.GROUP_CHAT_MANAGER.value,
        agent_tools_list: List[str] = None,
        agent_instances: Optional[Dict[str, BaseAgent]] = None,
        client=None,
        definition=None,
    ) -> None:
        """Initialize the GroupChatManager Agent.

        Args:
            session_id: The current session identifier
            user_id: The user identifier
            memory_store: The Cosmos memory context
            system_message: Optional system message for the agent
            agent_name: Optional name for the agent (defaults to "GroupChatManagerAgent")
            config_path: Optional path to the configuration file
            available_agents: List of available agent names for creating steps
            agent_tools_list: List of available tools across all agents
            agent_instances: Dictionary of agent instances available to the GroupChatManager
            client: Optional client instance (passed to BaseAgent)
            definition: Optional definition instance (passed to BaseAgent)
        """
        # Default system message if not provided
        if not system_message:
            system_message = self.default_system_message(agent_name)

        # Initialize the base agent
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

        # Store additional GroupChatManager-specific attributes
        self._available_agents = [
            AgentType.HUMAN.value,
            AgentType.HR.value,
            AgentType.MARKETING.value,
            AgentType.PRODUCT.value,
            AgentType.PROCUREMENT.value,
            AgentType.TECH_SUPPORT.value,
            AgentType.GENERIC.value,
        ]
        self._agent_tools_list = agent_tools_list or []
        self._agent_instances = agent_instances or {}

        # Create the Azure AI Agent for group chat operations
        # This will be initialized in async_init
        self._azure_ai_agent = None

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
        agent_tools_list = kwargs.get("agent_tools_list", None)
        agent_instances = kwargs.get("agent_instances", None)
        client = kwargs.get("client")

        try:
            logging.info("Initializing GroupChatAgent from async init azure AI Agent")

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
                agent_tools_list=agent_tools_list,
                agent_instances=agent_instances,
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
        return "You are a GroupChatManager agent responsible for creating and managing plans. You analyze tasks, break them down into steps, and assign them to the appropriate specialized agents."

    async def handle_input_task(self, message: InputTask) -> Plan:
        """
        Handles the input task from the user. This is the initial message that starts the conversation.
        This method should create a new plan.
        """
        logging.info(f"Received input task: {message}")
        await self._memory_store.add_item(
            AgentMessage(
                session_id=message.session_id,
                user_id=self._user_id,
                plan_id="",
                content=f"{message.description}",
                source=AgentType.HUMAN.value,
                step_id="",
            )
        )

        track_event_if_configured(
            "Group Chat Manager - Received and added input task into the cosmos",
            {
                "session_id": message.session_id,
                "user_id": self._user_id,
                "content": message.description,
                "source": AgentType.HUMAN.value,
            },
        )

        # Send the InputTask to the PlannerAgent
        planner_agent = self._agent_instances[AgentType.PLANNER.value]
        result = await planner_agent.handle_input_task(message)
        logging.info(f"Plan created: {result}")
        return result

    async def handle_human_feedback(self, message: HumanFeedback) -> None:
        """
        Handles the human approval feedback for a single step or all steps.
        Updates the step status and stores the feedback in the session context.

        class HumanFeedback(BaseModel):
            step_id: str
            plan_id: str
            session_id: str
            approved: bool
            human_feedback: Optional[str] = None
            updated_action: Optional[str] = None

        class Step(BaseDataModel):

            data_type: Literal["step"] = Field("step", Literal=True)
            plan_id: str
            action: str
            agent: BAgentType
            status: StepStatus = StepStatus.planned
            agent_reply: Optional[str] = None
            human_feedback: Optional[str] = None
            human_approval_status: Optional[HumanFeedbackStatus] = HumanFeedbackStatus.requested
            updated_action: Optional[str] = None
            session_id: (
                str  # Added session_id to the Step model to partition the steps by session_id
            )
            ts: Optional[int] = None
        """
        # Need to retrieve all the steps for the plan
        logging.info(f"GroupChatManager Received human feedback: {message}")

        steps: List[Step] = await self._memory_store.get_steps_by_plan(message.plan_id)
        # Filter for steps that are planned or awaiting feedback

        # Get the first step assigned to HumanAgent for feedback
        human_feedback_step: Step = next(
            (s for s in steps if s.agent == AgentType.HUMAN), None
        )

        # Determine the feedback to use
        if human_feedback_step and human_feedback_step.human_feedback:
            # Use the provided human feedback if available
            received_human_feedback_on_step = human_feedback_step.human_feedback
        else:
            received_human_feedback_on_step = ""

        # Provide generic context to the model
        current_date = datetime.now().strftime("%Y-%m-%d")
        formatted_date = format_date_for_user(current_date)
        general_information = f"Today's date is {formatted_date}."

        # Get the general background information provided by the user in regards to the overall plan (not the steps) to add as context.
        plan = await self._memory_store.get_plan_by_session(
            session_id=message.session_id
        )
        if plan.human_clarification_response:
            received_human_feedback_on_plan = (
                f"{plan.human_clarification_request}: {plan.human_clarification_response}"
                + " This information may or may not be relevant to the step you are executing - it was feedback provided by the human user on the overall plan, which includes multiple steps, not just the one you are actioning now."
            )
        else:
            received_human_feedback_on_plan = (
                "No human feedback provided on the overall plan."
            )
        # Combine all feedback into a single string
        received_human_feedback = (
            f"{received_human_feedback_on_step} "
            f"{general_information} "
            f"{received_human_feedback_on_plan}"
        )

        # Update and execute the specific step if step_id is provided
        if message.step_id:
            step = next((s for s in steps if s.id == message.step_id), None)
            if step:
                await self._update_step_status(
                    step, message.approved, received_human_feedback
                )
                if message.approved:
                    await self._execute_step(message.session_id, step)
                else:
                    # Notify the GroupChatManager that the step has been rejected
                    # TODO: Implement this logic later
                    step.status = StepStatus.rejected
                    step.human_approval_status = HumanFeedbackStatus.rejected
                    self._memory_store.update_step(step)
                    track_event_if_configured(
                        "Group Chat Manager - Steps has been rejected and updated into the cosmos",
                        {
                            "status": StepStatus.rejected,
                            "session_id": message.session_id,
                            "user_id": self._user_id,
                            "human_approval_status": HumanFeedbackStatus.rejected,
                            "source": step.agent,
                        },
                    )
        else:
            # Update and execute all steps if no specific step_id is provided
            for step in steps:
                await self._update_step_status(
                    step, message.approved, received_human_feedback
                )
                if message.approved:
                    await self._execute_step(message.session_id, step)
                else:
                    # Notify the GroupChatManager that the step has been rejected
                    # TODO: Implement this logic later
                    step.status = StepStatus.rejected
                    step.human_approval_status = HumanFeedbackStatus.rejected
                    self._memory_store.update_step(step)
                    track_event_if_configured(
                        f"{AgentType.GROUP_CHAT_MANAGER.value} - Step has been rejected and updated into the cosmos",
                        {
                            "status": StepStatus.rejected,
                            "session_id": message.session_id,
                            "user_id": self._user_id,
                            "human_approval_status": HumanFeedbackStatus.rejected,
                            "source": step.agent,
                        },
                    )

    # Function to update step status and add feedback
    async def _update_step_status(
        self, step: Step, approved: bool, received_human_feedback: str
    ):
        if approved:
            step.status = StepStatus.approved
            step.human_approval_status = HumanFeedbackStatus.accepted
        else:
            step.status = StepStatus.rejected
            step.human_approval_status = HumanFeedbackStatus.rejected

        step.human_feedback = received_human_feedback
        step.status = StepStatus.completed
        await self._memory_store.update_step(step)
        track_event_if_configured(
            f"{AgentType.GROUP_CHAT_MANAGER.value} - Received human feedback, Updating step and updated into the cosmos",
            {
                "status": StepStatus.completed,
                "session_id": step.session_id,
                "user_id": self._user_id,
                "human_feedback": received_human_feedback,
                "source": step.agent,
            },
        )

    async def _execute_step(self, session_id: str, step: Step):
        """
        Executes the given step by sending an ActionRequest to the appropriate agent.
        """
        # Update step status to 'action_requested'
        step.status = StepStatus.action_requested
        await self._memory_store.update_step(step)
        track_event_if_configured(
            f"{AgentType.GROUP_CHAT_MANAGER.value} - Update step to action_requested and updated into the cosmos",
            {
                "status": StepStatus.action_requested,
                "session_id": step.session_id,
                "user_id": self._user_id,
                "source": step.agent,
            },
        )

        # generate conversation history for the invoked agent
        plan = await self._memory_store.get_plan_by_session(session_id=session_id)
        steps: List[Step] = await self._memory_store.get_steps_by_plan(plan.id)

        current_step_id = step.id
        # Initialize the formatted string
        formatted_string = ""
        formatted_string += "<conversation_history>Here is the conversation history so far for the current plan. This information may or may not be relevant to the step you have been asked to execute."
        formatted_string += f"The user's task was:\n{plan.summary}\n\n"
        formatted_string += (
            f" human_clarification_request:\n{plan.human_clarification_request}\n\n"
        )
        formatted_string += (
            f" human_clarification_response:\n{plan.human_clarification_response}\n\n"
        )
        formatted_string += (
            "The conversation between the previous agents so far is below:\n"
        )

        # Iterate over the steps until the current_step_id
        for i, step in enumerate(steps):
            if step.id == current_step_id:
                break
            formatted_string += f"Step {i}\n"
            formatted_string += f"{AgentType.GROUP_CHAT_MANAGER.value}: {step.action}\n"
            formatted_string += f"{step.agent.value}: {step.agent_reply}\n"
        formatted_string += "<conversation_history \\>"

        logging.info(f"Formatted string: {formatted_string}")

        action_with_history = f"{formatted_string}. Here is the step to action: {step.action}. ONLY perform the steps and actions required to complete this specific step, the other steps have already been completed. Only use the conversational history for additional information, if it's required to complete the step you have been assigned."

        # Send action request to the appropriate agent
        action_request = ActionRequest(
            step_id=step.id,
            plan_id=step.plan_id,
            session_id=session_id,
            action=action_with_history,
            agent=step.agent,
        )
        logging.info(f"Sending ActionRequest to {step.agent.value}")

        if step.agent != "":
            agent_name = step.agent.value
            formatted_agent = agent_name.replace("_", " ")
        else:
            raise ValueError(f"Check {step.agent} is missing")

        await self._memory_store.add_item(
            AgentMessage(
                session_id=session_id,
                user_id=self._user_id,
                plan_id=step.plan_id,
                content=f"Requesting {formatted_agent} to perform action: {step.action}",
                source=AgentType.GROUP_CHAT_MANAGER.value,
                step_id=step.id,
            )
        )

        track_event_if_configured(
            f"{AgentType.GROUP_CHAT_MANAGER.value} - Requesting {formatted_agent} to perform the action and added into the cosmos",
            {
                "session_id": session_id,
                "user_id": self._user_id,
                "plan_id": step.plan_id,
                "content": f"Requesting {formatted_agent} to perform action: {step.action}",
                "source": AgentType.GROUP_CHAT_MANAGER.value,
                "step_id": step.id,
            },
        )

        if step.agent == AgentType.HUMAN.value:
            # we mark the step as complete since we have received the human feedback
            # Update step status to 'completed'
            step.status = StepStatus.completed
            await self._memory_store.update_step(step)
            logging.info(
                "Marking the step as complete - Since we have received the human feedback"
            )
            track_event_if_configured(
                "Group Chat Manager - Steps completed - Received the human feedback and updated into the cosmos",
                {
                    "session_id": session_id,
                    "user_id": self._user_id,
                    "plan_id": step.plan_id,
                    "content": "Marking the step as complete - Since we have received the human feedback",
                    "source": step.agent,
                    "step_id": step.id,
                },
            )
        else:
            # Use the agent from the step to determine which agent to send to
            agent = self._agent_instances[step.agent.value]
            await agent.handle_action_request(
                action_request
            )  # this function is in base_agent.py
            logging.info(f"Sent ActionRequest to {step.agent.value}")

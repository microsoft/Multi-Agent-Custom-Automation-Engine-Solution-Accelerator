# group_chat_manager.py

import logging
from datetime import datetime
import re
from typing import Dict, List

from autogen_core.base import AgentId, MessageContext
from autogen_core.components import RoutedAgent, default_subscription, message_handler
from autogen_core.components.models import AzureOpenAIChatCompletionClient

from context.cosmos_memory import CosmosBufferedChatCompletionContext
from models.messages import (
    ActionRequest,
    AgentMessage,
    BAgentType,
    HumanFeedback,
    HumanFeedbackStatus,
    InputTask,
    Plan,
    Step,
    StepStatus,
)

from azure.monitor.events.extension import track_event


@default_subscription
class GroupChatManager(RoutedAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        agent_ids: Dict[BAgentType, AgentId],
    ):
        super().__init__("GroupChatManager")
        self._model_client = model_client
        self._session_id = session_id
        self._user_id = user_id
        self._memory = memory
        self._agent_ids = agent_ids  # Dictionary mapping AgentType to AgentId

    @message_handler
    async def handle_input_task(
        self, message: InputTask, context: MessageContext
    ) -> Plan:
        """
        Handles the input task from the user. This is the initial message that starts the conversation.
        This method should create a new plan.
        """
        logging.info(f"Received input task: {message}")
        await self._memory.add_item(
            AgentMessage(
                session_id=message.session_id,
                user_id=self._user_id,
                plan_id="",
                content=f"{message.description}",
                source="HumanAgent",
                step_id="",
            )
        )

        track_event(
            "Group Chat Manager - Received and added input task into the cosmos",
            {
                "session_id": message.session_id,
                "user_id": self._user_id,
                "content": message.description,
                "source": "HumanAgent",
            },
        )

        # Send the InputTask to the PlannerAgent
        planner_agent_id = self._agent_ids.get(BAgentType.planner_agent)
        plan: Plan = await self.send_message(message, planner_agent_id)
        logging.info(f"Plan created: {plan}")
        return plan

    @message_handler
    async def handle_human_approval_feedback(
        self, message: HumanFeedback, context: MessageContext
    ) -> None:
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

        steps: List[Step] = await self._memory.get_steps_by_plan(message.plan_id)
        # Filter for steps that are planned or awaiting feedback

        # Get the first step assigned to HumanAgent for feedback
        human_feedback_step: Step = next(
            (s for s in steps if s.agent == BAgentType.human_agent), None
        )

        # Determine the feedback to use
        if human_feedback_step and human_feedback_step.human_feedback:
            # Use the provided human feedback if available
            received_human_feedback_on_step = human_feedback_step.human_feedback
        else:
            received_human_feedback_on_step = ""

        # Provide generic context to the model
        general_information = f"Today's date is {datetime.now().date()}."

        # Get the general background information provided by the user in regards to the overall plan (not the steps) to add as context.
        plan = await self._memory.get_plan_by_session(session_id=message.session_id)
        if plan.human_clarification_response:
            received_human_feedback_on_plan = (
                plan.human_clarification_response
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
                    self._memory.update_step(step)
                    track_event(
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
                    self._memory.update_step(step)
                    track_event(
                        "Group Chat Manager - Step has been rejected and updated into the cosmos",
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
        await self._memory.update_step(step)
        track_event(
            "Group Chat Manager - Received human feedback, Updating step and updated into the cosmos",
            {
                "status": StepStatus.completed,
                "session_id": step.session_id,
                "user_id": self._user_id,
                "human_feedback": received_human_feedback,
                "source": step.agent,
            },
        )
        # TODO: Agent verbosity
        # await self._memory.add_item(
        #     AgentMessage(
        #         session_id=step.session_id,
        #         plan_id=step.plan_id,
        #         content=feedback_message,
        #         source="GroupChatManager",
        #         step_id=step.id,
        #     )
        # )

    async def _execute_step(self, session_id: str, step: Step):
        """
        Executes the given step by sending an ActionRequest to the appropriate agent.
        """
        # Update step status to 'action_requested'
        step.status = StepStatus.action_requested
        await self._memory.update_step(step)
        track_event(
            "Group Chat Manager - Update step to action_requested and updated into the cosmos",
            {
                "status": StepStatus.action_requested,
                "session_id": step.session_id,
                "user_id": self._user_id,
                "source": step.agent,
            },
        )

        # generate conversation history for the invoked agent
        plan = await self._memory.get_plan_by_session(session_id=session_id)
        steps: List[Step] = await self._memory.get_steps_by_plan(plan.id)

        current_step_id = step.id
        # Initialize the formatted string
        formatted_string = ""
        formatted_string += "<conversation_history>Here is the conversation history so far for the current plan. This information may or may not be relevant to the step you have been asked to execute."
        formatted_string += f"The user's task was:\n{plan.summary}\n\n"
        formatted_string += (
            "The conversation between the previous agents so far is below:\n"
        )

        # Iterate over the steps until the current_step_id
        for i, step in enumerate(steps):
            if step.id == current_step_id:
                break
            formatted_string += f"Step {i}\n"
            formatted_string += f"Group chat manager: {step.action}\n"
            formatted_string += f"{step.agent.name}: {step.agent_reply}\n"
        formatted_string += "<conversation_history \\>"

        print(formatted_string)

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
            formatted_agent = re.sub(r"([a-z])([A-Z])", r"\1 \2", agent_name)
        else:
            raise ValueError(f"Check {step.agent} is missing")

        await self._memory.add_item(
            AgentMessage(
                session_id=session_id,
                user_id=self._user_id,
                plan_id=step.plan_id,
                content=f"Requesting {formatted_agent} to perform action: {step.action}",
                source="GroupChatManager",
                step_id=step.id,
            )
        )

        track_event(
            f"Group Chat Manager - Requesting {step.agent.value.title()} to perform the action and added into the cosmos",
            {
                "session_id": session_id,
                "user_id": self._user_id,
                "plan_id": step.plan_id,
                "content": f"Requesting {step.agent.value.title()} to perform action: {step.action}",
                "source": "GroupChatManager",
                "step_id": step.id,
            },
        )

        agent_id = self._agent_ids.get(step.agent)
        # If the agent_id is not found, send the request to the PlannerAgent for re-planning
        # TODO: re-think for the demo scenario
        # if not agent_id:
        #     logging.warning(
        #         f"Agent ID for agent type '{step.agent}' not found. Sending to PlannerAgent for re-planning."
        #     )
        #     planner_agent_id = self._agent_ids.get(BAgentType.planner_agent)
        #     if planner_agent_id:
        #         await self.send_message(action_request, planner_agent_id)
        #     else:
        #         logging.error("PlannerAgent ID not found in agent_ids mapping.")
        #     return

        if step.agent == BAgentType.human_agent:
            # we mark the step as complete since we have received the human feedback
            # Update step status to 'completed'
            step.status = StepStatus.completed
            await self._memory.update_step(step)
            logging.info(
                "Marking the step as complete - Since we have received the human feedback"
            )
            track_event(
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
            await self.send_message(action_request, agent_id)
            logging.info(f"Sent ActionRequest to {step.agent.value}")

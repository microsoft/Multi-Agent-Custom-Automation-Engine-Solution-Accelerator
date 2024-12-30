# human_agent.py
import logging

from autogen_core.base import AgentId, MessageContext
from autogen_core.components import (RoutedAgent, default_subscription,
                                     message_handler)

from context.cosmos_memory import CosmosBufferedChatCompletionContext
from models.messages import (
    ApprovalRequest,
    HumanFeedback,
    HumanClarification,
    HumanFeedbackStatus,
    StepStatus,
    AgentMessage,
    Step,
)
from azure.monitor.events.extension import track_event


@default_subscription
class HumanAgent(RoutedAgent):
    def __init__(
        self,
        memory: CosmosBufferedChatCompletionContext,
        user_id:str,
        group_chat_manager_id: AgentId,
    ) -> None:
        super().__init__("HumanAgent")
        self._memory = memory
        self.user_id = user_id
        self.group_chat_manager_id = group_chat_manager_id

    @message_handler
    async def handle_step_feedback(
        self, message: HumanFeedback, ctx: MessageContext
    ) -> None:
        """
        Handles the human feedback for a single step from the GroupChatManager.
        Updates the step status and stores the feedback in the session context.
        """
        # Retrieve the step from the context
        step: Step = await self._memory.get_step(message.step_id, message.session_id)
        if not step:
            logging.info(f"No step found with id: {message.step_id}")
            return

        # Update the step status and feedback
        step.status = StepStatus.completed
        step.human_feedback = message.human_feedback
        await self._memory.update_step(step)
        await self._memory.add_item(
            AgentMessage(
                session_id=message.session_id,
                user_id=self.user_id,
                plan_id=step.plan_id,
                content=f"Received feedback for step: {step.action}",
                source="HumanAgent",
                step_id=message.step_id,
            )
        )
        logging.info(f"HumanAgent received feedback for step: {step}")
        track_event(
            f"HumanAgent received feedback for step: {step} and added into the cosmos",
            {
                "session_id": message.session_id,
                "user_id": self.user_id,
                "plan_id": step.plan_id,
                "content": f"Received feedback for step: {step.action}",
                "source": "HumanAgent",
                "step_id": message.step_id,
            },
        )

        # Notify the GroupChatManager that the step has been completed
        await self._memory.add_item(
            ApprovalRequest(
                session_id=message.session_id,
                user_id=self.user_id,
                plan_id=step.plan_id,
                step_id=message.step_id,
                agent_id=self.group_chat_manager_id,
            )
        )
        logging.info(f"HumanAgent sent approval request for step: {step}")
        
        track_event(
            f"HumanAgent sent approval request for step {step} and added into the cosmos",
            {
                "session_id": message.session_id,
                "user_id": self.user_id,
                "plan_id": step.plan_id,
                "step_id": message.step_id,
                "agent_id": self.group_chat_manager_id,
            },
        )

"""
Human-in-the-loop Magentic Manager for employee onboarding orchestration.
Extends StandardMagenticManager (agent_framework version) to add approval gates before plan execution.
"""

import asyncio
import logging
from typing import Any, Optional

import v4.models.messages as messages
from agent_framework import ChatMessage
from agent_framework._workflows._magentic import (
    MagenticContext,
    StandardMagenticManager,
    ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
)

from v4.config.settings import connection_config, orchestration_config
from v4.models.models import MPlan
from v4.orchestration.helper.plan_to_mplan_converter import PlanToMPlanConverter

logger = logging.getLogger(__name__)


class HumanApprovalMagenticManager(StandardMagenticManager):
    """
    Extended Magentic manager (agent_framework) that requires human approval before executing plan steps.
    Provides interactive approval for each step in the orchestration plan.
    """

    approval_enabled: bool = True
    magentic_plan: Optional[MPlan] = None
    current_user_id: str  # populated in __init__

    def __init__(self, user_id: str, agent, *args, **kwargs):
        """
        Initialize the HumanApprovalMagenticManager.
        Args:
            user_id: ID of the user to associate with this orchestration instance.
            agent: The manager ChatAgent for orchestration (required by new API).
            *args: Additional positional arguments for the parent StandardMagenticManager.
            **kwargs: Additional keyword arguments for the parent StandardMagenticManager.
        """

        plan_append = """

IMPORTANT: Never ask the user for information or clarification until all agents on the team have been asked first.

EXAMPLE: If the user request involves product information, first ask all agents on the team to provide the information.
Do not ask the user unless all agents have been consulted and the information is still missing.

Plan steps should always include a bullet point, followed by an agent name, followed by a description of the action
to be taken. If a step involves multiple actions, separate them into distinct steps with an agent included in each step.
If the step is taken by an agent that is not part of the team, such as the MagenticManager, please always list the MagenticManager as the agent for that step. At any time, if more information is needed from the user, use the ProxyAgent to request this information.

CRITICAL: Each agent should only be called ONCE to perform their task. Do NOT call the same agent multiple times.
After an agent has provided their response, move on to the next agent in the plan.

Here is an example of a well-structured plan:
- **EnhancedResearchAgent** to gather authoritative data on the latest industry trends and best practices in employee onboarding
- **EnhancedResearchAgent** to gather authoritative data on Innovative onboarding techniques that enhance new hire engagement and retention.
- **DocumentCreationAgent** to draft a comprehensive onboarding plan that includes a detailed schedule of onboarding activities and milestones.
- **DocumentCreationAgent** to draft a comprehensive onboarding plan that includes a checklist of resources and materials needed for effective onboarding.
- **ProxyAgent** to review the drafted onboarding plan for clarity and completeness.
- **MagenticManager** to finalize the onboarding plan and prepare it for presentation to stakeholders.
"""

        # Add progress ledger prompt to prevent re-calling agents
        progress_append = """
CRITICAL RULE: DO NOT call the same agent more than once unless absolutely necessary.
If an agent has already provided a response, consider their task COMPLETE and move to the next agent.
Only re-call an agent if their previous response was explicitly an error or failure.
"""

        final_append = """
DO NOT EVER OFFER TO HELP FURTHER IN THE FINAL ANSWER! Just provide the final answer and end with a polite closing.
"""

        kwargs["task_ledger_plan_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT + plan_append
        )
        kwargs["task_ledger_plan_update_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT + plan_append
        )
        kwargs["final_answer_prompt"] = ORCHESTRATOR_FINAL_ANSWER_PROMPT + final_append

        # Override progress ledger prompt to discourage re-calling agents
        from agent_framework._workflows._magentic import ORCHESTRATOR_PROGRESS_LEDGER_PROMPT
        kwargs["progress_ledger_prompt"] = ORCHESTRATOR_PROGRESS_LEDGER_PROMPT + progress_append

        self.current_user_id = user_id
        # New API: StandardMagenticManager takes agent as first positional argument
        super().__init__(agent, *args, **kwargs)

    async def plan(self, magentic_context: MagenticContext) -> Any:
        """
        Override the plan method to create the plan first, then ask for approval before execution.
        Returns the original plan ChatMessage if approved, otherwise raises.
        """
        # Normalize task text
        task_text = getattr(magentic_context.task, "text", str(magentic_context.task))

        logger.info("\n Human-in-the-Loop Magentic Manager Creating Plan:")
        logger.info("   Task: %s", task_text)
        logger.info("-" * 60)

        logger.info(" Creating execution plan...")
        plan_message = await super().plan(magentic_context)
        logger.info(
            " Plan created (assistant message length=%d)",
            len(plan_message.text) if plan_message and plan_message.text else 0,
        )

        # Build structured MPlan from task ledger
        if self.task_ledger is None:
            raise RuntimeError("task_ledger not set after plan()")

        self.magentic_plan = self.plan_to_obj(magentic_context, self.task_ledger)
        self.magentic_plan.user_id = self.current_user_id  # annotate with user

        approval_message = messages.PlanApprovalRequest(
            plan=self.magentic_plan,
            status="PENDING_APPROVAL",
            context=(
                {
                    "task": task_text,
                    "participant_descriptions": magentic_context.participant_descriptions,
                }
                if hasattr(magentic_context, "participant_descriptions")
                else {}
            ),
        )

        try:
            orchestration_config.plans[self.magentic_plan.id] = self.magentic_plan
        except Exception as e:
            logger.error("Error processing plan approval: %s", e)

        # Send approval request
        await connection_config.send_status_update_async(
            message=approval_message,
            user_id=self.current_user_id,
            message_type=messages.WebsocketMessageType.PLAN_APPROVAL_REQUEST,
        )

        # Await user response
        approval_response = await self._wait_for_user_approval(approval_message.plan.id)

        if approval_response and approval_response.approved:
            logger.info("Plan approved - proceeding with execution...")
            return plan_message
        else:
            logger.debug("Plan execution cancelled by user")
            await connection_config.send_status_update_async(
                {
                    "type": messages.WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
                    "data": approval_response,
                },
                user_id=self.current_user_id,
                message_type=messages.WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
            )
            raise Exception("Plan execution cancelled by user")

    async def replan(self, magentic_context: MagenticContext) -> Any:
        """
        Override to add websocket messages for replanning events.
        """
        logger.info("\nHuman-in-the-Loop Magentic Manager replanned:")
        replan_message = await super().replan(magentic_context=magentic_context)
        logger.info(
            "Replanned message length: %d",
            len(replan_message.text) if replan_message and replan_message.text else 0,
        )
        return replan_message

    async def create_progress_ledger(self, magentic_context: MagenticContext):
        """
        Check for max rounds exceeded and send final message if so, else defer to base.

        Returns:
            Progress ledger object (type depends on agent_framework version)
        """
        if magentic_context.round_count >= orchestration_config.max_rounds:
            final_message = messages.FinalResultMessage(
                content="Process terminated: Maximum rounds exceeded",
                status="terminated",
                summary=f"Stopped after {magentic_context.round_count} rounds (max: {orchestration_config.max_rounds})",
            )

            await connection_config.send_status_update_async(
                message=final_message,
                user_id=self.current_user_id,
                message_type=messages.WebsocketMessageType.FINAL_RESULT_MESSAGE,
            )

            # Call base class to get the proper ledger type, then raise to terminate
            ledger = await super().create_progress_ledger(magentic_context)

            # Override key fields to signal termination
            ledger.is_request_satisfied.answer = True
            ledger.is_request_satisfied.reason = "Maximum rounds exceeded"
            ledger.is_in_loop.answer = False
            ledger.is_in_loop.reason = "Terminating"
            ledger.is_progress_being_made.answer = False
            ledger.is_progress_being_made.reason = "Terminating"
            ledger.next_speaker.answer = ""
            ledger.next_speaker.reason = "Task complete"
            ledger.instruction_or_question.answer = "Process terminated due to maximum rounds exceeded"
            ledger.instruction_or_question.reason = "Task complete"

            return ledger

        # Delegate to base for normal progress ledger creation
        return await super().create_progress_ledger(magentic_context)

    async def _wait_for_user_approval(
        self, m_plan_id: Optional[str] = None
    ) -> Optional[messages.PlanApprovalResponse]:
        """
        Wait for user approval response using event-driven pattern with timeout handling.
        """
        logger.info("Waiting for user approval for plan: %s", m_plan_id)

        if not m_plan_id:
            logger.error("No plan ID provided for approval")
            return messages.PlanApprovalResponse(approved=False, m_plan_id=m_plan_id)

        orchestration_config.set_approval_pending(m_plan_id)

        try:
            approved = await orchestration_config.wait_for_approval(m_plan_id)
            logger.info("Approval received for plan %s: %s", m_plan_id, approved)
            return messages.PlanApprovalResponse(approved=approved, m_plan_id=m_plan_id)

        except asyncio.TimeoutError:
            logger.debug(
                "Approval timeout for plan %s - notifying user and terminating process",
                m_plan_id,
            )

            timeout_message = messages.TimeoutNotification(
                timeout_type="approval",
                request_id=m_plan_id,
                message=f"Plan approval request timed out after {orchestration_config.default_timeout} seconds. Please try again.",
                timestamp=asyncio.get_event_loop().time(),
                timeout_duration=orchestration_config.default_timeout,
            )

            try:
                await connection_config.send_status_update_async(
                    message=timeout_message,
                    user_id=self.current_user_id,
                    message_type=messages.WebsocketMessageType.TIMEOUT_NOTIFICATION,
                )
                logger.info(
                    "Timeout notification sent to user %s for plan %s",
                    self.current_user_id,
                    m_plan_id,
                )
            except Exception as e:
                logger.error("Failed to send timeout notification: %s", e)

            orchestration_config.cleanup_approval(m_plan_id)
            return None

        except KeyError as e:
            logger.debug("Plan ID not found: %s - terminating process silently", e)
            return None

        except asyncio.CancelledError:
            logger.debug("Approval request %s was cancelled", m_plan_id)
            orchestration_config.cleanup_approval(m_plan_id)
            return None

        except Exception as e:
            logger.debug(
                "Unexpected error waiting for approval: %s - terminating process silently",
                e,
            )
            orchestration_config.cleanup_approval(m_plan_id)
            return None

        finally:
            if (
                m_plan_id in orchestration_config.approvals
                and orchestration_config.approvals[m_plan_id] is None
            ):
                logger.debug("Final cleanup for pending approval plan %s", m_plan_id)
                orchestration_config.cleanup_approval(m_plan_id)

    async def prepare_final_answer(
        self, magentic_context: MagenticContext
    ) -> ChatMessage:
        """
        Override to ensure final answer is prepared after all steps are executed.
        """
        logger.info("\n Magentic Manager - Preparing final answer...")
        return await super().prepare_final_answer(magentic_context)

    def plan_to_obj(self, magentic_context: MagenticContext, ledger) -> MPlan:
        """Convert the generated plan from the ledger into a structured MPlan object."""
        if (
            ledger is None
            or not hasattr(ledger, "plan")
            or not hasattr(ledger, "facts")
        ):
            raise ValueError(
                "Invalid ledger structure; expected plan and facts attributes."
            )

        task_text = getattr(magentic_context.task, "text", str(magentic_context.task))

        return_plan: MPlan = PlanToMPlanConverter.convert(
            plan_text=getattr(ledger.plan, "text", ""),
            facts=getattr(ledger.facts, "text", ""),
            team=list(magentic_context.participant_descriptions.keys()),
            task=task_text,
        )

        return return_plan

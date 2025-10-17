"""
Human-in-the-loop Magentic Manager for employee onboarding orchestration.
Extends StandardMagenticManager to add approval gates before plan execution.
"""

import asyncio
import logging
from typing import Any, Optional

import v3.models.messages as messages
from semantic_kernel.agents.orchestration.magentic import (
    MagenticContext,
    ProgressLedger,
    ProgressLedgerItem,
    StandardMagenticManager,
)
from semantic_kernel.agents.orchestration.prompts._magentic_prompts import (
    ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
)
from semantic_kernel.contents import ChatMessageContent
from v3.config.settings import connection_config, orchestration_config
from v3.models.models import MPlan
from v3.orchestration.helper.plan_to_mplan_converter import \
    PlanToMPlanConverter

# Using a module level logger to avoid pydantic issues around inherited fields
logger = logging.getLogger(__name__)


# Create a progress ledger that indicates the request is satisfied (task completed)
class HumanApprovalMagenticManager(StandardMagenticManager):
    """
    Extended Magentic manager that requires human approval before executing plan steps.
    Provides interactive approval for each step in the orchestration plan.
    """

    # Define Pydantic fields to avoid validation errors
    approval_enabled: bool = True
    magentic_plan: Optional[MPlan] = None
    current_user_id: str

    def __init__(self, user_id: str, *args, **kwargs):
        """
        Initialize the HumanApprovalMagenticManager.
        Args:
            user_id: ID of the user to associate with this orchestration instance.
            *args: Additional positional arguments for the parent StandardMagenticManager.
            **kwargs: Additional keyword arguments for the parent StandardMagenticManager.
        """

        # Remove any custom kwargs before passing to parent

        plan_append = """
IMPORTANT: Never ask the user for information or clarification until all agents on the team have been asked first.

EXAMPLE: If the user request involves product information, first ask all agents on the team to provide the information.
Do not ask the user unless all agents have been consulted and the information is still missing.

Plan steps should always include a bullet point, followed by an agent name, followed by a description of the action
to be taken. If a step involves multiple actions, separate them into distinct steps with an agent included in each step.
If the step is taken by an agent that is not part of the team, such as the MagenticManager, please always list the MagenticManager as the agent for that step. At any time, if more information is needed from the user, use the ProxyAgent to request this information.

Here is an example of a well-structured plan:
- **EnhancedResearchAgent** to gather authoritative data on the latest industry trends and best practices in employee onboarding
- **EnhancedResearchAgent** to gather authoritative data on Innovative onboarding techniques that enhance new hire engagement and retention.
- **DocumentCreationAgent** to draft a comprehensive onboarding plan that includes a detailed schedule of onboarding activities and milestones.
- **DocumentCreationAgent** to draft a comprehensive onboarding plan that includes a checklist of resources and materials needed for effective onboarding.
- **ProxyAgent** to review the drafted onboarding plan for clarity and completeness.
- **MagenticManager** to finalize the onboarding plan and prepare it for presentation to stakeholders.

"""

        final_append = """
 DO NOT EVER OFFER TO HELP FURTHER IN THE FINAL ANSWER! Just provide the final answer and end with a polite closing.
"""

        # kwargs["task_ledger_facts_prompt"] = ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT + facts_append
        kwargs["task_ledger_plan_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT + plan_append
        )
        kwargs["task_ledger_plan_update_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT + plan_append
        )
        kwargs["final_answer_prompt"] = ORCHESTRATOR_FINAL_ANSWER_PROMPT + final_append

        kwargs['current_user_id'] = user_id

        super().__init__(*args, **kwargs)

    async def plan(self, magentic_context: MagenticContext) -> Any:
        """
        Override the plan method to create the plan first, then ask for approval before execution.
        """
        # Extract task text from the context
        task_text = magentic_context.task
        if hasattr(task_text, "content"):
            task_text = task_text.content
        elif not isinstance(task_text, str):
            task_text = str(task_text)

        logger.info("\n Human-in-the-Loop Magentic Manager Creating Plan:")
        logger.info("   Task: %s", task_text)
        logger.info("-" * 60)

        # First, let the parent create the actual plan
        logger.info(" Creating execution plan...")
        plan = await super().plan(magentic_context)
        logger.info(" Plan created: %s", plan)

        self.magentic_plan = self.plan_to_obj(magentic_context, self.task_ledger)

        self.magentic_plan.user_id = self.current_user_id

        # Request approval from the user before executing the plan
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

        # Send the approval request to the user's WebSocket
        # The user_id will be automatically retrieved from context
        await connection_config.send_status_update_async(
            message=approval_message,
            user_id=self.current_user_id,
            message_type=messages.WebsocketMessageType.PLAN_APPROVAL_REQUEST,
        )

        # Wait for user approval
        approval_response = await self._wait_for_user_approval(approval_message.plan.id)

        if approval_response and approval_response.approved:
            logger.info("Plan approved - proceeding with execution...")
            return plan
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
        replan = await super().replan(magentic_context=magentic_context)
        logger.info("Replanned: %s", replan)
        return replan

    async def create_progress_ledger(
        self, magentic_context: MagenticContext
    ) -> ProgressLedger:
        """Check for max rounds exceeded and send final message if so."""
        if magentic_context.round_count >= orchestration_config.max_rounds:
            # Send final message to user
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

            return ProgressLedger(
                is_request_satisfied=ProgressLedgerItem(
                    reason="Maximum rounds exceeded", answer=True
                ),
                is_in_loop=ProgressLedgerItem(reason="Terminating", answer=False),
                is_progress_being_made=ProgressLedgerItem(
                    reason="Terminating", answer=False
                ),
                next_speaker=ProgressLedgerItem(reason="Task complete", answer=""),
                instruction_or_question=ProgressLedgerItem(
                    reason="Task complete",
                    answer="Process terminated due to maximum rounds exceeded",
                ),
            )

        return await super().create_progress_ledger(magentic_context)

    # plan_id will not be optional in future
    async def _wait_for_user_approval(
        self, m_plan_id: Optional[str] = None
    ) -> Optional[messages.PlanApprovalResponse]:
        """
        Wait for user approval response using event-driven pattern with timeout handling.

        Args:
            m_plan_id: The plan ID to wait for approval

        Returns:
            PlanApprovalResponse: Approval result with approved status and plan ID

        Raises:
            asyncio.TimeoutError: If timeout is exceeded (300 seconds default)
        """
        logger.info(f"Waiting for user approval for plan: {m_plan_id}")

        if not m_plan_id:
            logger.error("No plan ID provided for approval")
            return messages.PlanApprovalResponse(approved=False, m_plan_id=m_plan_id)

        # Initialize approval as pending using the new event-driven method
        orchestration_config.set_approval_pending(m_plan_id)

        try:
            # Wait for approval with timeout using the new event-driven method
            approved = await orchestration_config.wait_for_approval(m_plan_id)

            logger.info(f"Approval received for plan {m_plan_id}: {approved}")
            return messages.PlanApprovalResponse(
                approved=approved, m_plan_id=m_plan_id
            )
        except asyncio.TimeoutError:
            # Enhanced timeout handling - notify user via WebSocket and cleanup
            logger.debug(f"Approval timeout for plan {m_plan_id} - notifying user and terminating process")

            # Create timeout notification message
            timeout_message = messages.TimeoutNotification(
                timeout_type="approval",
                request_id=m_plan_id,
                message=f"Plan approval request timed out after {orchestration_config.default_timeout} seconds. Please try again.",
                timestamp=asyncio.get_event_loop().time(),
                timeout_duration=orchestration_config.default_timeout
            )

            # Send timeout notification to user via WebSocket
            try:
                await connection_config.send_status_update_async(
                    message=timeout_message,
                    user_id=self.current_user_id,
                    message_type=messages.WebsocketMessageType.TIMEOUT_NOTIFICATION,
                )
                logger.info(f"Timeout notification sent to user {self.current_user_id} for plan {m_plan_id}")
            except Exception as e:
                logger.error(f"Failed to send timeout notification: {e}")

            # Clean up this specific request
            orchestration_config.cleanup_approval(m_plan_id)

            # Return None to indicate silent termination
            # The timeout naturally stops this specific wait operation without affecting other tasks
            return None

        except KeyError as e:
            # Silent error handling for invalid plan IDs
            logger.debug(f"Plan ID not found: {e} - terminating process silently")
            return None

        except asyncio.CancelledError:
            # Handle task cancellation gracefully
            logger.debug(f"Approval request {m_plan_id} was cancelled")
            orchestration_config.cleanup_approval(m_plan_id)
            return None

        except Exception as e:
            # Silent error handling for unexpected errors
            logger.debug(f"Unexpected error waiting for approval: {e} - terminating process silently")
            orchestration_config.cleanup_approval(m_plan_id)
            return None
        finally:
            # Ensure cleanup happens for any incomplete requests
            # This provides an additional safety net for resource cleanup
            if (m_plan_id in orchestration_config.approvals and orchestration_config.approvals[m_plan_id] is None):
                logger.debug(f"Final cleanup for pending approval plan {m_plan_id}")
                orchestration_config.cleanup_approval(m_plan_id)

    async def prepare_final_answer(
        self, magentic_context: MagenticContext
    ) -> ChatMessageContent:
        """
        Override to ensure final answer is prepared after all steps are executed.
        """
        logger.info("\n Magentic Manager - Preparing final answer...")

        return await super().prepare_final_answer(magentic_context)

    def plan_to_obj(self, magentic_context, ledger) -> MPlan:
        """Convert the generated plan from the ledger into a structured MPlan object."""

        return_plan: MPlan = PlanToMPlanConverter.convert(
            plan_text=ledger.plan.content,
            facts=ledger.facts.content,
            team=list(magentic_context.participant_descriptions.keys()),
            task=magentic_context.task,
        )

        # # get the request text from the ledger
        # if hasattr(magentic_context, 'task'):
        #     return_plan.user_request = magentic_context.task

        # return_plan.team = list(magentic_context.participant_descriptions.keys())

        # # Get the facts content from the ledger
        # if hasattr(ledger, 'facts') and ledger.facts.content:
        #     return_plan.facts = ledger.facts.content

        # # Get the plan / steps content from the ledger
        # # Split the description into lines and clean them
        # lines = [line.strip() for line in ledger.plan.content.strip().split('\n') if line.strip()]

        # found_agent = None
        # prefix = None

        # for line in lines:
        #     found_agent = None
        #     prefix = None
        #     # log the line for troubleshooting
        #     logger.debug("Processing plan line: %s", line)

        #     # match only lines that have bullet points
        #     if re.match(r'^[-•*]\s+', line):
        #         # Remove the bullet point marker
        #         line = re.sub(r'^[-•*]\s+', '', line).strip()

        #         # Look for agent names in the line

        #         for agent_name in return_plan.team:
        #             # Check if agent name appears in the line (case insensitive)
        #             if agent_name.lower() in line[:20].lower():
        #                 found_agent = agent_name
        #                 line = line.split(agent_name, 1)
        #                 line = line[1].strip() if len(line) > 1 else ""
        #                 line = line.replace('*', '').strip()
        #                 break

        #         if not found_agent:
        #             # If no agent found, assign to ProxyAgent if available
        #             found_agent = "MagenticAgent"
        #         # If line indicates a following list of actions (e.g. "Assign **EnhancedResearchAgent**
        #         # to gather authoritative data on:") save and prefix to the steps
        #         # if line.endswith(':'):
        #         #     line = line.replace(':', '').strip()
        #         #     prefix = line + " "

        #         # Don't create a step if action is blank
        #         if line.strip() != "":
        #             if prefix:
        #                 line = prefix + line
        #             # Create the step object
        #             step = MStep(agent=found_agent, action=line)

        #             # add the step to the plan
        #             return_plan.steps.append(step) # pylint: disable=E1101

        return return_plan

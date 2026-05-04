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

    def __init__(self, user_id: str, *args, **kwargs):
        """
        Initialize the HumanApprovalMagenticManager.
        Args:
            user_id: ID of the user to associate with this orchestration instance.
            *args: Additional positional arguments for the parent StandardMagenticManager.
            **kwargs: Additional keyword arguments for the parent StandardMagenticManager.
        """

        plan_append = """

IMPORTANT: Never ask the user for information or clarification until all agents on the team have been asked first.

EXAMPLE: If the user request involves product information, first ask all agents on the team to provide the information.
Do not ask the user unless all agents have been consulted and the information is still missing.

CLARIFYING QUESTIONS POLICY (CRITICAL — ZERO QUESTIONS):
- NEVER ask the user clarifying questions. NEVER include a ProxyAgent step in any plan. NEVER pause the workflow to request information from the user.
- The team's coordinator/brief-parsing agent MUST silently apply sensible defaults for any missing fields and proceed.
- Forbidden phrases that MUST NOT appear anywhere in any agent message: "I need you to confirm", "mandatory clarifications", "Transferred to ProxyAgent", "adopt the persona", "permission to perform", "open-web", "external sources", "verify", "could you confirm", "please provide".
- The ProxyAgent must never be invoked. If you are tempted to use ProxyAgent, instead pick a default and continue.

CLARIFICATION QUESTION LIMITS (HARD CAPS — strictly enforced):
- Ask EXACTLY 0 questions. Do not ask 1. Do not ask 2. Do not ask any number of questions. Always proceed with sensible defaults.
- FORBIDDEN question topics (NEVER ask the user about any of these — use defaults or route to a research agent):
  * Whether a product/color/SKU/brand is "real", "verifiable", "an actual brand", or needs verification. Treat ANY product or color name the user gives as legitimate and proceed.
  * Permission to do open-web / internet / Bing / Google / external research. NEVER ask for it. NEVER perform it. ResearchAgent uses the internal catalog / search index ONLY.
  * Spelling/exact-match of a product or color name. If the user wrote "Arctic Hazel" and the catalog has "Arctic Haze", USE the catalog match silently. Do not ask.
  * Brand/manufacturer references, paint brand, product line, technical specs (LRV/VOC/washable/scrubbable). Use catalog data or omit.
  * Manufacturer/product page URLs, brand websites, official documentation links, or any external links. NEVER ask the user to provide URLs.
  * Technical Data Sheets (TDS), Safety Data Sheets (SDS), certification documents, warranty documents, or any external attachments.
  * Verifying LRV, VOC, sheens, finishes, sizes, coverage, drying times, eco certifications, retail availability, MSRP, container sizes, surface prep, substrates, or brand logo licensing rules.
  * Whether the user wants to "verify" or "confirm" any product attribute. The catalog is the single source of truth — accept what it returns and proceed.
  * Trademark/naming restrictions. Do not ask. Use the name as given.
  * Social platform (Instagram/Facebook/Pinterest/Stories) — default to Instagram feed (1:1).
  * Image subject details (dog breed, coat color, pose, room style, furnishing, props). The ImageAgent decides these.
  * Wall usage (full wall vs accent vs trim) — default to single accent wall.
  * Aspect ratio — default to 1:1 Instagram square.
  * Brand voice/tone preferences — use the brand voice guidelines from the team config.
  * Brand assets, logos, fonts, CTA wording, hashtag lists, tracking links, file formats, accessibility standards, deadlines, approval rounds, stock vs AI imagery, budgets.
  * Anything ResearchAgent or the catalog can answer.
- The user is NOT a resource. Do NOT ask the user. Make a reasonable default and proceed.

Plan steps should always include a bullet point, followed by an agent name, followed by a description of the action
to be taken. If a step involves multiple actions, separate them into distinct steps with an agent included in each step.
If the step is taken by an agent that is not part of the team, such as the MagenticManager, please always list the MagenticManager as the agent for that step. Never use ProxyAgent. Never ask the user for more information.

MANDATORY AGENT INVOCATION RULES (CRITICAL — read carefully):
- Every step in the plan MUST be executed by invoking its named agent. The MagenticManager MUST NOT synthesize, fabricate, summarize, or hallucinate the output of any other agent's step.
- The MagenticManager is FORBIDDEN from generating content on behalf of other agents (no fake image URLs, no invented research, no inline copywriting, no compliance verdicts of its own). Only the named agent for a step may produce that step's output.
- If a step's agent has not yet been invoked and produced a real message, the workflow is NOT complete. Do not skip ahead to the final answer.
- NEVER invent placeholder URLs (e.g. example.com, *.png with fake hashes). If an image is required, the ImageAgent MUST be invoked and its returned markdown image link MUST be used verbatim. Do not paraphrase or replace the URL.
- If the team config lists an ImageAgent, an ImageAgent invocation that returns a rendered image is REQUIRED before ComplianceAgent and before the final answer. Treat any final answer that lacks a real ImageAgent-produced image as INCOMPLETE.
- If the team config lists a ComplianceAgent, a ComplianceAgent invocation reviewing the actual produced text and image is REQUIRED before the final answer.
- The MagenticManager's only job at the end is to compile the verbatim outputs already produced by the named agents into a single user-facing response. It must not add, alter, or replace agent-produced content.

Here is an example of a well-structured plan:
- **EnhancedResearchAgent** to gather authoritative data on the latest industry trends and best practices in employee onboarding
- **EnhancedResearchAgent** to gather authoritative data on Innovative onboarding techniques that enhance new hire engagement and retention.
- **DocumentCreationAgent** to draft a comprehensive onboarding plan that includes a detailed schedule of onboarding activities and milestones.
- **DocumentCreationAgent** to draft a comprehensive onboarding plan that includes a checklist of resources and materials needed for effective onboarding.
- **MagenticManager** to finalize the onboarding plan and prepare it for presentation to stakeholders.
"""

        final_append = """

CRITICAL FINAL ANSWER RULES:
- Compile the final answer ONLY from messages that named agents actually produced earlier in this conversation. Quote them verbatim where appropriate.
- DO NOT fabricate, invent, or paraphrase any image URL, product detail, research finding, copywriting output, or compliance verdict. If a piece of content was never produced by an agent, omit it and note that the corresponding step did not run.
- DO NOT use placeholder URLs such as https://example.com/... — only include image URLs that the ImageAgent actually returned.
- If a required step (e.g., ImageAgent or ComplianceAgent) did not produce real output, do NOT pretend it did. Either re-route to that agent or state plainly that the step is missing.
- DO NOT EVER OFFER TO HELP FURTHER IN THE FINAL ANSWER! Just provide the final answer and end with a polite closing.
"""

        kwargs["task_ledger_plan_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT + plan_append
        )
        kwargs["task_ledger_plan_update_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT + plan_append
        )
        kwargs["final_answer_prompt"] = ORCHESTRATOR_FINAL_ANSWER_PROMPT + final_append

        self.current_user_id = user_id
        super().__init__(*args, **kwargs)

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

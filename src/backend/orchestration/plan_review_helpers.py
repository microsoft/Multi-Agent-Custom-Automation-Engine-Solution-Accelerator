"""
Prompt customization and plan-review helpers for MagenticBuilder workflows.

Provides:
- ``get_magentic_prompt_kwargs()`` — returns a dict of prompt overrides for MagenticBuilder.
- ``convert_plan_review_to_mplan()`` — converts a MagenticPlanReviewRequest into an MPlan.
- ``wait_for_plan_approval()`` — WebSocket-based approval gate with timeout handling.
"""

import asyncio
import logging
from typing import Optional

import models.messages as messages
from agent_framework_orchestrations._magentic import (
    ORCHESTRATOR_FINAL_ANSWER_PROMPT, ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT)
from models.plan_models import MPlan
from orchestration.connection_config import (connection_config,
                                             orchestration_config)
from orchestration.helper.plan_to_mplan_converter import PlanToMPlanConverter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt kwargs builder
# ---------------------------------------------------------------------------

def get_magentic_prompt_kwargs(*, has_user_responses: bool = False) -> dict:
    """Build the prompt-override kwargs dict for ``MagenticBuilder``.

    Args:
        has_user_responses: Whether any agent has ``user_responses: true``,
            giving it access to the ``ask_user`` tool for user clarification.
            When True, prompts allow agents to gather info via their tools;
            when False, agents must use defaults only.

    Returns:
        A dict suitable for unpacking into ``MagenticBuilder(**kwargs)``.
    """
    if has_user_responses:
        clarification_policy = """
USER CLARIFICATION POLICY (UserInteractionAgent is a participant):
- BEFORE creating a plan, review the task for missing user-specific information
  that domain agents will need (e.g. employee name, start date, role,
  preferences, configuration choices).
- If critical details are missing, include a step for **UserInteractionAgent** at
  the START of the plan to gather that information.  Describe exactly what
  questions to ask (numbered list with required/optional markers).
- Only include a UserInteractionAgent step when information is genuinely missing —
  if the user already provided enough detail, proceed directly to domain agents.
- After UserInteractionAgent returns the answers, subsequent agents receive them
  as part of the conversation history — no manual forwarding needed.
- If a domain agent reports during execution that it needs additional user info,
  select UserInteractionAgent as next_speaker with a message describing what is
  needed, then re-invoke the requesting agent afterward.
- Do NOT fabricate, assume, or hallucinate missing user-specific details.
- NEVER call ask_user yourself — only UserInteractionAgent has that tool.
"""
    else:
        clarification_policy = """
CLARIFYING QUESTIONS POLICY (CRITICAL — ZERO QUESTIONS):
- NEVER ask the user clarifying questions. NEVER pause the workflow to request
  information from the user.
- Agents MUST silently apply sensible defaults for any missing fields and proceed.
- Ask EXACTLY 0 questions. Always proceed with sensible defaults.
"""

    plan_append = f"""

PLAN RULES:
- Steps are HIGH-LEVEL task assignments — one step per agent. Do NOT prescribe
  sub-tasks, parameters, or data retrieval. Agents discover their own processes.
{clarification_policy}
FORMAT: Each step = bullet + **AgentName** + "to" + action. Use exact agent names.
Example (when user info is missing):
- **UserInteractionAgent** to ask the user for the new employee's full name, start date, and role.
- **HRHelperAgent** to execute the onboarding process for the new employee.
- **TechnicalSupportAgent** to provision IT resources and accounts for the new employee.
- **MagenticManager** to compile a final onboarding summary for the user.

Example (when user provided all details):
- **HRHelperAgent** to execute the onboarding process for the new employee.
- **TechnicalSupportAgent** to provision IT resources and accounts for the new employee.
- **MagenticManager** to compile a final onboarding summary for the user.

Note: UserInteractionAgent is the ONLY agent that communicates with the user.
MagenticManager NEVER asks the user questions directly.

INVOCATION RULES:
- Every plan step MUST be executed by its named agent. MagenticManager MUST NOT
  fabricate content on behalf of other agents (no fake URLs, no invented results).
- If an agent has not been invoked yet, the workflow is NOT complete.
- MagenticManager's final job: compile verbatim agent outputs into one response.
"""

    final_append = """

FINAL ANSWER RULES:
- Compile ONLY from messages agents actually produced. Quote verbatim where appropriate.
- Do NOT fabricate URLs, results, or content that no agent produced.
- If a required agent step did not run, state it plainly — do not pretend it did.
- Do NOT offer further help. Provide the answer and end with a polite closing.
"""

    kwargs: dict = {
        "task_ledger_plan_prompt": ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT + plan_append,
        "task_ledger_plan_update_prompt": ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT + plan_append,
        "final_answer_prompt": ORCHESTRATOR_FINAL_ANSWER_PROMPT + final_append,
    }

    if has_user_responses:
        facts_append = """

- Under "FACTS TO LOOK UP", list ONLY facts agents can discover via their tools.
  Do NOT list user-specific information (preferences, choices, dates).
- Under "EDUCATED GUESSES", do NOT guess user-specific details.
"""
        kwargs["task_ledger_facts_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT + facts_append
        )

        progress_append = """

EXECUTION RULES:
- When selecting next_speaker, prefer a work agent that has NOT yet been invoked.
- MagenticManager MUST NOT generate answers, ask questions, or list missing info.
  It only routes tasks to the appropriate agent.
- If a domain agent's response indicates it needs user clarification (e.g. it says
  "I need the user to provide X"), select **UserInteractionAgent** as next_speaker
  with a message describing what is needed, then re-invoke the domain agent after.

COMPLETION CHECK (CRITICAL):
Before setting is_request_satisfied to true, you MUST verify:
1. Review the conversation history and list every agent that has actually produced
   a substantive response (called tools and returned results).
2. Compare that list against the plan steps. If ANY plan-step agent has NOT been
   invoked and produced a substantive response, set is_request_satisfied to false
   and select the next uninvoked agent as next_speaker.
3. is_request_satisfied = true ONLY when ALL plan-step agents have completed
   their work successfully (called their tools, returned results).
- Each agent handles a DISTINCT domain. One agent's output does NOT satisfy
  another agent's step.
- Do NOT re-invoke an agent that already completed its step successfully.
- IGNORE agent-level completion language (e.g. "all steps are complete",
  "onboarding is done"). An individual agent only knows about its own domain.
  The workflow is NOT complete until every plan-step agent has been invoked."""
        kwargs["progress_ledger_prompt"] = (
            ORCHESTRATOR_PROGRESS_LEDGER_PROMPT + progress_append
        )

    return kwargs


# ---------------------------------------------------------------------------
# Plan conversion
# ---------------------------------------------------------------------------

def convert_plan_review_to_mplan(
    plan_review_request,
    participant_names: list[str],
    task_text: str,
    user_id: str,
) -> MPlan:
    """Convert a ``MagenticPlanReviewRequest`` into a structured ``MPlan``.

    Args:
        plan_review_request: The framework's ``MagenticPlanReviewRequest`` event data.
        participant_names: List of participant agent names in the workflow.
        task_text: The original user task description.
        user_id: User ID to annotate on the plan.

    Returns:
        An ``MPlan`` instance suitable for frontend display.
    """
    # plan_review_request.plan may be a _MagenticTaskLedger (with .plan and
    # .facts Message sub-attrs) OR a plain Message (after serialisation).
    # Handle both cases.
    obj = plan_review_request.plan
    if obj is None:
        raise ValueError("Plan review request has no plan data.")

    logger.info(
        "[DEBUG] plan_review_request.plan type=%s, has .text=%s, has .plan=%s",
        type(obj).__name__,
        hasattr(obj, "text"),
        hasattr(obj, "plan"),
    )

    inner_plan = getattr(obj, "plan", None)  # _MagenticTaskLedger path
    inner_facts = getattr(obj, "facts", None)

    if inner_plan is not None and hasattr(inner_plan, "text"):
        # _MagenticTaskLedger — plan and facts are separate Messages
        plan_text_str = inner_plan.text or ""
        facts_str = getattr(inner_facts, "text", "") or ""
    else:
        # Plain Message — .text contains everything (team + facts + plan).
        # Filter to only bullet lines with bold agent names (**Agent**) so
        # we keep plan steps and drop team descriptions / facts.
        import re
        full_text = getattr(obj, "text", "") or ""
        bold_re = re.compile(r"\*\*\w+\*\*")
        plan_lines = [
            ln for ln in full_text.splitlines() if bold_re.search(ln)
        ]
        plan_text_str = "\n".join(plan_lines)
        facts_str = ""

    mplan: MPlan = PlanToMPlanConverter.convert(
        plan_text=plan_text_str,
        facts=facts_str,
        team=participant_names,
        task=task_text,
    )
    mplan.user_id = user_id
    return mplan


# ---------------------------------------------------------------------------
# WebSocket-based plan approval gate
# ---------------------------------------------------------------------------

async def wait_for_plan_approval(
    m_plan_id: str,
    user_id: str,
) -> Optional[messages.PlanApprovalResponse]:
    """Wait for user approval via WebSocket with timeout handling.

    Args:
        m_plan_id: The ``MPlan.id`` to wait on.
        user_id: The user to send timeout notifications to.

    Returns:
        A ``PlanApprovalResponse`` or ``None`` on timeout/error.
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
                user_id=user_id,
                message_type=messages.WebsocketMessageType.TIMEOUT_NOTIFICATION,
            )
            logger.info(
                "Timeout notification sent to user %s for plan %s",
                user_id,
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

"""
Prompt customization and plan-review helpers for MagenticBuilder workflows.

Provides:
- ``get_magentic_prompt_kwargs()`` — returns a dict of prompt overrides for MagenticBuilder.
- ``convert_plan_review_to_mplan()`` — converts a MagenticPlanReviewRequest into an MPlan.
- ``wait_for_plan_approval()`` — WebSocket-based approval gate with timeout handling.
"""

import asyncio
import json
import logging
import re
from typing import Optional

import models.messages as messages
from agent_framework_orchestrations._magentic import (
    ORCHESTRATOR_FINAL_ANSWER_PROMPT, ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT)
from models.plan_models import MPlan, MStep
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
USER CLARIFICATION POLICY (tool-based — no separate interaction agent):
- Domain agents have MCP tools that tell them EXACTLY what information they need
  (via workflow blueprints). They know better than you what to ask.
- PLAN STRUCTURE: Always start with domain agents. They will call their blueprint
  tools, discover what info is missing, and call their request_user_clarification
  tool directly. The framework pauses automatically when they do this.
- There is NO UserInteractionAgent. Do NOT select any agent named
  UserInteractionAgent — it does not exist as a participant.
- When a domain agent needs user info, it calls its request_user_clarification
  tool. The framework handles the pause/resume cycle automatically. You do NOT
  need to route to any intermediary agent.
- After the framework resumes (user answered), the domain agent receives the
  answer as the tool's return value and continues execution on its own.
- Do NOT fabricate, assume, or hallucinate missing user-specific details.
- MagenticManager NEVER asks questions directly — it only routes tasks to agents.
"""
    else:
        clarification_policy = """
CLARIFYING QUESTIONS POLICY (CRITICAL — ZERO QUESTIONS):
- NEVER ask the user clarifying questions. NEVER pause the workflow to request
  information from the user.
- Agents MUST silently apply sensible defaults for any missing fields and proceed.
- Ask EXACTLY 0 questions. Always proceed with sensible defaults.
"""

    plan_append = """

PLAN RULES:
- Steps are HIGH-LEVEL task assignments — one step per agent. Do NOT prescribe
  sub-tasks, parameters, or data retrieval. Agents discover their own processes.
""" + clarification_policy + """
OUTPUT FORMAT (CRITICAL — use EXACTLY this JSON structure, nothing else):
```json
[
  {{"agent": "AgentName", "action": "high-level task description"}},
  ...
]
```
Use exact agent names from the team list above. Output ONLY the JSON array — no
markdown fences, no commentary before or after.

IMPORTANT: There is NO UserInteractionAgent. Do NOT include any user-interaction
agent in the plan. Domain agents gather user info themselves via their
request_user_clarification tool — the framework pauses automatically when they
call it and resumes when the user answers.

Example plan:
[
  {{"agent": "HRHelperAgent", "action": "execute the onboarding process for the new employee"}},
  {{"agent": "TechnicalSupportAgent", "action": "provision IT resources and accounts for the new employee"}},
  {{"agent": "MagenticManager", "action": "compile a final onboarding summary for the user"}}
]

MagenticManager NEVER asks the user questions directly. MagenticManager NEVER
lists missing information or asks clarifying questions — it ONLY routes tasks.

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
- If an agent produced an image (a markdown image ![alt](url) or an image URL such as one
  under /api/v4/images/), embed it in your answer using markdown image syntax
  ![description](url). NEVER present an image as a bare URL or a plain link.
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
  Do NOT list user-specific information (preferences, choices, dates, names,
  departments, email formats, equipment preferences, etc.).
- Under "EDUCATED GUESSES", do NOT guess user-specific details.
- Do NOT enumerate "information needed from the user" — domain agents will
  determine exactly what they need by consulting their workflow blueprints.
  You do NOT know what questions to ask; only domain agents do.
- Keep facts minimal. The agents are self-directed — they will discover their
  own process via tools.
"""
        kwargs["task_ledger_facts_prompt"] = (
            ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT + facts_append
        )

        progress_append = """

EXECUTION RULES:
- When selecting next_speaker, prefer a work agent that has NOT yet been invoked.
- MagenticManager MUST NOT generate answers, ask questions, or list missing info.
  It only routes tasks to the appropriate agent.
- There is NO UserInteractionAgent. Do NOT select it as next_speaker.
- Domain agents that need user info will call their request_user_clarification
  tool. The framework handles the pause/resume automatically via
  function_approval_request events. You do NOT need to route to any special agent.
- If a domain agent's TEXT response says it needs user information but did NOT call
  its tool, re-invoke the same agent with the message:
  "You MUST call the request_user_clarification tool with your questions.
  Do NOT just list them in text. Call the tool now."

RE-INVOCATION RULE (AFTER USER ANSWERS):
- After the framework resumes from a function_approval_request (the user answered),
  the domain agent receives the answer automatically as the tool's return value.
  You do NOT need to manually relay answers. Just let the workflow continue.
- If for any reason an agent needs to be re-invoked after clarification, prefix
  your message with: "USER ANSWERS RECEIVED — PROCEED TO EXECUTION."

STALL DETECTION OVERRIDE:
- An agent calling request_user_clarification is NOT stalling. The framework
  pauses automatically. Set is_progress_being_made=true and is_in_loop=false.
- Do NOT treat a framework pause as a stall or loop.

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
# JSON plan parsing (for reasoning models like o4-mini)
# ---------------------------------------------------------------------------

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _try_parse_json_plan(
    plan_text: str,
    team: list[str],
    task: str,
    facts: str,
) -> Optional["MPlan"]:
    """Attempt to parse plan_text as a JSON array of steps.

    Expected format:
        [{"agent": "AgentName", "action": "description"}, ...]

    Returns an MPlan if successful, or None to signal fallback to bullet parsing.
    """
    text = plan_text.strip()
    if not text:
        return None

    # Strip markdown code fences if present (```json ... ```)
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json) and last line (```)
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try to extract a JSON array from the text
    if not text.startswith("["):
        m = _JSON_ARRAY_RE.search(text)
        if m:
            text = m.group(0)
        else:
            return None

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, list) or not data:
        return None

    # Build team lookup for case-insensitive matching
    team_lookup = {name.lower(): name for name in team}

    steps: list["MStep"] = []
    for item in data:
        if not isinstance(item, dict):
            return None  # unexpected structure → fallback
        agent_raw = item.get("agent", "")
        action = item.get("action", "")
        if not agent_raw or not action:
            continue
        # Resolve canonical agent name (case-insensitive)
        agent = team_lookup.get(agent_raw.lower(), agent_raw)
        steps.append(MStep(agent=agent, action=action))

    if not steps:
        return None

    mplan = MPlan()
    mplan.team = list(team)
    mplan.user_request = task
    mplan.facts = facts
    mplan.steps = steps
    return mplan


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
        # First try full text (may be JSON from reasoning models).
        # If not JSON, filter to bullet lines with bold agent names.
        full_text = getattr(obj, "text", "") or ""
        plan_text_str = full_text
        facts_str = ""

    logger.warning(
        "[PLAN-DEBUG] plan_text_str for parsing (%d chars):\n%s",
        len(plan_text_str), plan_text_str[:2000],
    )

    # Try JSON parsing first (structured output from reasoning models),
    # fall back to bullet-style regex parsing for backward compatibility.
    mplan = _try_parse_json_plan(plan_text_str, participant_names, task_text, facts_str)
    if mplan is None:
        # For bullet parsing in the plain-message path, filter to only lines
        # containing bold agent names to strip team descriptions / facts.
        if inner_plan is None or not hasattr(inner_plan, "text"):
            bold_re = re.compile(r"\*\*\w+\*\*")
            plan_lines = [
                ln for ln in plan_text_str.splitlines() if bold_re.search(ln)
            ]
            bullet_text = "\n".join(plan_lines)
        else:
            bullet_text = plan_text_str

        mplan = PlanToMPlanConverter.convert(
            plan_text=bullet_text,
            facts=facts_str,
            team=participant_names,
            task=task_text,
        )

    logger.warning(
        "[PLAN-DEBUG] Parsed %d steps from plan text. Steps: %s",
        len(mplan.steps),
        [(s.agent, s.action[:60]) for s in mplan.steps],
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

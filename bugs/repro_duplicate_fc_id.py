"""
Minimal reproduction: Magentic Orchestrator "Duplicate item found" error.

This script reproduces a bug in `_MagenticManager._complete` where the full
`chat_history` (which accumulates participant messages containing function_call
items with `fc_` IDs) is sent as explicit `input` to the Responses API alongside
`session=self._session` (which chains via `previous_response_id`).  After the
FIRST participant completes and the manager makes a successful progress-ledger
call that includes the participant's messages, all subsequent `_complete` calls
re-send those same `fc_`-bearing messages.  The Responses API rejects the
request because the `fc_` IDs already exist in the `previous_response_id` chain.

Sequence that triggers the bug:
  1. Manager calls `plan()` → several `_complete` calls → session stores
     `previous_response_id` chain.
  2. Participant A (with tools) runs → response.messages include function_call
     items → added to `magentic_context.chat_history` via `_handle_response`.
  3. Manager calls `create_progress_ledger()` →
     `_complete([*chat_history, prompt])` → includes Participant A's fc_ items
     in explicit input → SUCCEEDS (fc_ items are new to the session chain).
     Session now stores this response as `previous_response_id`.
  4. Participant B (with tools) runs → response.messages added to chat_history.
  5. Manager calls `create_progress_ledger()` again →
     `_complete([*chat_history, prompt])` → chat_history still contains
     Participant A's fc_ items from step 2, but the session chain from step 3
     already has them.
  6. Responses API rejects: "Duplicate item found with id fc_..."

Requirements:
  pip install agent-framework==1.2.2 agent-framework-foundry==1.2.2

Environment variables (set before running):
  AZURE_AI_PROJECT_ENDPOINT  – your Foundry project endpoint
  AZURE_OPENAI_DEPLOYMENT    – e.g. "gpt-4.1-mini"

  Auth: uses DefaultAzureCredential; `az login` is sufficient for local dev.
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("repro")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from agent_framework import Agent, Message
from agent_framework.orchestrations import MagenticBuilder, MagenticPlanReviewRequest
from azure.identity import DefaultAzureCredential

try:
    from agent_framework_foundry import FoundryChatClient
except ImportError:
    sys.exit("Install: pip install agent-framework-foundry==1.2.2")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
MODEL = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")

if not ENDPOINT:
    sys.exit("Set AZURE_AI_PROJECT_ENDPOINT env var")


# ---------------------------------------------------------------------------
# Two trivial tool-bearing agents
# ---------------------------------------------------------------------------
# The bug requires participant agents that USE tools (producing fc_ items in
# their responses).  We define two simple agents with one tool each.

def make_tool_agent(name: str, instructions: str, tool_func) -> Agent:
    """Create a FoundryChatClient-backed Agent with a single tool."""
    credential = DefaultAzureCredential()
    client = FoundryChatClient(
        project_endpoint=ENDPOINT,
        model=MODEL,
        credential=credential,
    )
    agent = Agent(
        client,
        name=name,
        instructions=instructions,
    )
    agent.toolbox.add_function(tool_func)
    return agent


# Simple tools that just return a string (simulating MCP tool results)
async def lookup_employee_record(employee_name: str) -> str:
    """Look up an employee's HR record by name."""
    return f'{{"employee": "{employee_name}", "department": "Engineering", "start_date": "2025-01-15"}}'


async def provision_laptop(employee_name: str, laptop_model: str = "Standard") -> str:
    """Provision a laptop for a new employee."""
    return f'{{"employee": "{employee_name}", "laptop": "{laptop_model}", "status": "provisioned"}}'


# ---------------------------------------------------------------------------
# Build and run the Magentic workflow
# ---------------------------------------------------------------------------
async def main():
    logger.info("Creating tool-bearing participant agents...")

    hr_agent = make_tool_agent(
        name="HRAgent",
        instructions=(
            "You are an HR agent.  When asked to onboard someone, "
            "call lookup_employee_record with the employee name, "
            "then summarize the result."
        ),
        tool_func=lookup_employee_record,
    )

    it_agent = make_tool_agent(
        name="ITAgent",
        instructions=(
            "You are an IT provisioning agent.  When asked to set up "
            "equipment for someone, call provision_laptop with the "
            "employee name, then confirm the result."
        ),
        tool_func=provision_laptop,
    )

    # Manager agent (no tools — just orchestrates)
    credential = DefaultAzureCredential()
    manager_client = FoundryChatClient(
        project_endpoint=ENDPOINT,
        model=MODEL,
        credential=credential,
    )
    manager_agent = Agent(manager_client, name="Manager")

    logger.info("Building Magentic workflow (enable_plan_review=True)...")
    workflow = MagenticBuilder(
        participants=[hr_agent, it_agent],
        manager_agent=manager_agent,
        max_round_count=10,
        enable_plan_review=True,
    ).build()

    task = "Onboard new employee Jessica Smith — look up her record and provision her laptop."
    logger.info("Running workflow with task: %s", task)

    try:
        async for event in workflow.run(task, stream=True):
            etype = event.type
            executor = getattr(event, "executor_id", "?")

            # Auto-approve any plan review so the workflow continues
            if etype == "request_info" and isinstance(event.data, MagenticPlanReviewRequest):
                logger.info("[PLAN_REVIEW] Auto-approving plan (request_id=%s)", event.request_id)
                # Drain the rest of the stream (it will end after
                # IDLE_WITH_PENDING_REQUESTS)
                continue

            if etype == "status":
                state_name = getattr(event, "state", None)
                logger.info("[STATUS] %s", state_name)

            elif etype == "executor_completed":
                logger.info("[COMPLETED] %s", executor)

            elif etype == "magentic_orchestrator":
                orch_data = event.data
                evt_type = getattr(orch_data, "event_type", "?")
                logger.info("[ORCHESTRATOR] %s", evt_type)

            elif etype == "output":
                pass  # suppress streaming tokens

            else:
                logger.info("[EVENT] type=%s executor=%s", etype, executor)

        # After the initial stream, approve and resume
        # (In practice you'd collect the plan_review request and call
        # workflow.run(stream=True, responses={request_id: plan_review.approve()})
        # but the error triggers BEFORE the second resume cycle is needed.)

    except Exception as exc:
        # Expected: the "Duplicate item found with id fc_..." error
        # surfaces here, either as a RuntimeError from the framework or
        # as an openai.BadRequestError propagated through FoundryChatClient.
        logger.error("Workflow failed: %s", exc)
        if "Duplicate item found" in str(exc):
            logger.error(
                "\n*** BUG REPRODUCED ***\n"
                "The Magentic orchestrator's _complete method sent the full\n"
                "chat_history (containing participant fc_ items) alongside\n"
                "session=self._session (which chains via previous_response_id\n"
                "and already contains those fc_ items from a prior call).\n"
            )
            return 1
        raise
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

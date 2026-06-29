"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import uuid
import re
from typing import List, Optional

import models.messages as messages
from agent_framework import (Agent, AgentResponseUpdate,
                             InMemoryCheckpointStorage, Message,
                             WorkflowRunState)
from agent_framework_foundry import FoundryChatClient
from agent_framework_orchestrations import (MagenticBuilder,
                                            MagenticOrchestratorEvent,
                                            MagenticPlanReviewRequest)
from agents.agent_factory import AgentFactory
from callbacks.response_handlers import (agent_response_callback,
                                         format_agent_display_name,
                                         streaming_agent_response_callback)
from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages import TeamConfiguration
from models.messages import AgentMessageStreaming, WebsocketMessageType
from orchestration.connection_config import (connection_config,
                                             orchestration_config)
from orchestration.plan_review_helpers import (convert_plan_review_to_mplan,
                                               get_magentic_prompt_kwargs,
                                               wait_for_plan_approval)
from patches.tool_history_leak import apply_tool_history_leak_patch
from services.team_service import TeamService

# Apply patch: MAF bug causes tool_call/tool_result messages to leak across
# participants in GroupChat, triggering "No tool call found for call_id" 400 errors.
# See localspec/bugs/framework/F1-tool-history-leak.md
apply_tool_history_leak_patch()

_BARE_IMAGE_URL_RE = re.compile(
   r"(?<![\(\]])"
   r"(?<!\]\()"
   r"("
   # Absolute image URL (any host, or a backend /api/v4/images path)
   r"https?://[^\s)]+?(?:/api/v4/images/[^\s)]+?|[^\s)]+?\.(?:png|jpe?g|gif|webp))"
   # Bare relative backend image path (emitted by the MCP/backend image tools).
   # The (?<![^\s]) guard requires the path to start at whitespace/string-start so
   # it never matches the same substring inside an absolute URL.
   r"|(?<![^\s])/api/v4/images/[^\s)]+?\.(?:png|jpe?g|gif|webp)"
   r")"
   r"(?=[\s)\]]|$)",
   re.IGNORECASE,
)


def _embed_bare_image_urls(text: str) -> str:
    """Wrap bare image URLs in markdown image syntax so the UI renders them inline.

    Skips URLs already inside ``![alt](url)`` or ``[text](url)`` (handled by the
    negative lookbehinds), so it never double-wraps an existing markdown embed.
    """
    if not text:
        return text
    return _BARE_IMAGE_URL_RE.sub(r"![Generated image](\1)", text)


class OrchestrationManager:
    """Manager for handling orchestration logic using agent_framework Magentic workflow."""

    logger = logging.getLogger(f"{__name__}.OrchestrationManager")

    def __init__(self):
        self.user_id: Optional[str] = None
        self.logger = self.__class__.logger

    # ---------------------------
    # Orchestration construction
    # ---------------------------
    @classmethod
    async def init_orchestration(
        cls,
        agents: List,
        team_config: TeamConfiguration,
        memory_store: DatabaseBase,
        user_id: str | None = None,
    ):
        """
        Initialize a Magentic workflow using MagenticBuilder with:
          - enable_plan_review=True for framework-native plan approval
          - Prompt customizations from get_magentic_prompt_kwargs()
          - FoundryChatClient as the underlying chat client
          - Event-based callbacks for streaming and final responses
        """
        if not user_id:
            raise ValueError("user_id is required to initialize orchestration")

        # Get credential from config
        credential = config.get_azure_credential(client_id=config.AZURE_CLIENT_ID)

        # Create Foundry chat client for orchestration
        try:
            chat_client = FoundryChatClient(
                project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                model=team_config.deployment_name,
                credential=credential,
            )

            cls.logger.info(
                "Created FoundryChatClient for orchestration with model '%s' at endpoint '%s'",
                team_config.deployment_name,
                config.AZURE_AI_PROJECT_ENDPOINT,
            )
        except Exception as e:
            cls.logger.error("Failed to create FoundryChatClient: %s", e)
            raise

        # Create a separate client for the orchestrator manager using a
        # reasoning model (o4-mini) — much more reliable at structured JSON
        # output and multi-step routing decisions than standard GPT models.
        orchestrator_model = config.ORCHESTRATOR_MODEL_NAME
        try:
            manager_chat_client = FoundryChatClient(
                project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                model=orchestrator_model,
                credential=credential,
            )
            cls.logger.warning(
                "Manager model: '%s' (participants use '%s')",
                orchestrator_model, team_config.deployment_name,
            )
        except Exception as e:
            cls.logger.warning(
                "Failed to create manager client with '%s', falling back to '%s': %s",
                orchestrator_model, team_config.deployment_name, e,
            )
            manager_chat_client = chat_client

        # Detect whether any agent supports user interaction
        has_user_responses = any(
            getattr(ag, "user_responses", False) for ag in agents
        ) or any(
            getattr(ag, "user_responses", False)
            for ag in getattr(team_config, "agents", [])
        )

        manager_agent = Agent(manager_chat_client, name="MagenticManager")

        # Get prompt customization kwargs
        prompt_kwargs = get_magentic_prompt_kwargs(has_user_responses=has_user_responses)

        cls.logger.info(
            "Building MagenticBuilder for user '%s' with max_rounds=%d, "
            "enable_plan_review=True, has_user_responses=%s",
            user_id, orchestration_config.max_rounds, has_user_responses,
        )

        # Build participant list (unwrap AgentTemplate._agent)
        participant_list = []
        for ag in agents:
            name = getattr(ag, "agent_name", None) or getattr(ag, "name", None)
            if not name:
                name = f"agent_{len(participant_list) + 1}"
            inner = getattr(ag, "_agent", None) or ag
            participant_list.append(inner)
            cls.logger.debug("Added participant '%s'", name)

        # MagenticBuilder config:
        #   enable_plan_review=True  → emits request_info events with MagenticPlanReviewRequest
        #   intermediate_outputs=True → streams AgentResponseUpdate per token
        #   Both request_info event types (plan review + function_approval_request)
        #   pause the workflow in IDLE_WITH_PENDING_REQUESTS until responses are provided.
        storage = InMemoryCheckpointStorage()
        workflow = MagenticBuilder(
            participants=participant_list,
            manager_agent=manager_agent,
            max_round_count=orchestration_config.max_rounds,
            max_stall_count=5,
            checkpoint_storage=storage,
            output_from="all",
            enable_plan_review=True,
            **prompt_kwargs,
        ).build()

        cls.logger.info(
            "Built Magentic workflow with %d participants (plan review enabled)",
            len(participant_list),
        )

        return workflow

    # ---------------------------
    # Orchestration retrieval
    # ---------------------------
    @classmethod
    async def get_current_or_new_orchestration(
        cls,
        user_id: str,
        team_config: TeamConfiguration,
        team_switched: bool,
        team_service: Optional[TeamService] = None,
    ):
        """
        Return an existing workflow for the user or create a new one if:
          - None exists
          - Team switched flag is True

        When a previous workflow has completed (_terminated), we reuse the
        existing agent pool and only rebuild the workflow shell (Option 3).
        Full agent teardown only happens on explicit team switch.
        """
        current = orchestration_config.get_current_orchestration(user_id)
        workflow_terminated = getattr(current, "_terminated", False)

        # Detect a stale cached orchestration: it was built for a different team
        # than the one now selected. Without this, /select_team leaves the prior
        # team's workflow cached and the next run executes the wrong agents until
        # a page refresh rebuilds it. The team_id tag is set on every workflow we
        # build/reset below.
        current_team_id = getattr(current, "_team_id", None)
        team_changed = (
            current is not None and current_team_id != team_config.team_id
        )


        cls.logger.info(
            "get_current_or_new_orchestration: user='%s' selected_team='%s' "
            "cached_team='%s' team_switched=%s team_changed=%s current_is_none=%s",
            user_id, team_config.team_id, current_team_id,
            team_switched, team_changed, current is None,
        )


        # Full rebuild: no workflow exists, team explicitly switched, or the
        # cached workflow belongs to a different team than the selected one.
        needs_full_rebuild = current is None or team_switched or team_changed


        # Lightweight reset: workflow finished but agents are still valid for the
        # same team (a team change always routes to full rebuild above so we
        # never reuse the previous team's agents here).


        needs_workflow_reset = not needs_full_rebuild and workflow_terminated

        if needs_full_rebuild:
            if current is not None:
                cls.logger.info(
                    "Replacing workflow (team switched), closing previous agents for user '%s'",
                    user_id,
                )
                # Close prior agents — only on team switch
                for executor in current.get_executors_list():
                    agent = getattr(executor, "agent", executor)
                    agent_name = getattr(agent, "name", "") or getattr(executor, "id", "")
                    close_coro = getattr(agent, "close", None)
                    if callable(close_coro):
                        try:
                            result = close_coro()
                            if asyncio.iscoroutine(result):
                                await result
                            cls.logger.debug("Closed agent '%s'", agent_name)
                        except Exception as e:
                            cls.logger.error("Error closing agent: %s", e)

            assert team_service is not None, "team_service required for agent creation"
            memory_ctx = team_service.memory_context
            assert memory_ctx is not None, "memory_context required for agent creation"
            factory = AgentFactory(team_service=team_service)
            try:
                agents = await factory.get_agents(
                    user_id=user_id,
                    team_config_input=team_config,
                    memory_store=memory_ctx,
                )
                cls.logger.info("Created %d agents for user '%s'", len(agents), user_id)
            except Exception as e:
                cls.logger.error(
                    "Failed to create agents for user '%s': %s", user_id, e
                )
                print(f"Failed to create agents for user '{user_id}': {e}")
                raise
            try:
                cls.logger.info("Initializing new orchestration for user '%s'", user_id)
                orchestration_config.orchestrations[user_id] = (
                    await cls.init_orchestration(
                        agents, team_config, memory_ctx, user_id
                    )
                )
            except Exception as e:
                cls.logger.error(
                    "Failed to initialize orchestration for user '%s': %s", user_id, e
                )
                print(f"Failed to initialize orchestration for user '{user_id}': {e}")
                raise

        elif needs_workflow_reset:
            cls.logger.info(
                "Workflow completed — resetting workflow shell, reusing agents for user '%s'",
                user_id,
            )
            # Extract existing participant agents from the workflow executors.
            # Skip the MagenticManager — it is recreated by init_orchestration.
            reusable_agents = [
                executor.agent
                for executor in current.get_executors_list()
                if hasattr(executor, "agent")
                and getattr(executor.agent, "name", "") != "MagenticManager"
            ]
            cls.logger.info(
                "Reusing %d agents for new workflow", len(reusable_agents),
            )

            assert team_service is not None, "team_service required for workflow reset"
            reset_memory_ctx = team_service.memory_context
            assert reset_memory_ctx is not None, "memory_context required for workflow reset"
            try:
                orchestration_config.orchestrations[user_id] = (
                    await cls.init_orchestration(
                        reusable_agents, team_config,
                        reset_memory_ctx, user_id,
                    )
                )
            except Exception as e:
                cls.logger.error(
                    "Failed to reset orchestration for user '%s': %s", user_id, e
                )
                print(f"Failed to reset orchestration for user '{user_id}': {e}")
                raise

        return orchestration_config.get_current_orchestration(user_id)

    # ---------------------------
    # Execution
    # ---------------------------
    async def run_orchestration(self, user_id: str, input_task) -> None:
        """
        Execute the Magentic workflow for the provided user and task description.

        Follows the framework's recommended pattern for plan review:
        1. Run the workflow, streaming events until it idles with pending requests.
        2. Collect any ``MagenticPlanReviewRequest`` events emitted during the run.
        3. Present the plan to the user and wait for approval/rejection.
        4. Resume with ``workflow.run(responses={request_id: response})``.
        5. Repeat until the workflow completes with no pending requests.
        """
        job_id = str(uuid.uuid4())
        orchestration_config.set_approval_pending(job_id)
        self.logger.info(
            "Starting orchestration job '%s' for user '%s'", job_id, user_id
        )

        workflow = orchestration_config.get_current_orchestration(user_id)
        if workflow is None:
            raise ValueError("Orchestration not initialized for user.")

        # Build task from input
        task_text = getattr(input_task, "description", str(input_task))
        self.logger.debug("Task: %s", task_text)

        try:
            final_output_ref: list = [None]
            orchestrator_chunks: list[str] = []
            current_streaming_agent_ref: list = [None]

            # Collect participant names for plan conversion
            participant_names = [
                executor.id
                for executor in workflow.get_executors_list()
            ]
            self.logger.info("Participant names: %s", participant_names)

            self.logger.info("Starting workflow execution...")
            plan_already_approved = False

            # Initial run — stream events, collect any pending requests
            pending = await self._process_event_stream(
                workflow.run(task_text, stream=True),
                user_id=user_id,
                final_output_ref=final_output_ref,
                orchestrator_chunks=orchestrator_chunks,
                current_streaming_agent_ref=current_streaming_agent_ref,
            )

            # Resume loop — handle plan reviews and tool approvals until workflow completes
            while pending:
                plan_requests = pending.get("plan_reviews", {})
                tool_approvals = pending.get("tool_approvals", {})

                responses = {}

                # Handle plan reviews (present to user, wait for approval)
                if plan_requests:
                    if plan_already_approved:
                        self.logger.info(
                            "Auto-approving replanned workflow"
                        )
                        plan_responses = {
                            request_id: plan_review.approve()
                            for request_id, plan_review in plan_requests.items()
                        }
                    else:
                        self.logger.info(
                            "Workflow paused with %d plan review request(s)",
                            len(plan_requests),
                        )
                        plan_responses = await self._handle_plan_reviews(
                            plan_requests,
                            participant_names=participant_names,
                            task_text=task_text,
                            user_id=user_id,
                        )
                        if plan_responses is None:
                            raise RuntimeError("Plan execution cancelled by user")

                        plan_already_approved = True

                    responses.update(plan_responses)

                # Handle tool approval requests (clarification from user)
                if tool_approvals:
                    self.logger.info(
                        "Workflow paused with %d tool approval request(s)",
                        len(tool_approvals),
                    )
                    approval_responses = await self._handle_tool_approvals(
                        tool_approvals, user_id=user_id,
                    )
                    responses.update(approval_responses)

                self.logger.info(
                    "Resuming workflow with %d response(s)",
                    len(responses),
                )

                # Resume the workflow with the collected responses
                pending = await self._process_event_stream(
                    workflow.run(stream=True, responses=responses),
                    user_id=user_id,
                    final_output_ref=final_output_ref,
                    orchestrator_chunks=orchestrator_chunks,
                    current_streaming_agent_ref=current_streaming_agent_ref,
                )

            # Use executor_completed Message if available; otherwise fall back to
            # accumulated orchestrator streaming chunks.
            final_text = final_output_ref[0] or "".join(orchestrator_chunks)

            final_text = _embed_bare_image_urls(final_text)

            # Issue 1 diagnostic: confirm the final answer carries a renderable image
            # embed. has_image_markdown tracks TRUE markdown (![]) — the renderable form;
            # has_image_url tracks any image reference, even a bare URL.
            final_source = "executor" if final_output_ref[0] else "chunks"
            has_image_markdown = "![" in final_text
            has_image_url = "/api/v4/images/" in final_text
            self.logger.info(
                "[FINAL-ASSEMBLY] job=%s user=%s source=%s len=%d "
                "has_image_markdown=%s has_image_url=%s",
                job_id, user_id, final_source, len(final_text),
                has_image_markdown, has_image_url,
            )

            # Log results
            self.logger.info("\nAgent responses:")
            self.logger.info(
                "Orchestration completed. Final result length: %d chars",
                len(final_text),
            )
            self.logger.info("\nFinal result:\n%s", final_text)
            self.logger.info("=" * 50)

            # Send final result via WebSocket
            await connection_config.send_status_update_async(
                {
                    "type": WebsocketMessageType.FINAL_RESULT_MESSAGE,
                    "data": {
                        "content": final_text,
                        "status": "completed",
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                },
                user_id,
                message_type=WebsocketMessageType.FINAL_RESULT_MESSAGE,
            )
            self.logger.info("Final result sent via WebSocket to user '%s'", user_id)

        except Exception as e:
            # Error handling
            self.logger.error("Unexpected orchestration error: %s", e, exc_info=True)
            self.logger.error("Error type: %s", type(e).__name__)
            if hasattr(e, "__dict__"):
                self.logger.error("Error attributes: %s", e.__dict__)
            self.logger.info("=" * 50)

            # Send error status to user
            try:
                await connection_config.send_status_update_async(
                    {
                        "type": WebsocketMessageType.FINAL_RESULT_MESSAGE,
                        "data": {
                            "content": f"Error during orchestration: {str(e)}",
                            "status": "error",
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                    },
                    user_id,
                    message_type=WebsocketMessageType.FINAL_RESULT_MESSAGE,
                )
            except Exception as send_error:
                self.logger.error("Failed to send error status: %s", send_error)
            raise

        finally:
            # Clean up MCP connections to avoid noisy cross-task
            # RuntimeError from anyio when async generators are GC'd.
            await self._cleanup_workflow_mcp(user_id)

    async def _cleanup_workflow_mcp(self, user_id: str) -> None:
        """Close MCP async-generator contexts for the finished workflow."""
        workflow = orchestration_config.get_current_orchestration(user_id)
        if workflow is None:
            return

        # Mark workflow as terminated so next request creates a fresh one
        workflow._terminated = True

    # ---------------------------
    # Plan review handling
    # ---------------------------
    async def _handle_plan_reviews(
        self,
        plan_requests: dict[str, "MagenticPlanReviewRequest"],
        *,
        participant_names: list[str],
        task_text: str,
        user_id: str,
    ) -> dict | None:
        """Present collected plan review requests to the user and gather responses.

        Returns:
            A ``{request_id: MagenticPlanReviewResponse}`` dict if at least one
            plan was approved, or ``None`` if all were rejected/timed out.
        """
        responses = {}

        for request_id, plan_review in plan_requests.items():
            self.logger.info(
                "[PLAN_REVIEW] Presenting plan to user (request_id=%s)", request_id
            )

            # Convert to MPlan for frontend display
            mplan = convert_plan_review_to_mplan(
                plan_review,
                participant_names=participant_names,
                task_text=task_text,
                user_id=user_id,
            )

            # Store plan
            try:
                orchestration_config.plans[mplan.id] = mplan
            except Exception as e:
                self.logger.error("Error storing plan: %s", e)

            # Send approval request to frontend via WebSocket
            approval_message = messages.PlanApprovalRequest(
                plan=mplan,
                status="PENDING_APPROVAL",  # type: ignore[arg-type]
                context={"task": task_text},
            )
            await connection_config.send_status_update_async(
                message=approval_message,
                user_id=user_id,
                message_type=WebsocketMessageType.PLAN_APPROVAL_REQUEST,
            )

            # Wait for user response
            approval_response = await wait_for_plan_approval(mplan.id, user_id)

            if approval_response and approval_response.approved:
                self.logger.info("Plan approved (request_id=%s)", request_id)
                responses[request_id] = plan_review.approve()
            else:
                self.logger.info("Plan rejected (request_id=%s)", request_id)
                await connection_config.send_status_update_async(
                    {
                        "type": WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
                        "data": approval_response,
                    },
                    user_id=user_id,
                    message_type=WebsocketMessageType.PLAN_APPROVAL_RESPONSE,
                )
                return None

        return responses if responses else None

    async def _handle_tool_approvals(
        self,
        tool_approvals: dict[str, object],
        *,
        user_id: str,
    ) -> dict:
        """Handle pending tool approval requests (HITL clarification).

        For each approval request:
        1. Extract the questions from the function call arguments.
        2. Send a USER_CLARIFICATION_REQUEST to the frontend via WebSocket.
        3. Wait for the user's answer via the clarification event infrastructure.
        4. Store the answer so the tool body can read it after approval.
        5. Approve the tool call and return the response.

        Returns:
            A ``{request_id: approval_response}`` dict.
        """
        import json
        import threading

        from tools.clarification_tool import store_answer

        responses = {}

        for request_id, content in tool_approvals.items():
            # Extract the questions from function call arguments
            fn_call = content.function_call  # type: ignore[attr-defined]
            fn_args_raw = getattr(fn_call, "arguments", None) or "{}"
            try:
                fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
            except (json.JSONDecodeError, TypeError):
                fn_args = {}
            questions = fn_args.get("questions", "The agent needs clarification.")

            self.logger.info(
                "[TOOL_APPROVAL] Sending clarification to user (request_id=%s): %s",
                request_id, questions[:120],
            )

            # Register pending clarification
            orchestration_config.set_clarification_pending(request_id)

            # Send to frontend via WebSocket
            await connection_config.send_status_update_async(
                {
                    "type": WebsocketMessageType.USER_CLARIFICATION_REQUEST,
                    "data": {
                        "request_id": request_id,
                        "questions": questions,
                        "agent_name": getattr(fn_call, "name", "agent"),
                    },
                },
                user_id=user_id,
                message_type=WebsocketMessageType.USER_CLARIFICATION_REQUEST,
            )

            # Wait for user's answer (uses existing async event infrastructure)
            try:
                answer = await orchestration_config.wait_for_clarification(
                    request_id, timeout=300.0,
                )
            except asyncio.TimeoutError:
                self.logger.warning(
                    "[TOOL_APPROVAL] Timeout waiting for user answer (request_id=%s)",
                    request_id,
                )
                answer = "No response received from user (timeout)."
            except Exception as e:
                self.logger.error(
                    "[TOOL_APPROVAL] Error waiting for answer (request_id=%s): %s",
                    request_id, e,
                )
                answer = f"Error receiving response: {e}"

            self.logger.info(
                "[TOOL_APPROVAL] Received answer (request_id=%s): %s",
                request_id, answer[:120],
            )

            # Store the answer so the tool body can retrieve it after approval.
            # Store under request_id and also under a thread-local key that
            # the tool body uses as its primary lookup.
            store_answer(request_id, answer)
            thread_key = f"_clarification_{threading.current_thread().ident}"
            store_answer(thread_key, answer)

            # Approve the tool call
            approval = content.to_function_approval_response(approved=True)  # type: ignore[attr-defined]
            responses[request_id] = approval

        return responses

    async def _process_event_stream(
        self,
        stream,
        *,
        user_id: str,
        final_output_ref: list,
        orchestrator_chunks: list[str],
        current_streaming_agent_ref: list,
    ) -> dict | None:
        """Process a workflow event stream, collecting pending requests.

        Follows the framework sample pattern: consume all events, collect any
        ``MagenticPlanReviewRequest`` objects and ``function_approval_request``
        events, and break when the workflow reaches
        ``IDLE_WITH_PENDING_REQUESTS``. The caller is responsible for
        presenting plans/questions to the user and resuming the workflow.

        Returns:
            A dict with ``plan_reviews`` and/or ``tool_approvals`` keys if any
            were requested, or ``None`` if the stream completed normally.
        """
        plan_requests: dict[str, MagenticPlanReviewRequest] = {}
        tool_approvals: dict[str, object] = {}  # request_id -> event.data (Content)

        async for event in stream:
            try:
                data_type = type(event.data).__name__ if event.data is not None else "None"
                executor = getattr(event, "executor_id", None) or "?"
                self.logger.debug(
                    "[EVENT] type=%s  data_type=%s  executor=%s",
                    event.type, data_type, executor,
                )

                # -------------------------------------------------------
                # MAF request_info event #1: Plan review
                # Emitted by enable_plan_review=True when the orchestrator
                # produces a task plan. We collect it and present to the user.
                # -------------------------------------------------------
                if event.type == "request_info" and isinstance(event.data, MagenticPlanReviewRequest):
                    request_id = event.request_id
                    self.logger.info(
                        "[PLAN_REVIEW] Collected plan review request (request_id=%s)",
                        request_id,
                    )
                    plan_requests[request_id] = event.data

                # -------------------------------------------------------
                # MAF request_info event #2: Function approval (HITL)
                # Emitted by @tool(approval_mode=\"always_require\") when an
                # agent calls request_user_clarification. The framework pauses
                # and waits for us to approve/reject after getting the user's answer.
                # -------------------------------------------------------
                elif (
                    event.type == "request_info"
                    and getattr(event.data, "type", None) == "function_approval_request"
                ):
                    request_id = event.request_id
                    fn_name = (
                        getattr(event.data.function_call, "name", None)
                        if event.data.function_call else "?"
                    )
                    self.logger.info(
                        "[TOOL_APPROVAL] Collected approval request (tool=%s, request_id=%s)",
                        fn_name, request_id,
                    )
                    tool_approvals[request_id] = event.data

                # -------------------------------------------------------
                # Status — log when idle with pending requests
                # (stream will end naturally; do NOT break)
                # -------------------------------------------------------
                elif event.type == "status" and event.state is WorkflowRunState.IDLE_WITH_PENDING_REQUESTS:
                    self.logger.info(
                        "[STATUS] Workflow idle with %d plan review(s) + %d tool approval(s)",
                        len(plan_requests), len(tool_approvals),
                    )

                # Magentic orchestrator events (plan created, replanned, progress ledger)
                elif event.type == "magentic_orchestrator":
                    orch_event: MagenticOrchestratorEvent = event.data
                    self.logger.info(
                        "[ORCHESTRATOR:%s]", orch_event.event_type.value
                    )

                # Streaming output
                elif event.type == "output":
                    executor = event.executor_id or "unknown"
                    output_data = event.data

                    if isinstance(output_data, AgentResponseUpdate):
                        if executor == "magentic_orchestrator" and output_data.text:
                            orchestrator_chunks.append(output_data.text)

                        if (
                            executor != "magentic_orchestrator"
                            and executor != current_streaming_agent_ref[0]
                        ):
                            current_streaming_agent_ref[0] = executor
                            display_name = format_agent_display_name(executor)
                            header_text = f"\n\n---\n### {display_name}\n\n"
                            try:
                                await connection_config.send_status_update_async(
                                    AgentMessageStreaming(
                                        agent_name=display_name,
                                        content=header_text,
                                        is_final=False,
                                    ),
                                    user_id,
                                    message_type=WebsocketMessageType.AGENT_MESSAGE_STREAMING,
                                )
                            except Exception as cb_err:
                                self.logger.error(
                                    "Error sending agent header for %s: %s",
                                    executor, cb_err,
                                )

                        if executor != "magentic_orchestrator":
                            try:
                                await streaming_agent_response_callback(
                                    executor, output_data, False, user_id,
                                )
                            except Exception as cb_err:
                                self.logger.error(
                                    "Error in streaming callback for %s: %s",
                                    executor, cb_err,
                                )

                # Executor completed
                elif (
                    event.type == "executor_completed"
                    and isinstance(event.data, list)
                    and event.executor_id
                ):
                    agent_id = event.executor_id
                    if agent_id == "magentic_orchestrator":
                        for msg in event.data:
                            if isinstance(msg, Message) and msg.text:
                                final_output_ref[0] = msg.text
                    else:
                        for msg in event.data:
                            if isinstance(msg, Message) and msg.text:
                                try:
                                    agent_response_callback(
                                        agent_id, msg, user_id
                                    )
                                except Exception as cb_err:
                                    self.logger.error(
                                        "Error in agent callback for %s: %s",
                                        agent_id, cb_err,
                                    )

            except Exception as e:
                if "cancelled by user" in str(e):
                    raise
                self.logger.error(
                    "Error processing event type=%s: %s",
                    getattr(event, "type", "?"), e,
                    exc_info=True,
                )

        # Stream fully consumed or broke on IDLE_WITH_PENDING_REQUESTS
        if plan_requests or tool_approvals:
            result = {}
            if plan_requests:
                result["plan_reviews"] = plan_requests
            if tool_approvals:
                result["tool_approvals"] = tool_approvals
            return result
        return None
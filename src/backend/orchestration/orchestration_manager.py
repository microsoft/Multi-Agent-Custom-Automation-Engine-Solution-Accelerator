"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import uuid
from contextlib import AsyncExitStack
from typing import List, Optional

import models.messages as messages
from agent_framework import (Agent, AgentResponse, AgentResponseUpdate,
                             InMemoryCheckpointStorage, MCPStreamableHTTPTool,
                             Message, WorkflowEvent, WorkflowRunState)
from agent_framework.orchestrations import (MagenticBuilder,
                                            MagenticOrchestratorEvent,
                                            MagenticOrchestratorEventType,
                                            MagenticPlanReviewRequest)
# agent_framework imports
from agent_framework_foundry import FoundryChatClient
from agents.agent_factory import AgentFactory
from callbacks.response_handlers import (agent_response_callback,
                                         streaming_agent_response_callback)
from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages import TeamConfiguration
from config.mcp_config import MCPConfig
from models.messages import AgentMessageStreaming, WebsocketMessageType
from orchestration.connection_config import (connection_config,
                                             orchestration_config)
from orchestration.plan_review_helpers import (convert_plan_review_to_mplan,
                                               get_magentic_prompt_kwargs,
                                               wait_for_plan_approval)
from orchestration.user_interaction_agent import create_user_interaction_agent
from patches.tool_history_leak import apply_tool_history_leak_patch
from services.team_service import TeamService

# Apply framework bug workaround (tool-call history leaks between participants)
apply_tool_history_leak_patch()


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

        # If user interaction is enabled, create UserInteractionAgent as a
        # participant.  This agent has the ask_user MCP tool and acts as the
        # proxy for all user-facing questions.
        user_interaction_ctx = None
        if has_user_responses and user_id:
            ui_agent, user_interaction_ctx = await create_user_interaction_agent(
                chat_client=chat_client,
                user_id=user_id,
            )
            participant_list.append(ui_agent)
            cls.logger.info("Added UserInteractionAgent as participant")

        # Assemble and build the Magentic workflow using the standard
        # manager_agent= path with prompt overrides — no subclassing.
        storage = InMemoryCheckpointStorage()
        workflow = MagenticBuilder(
            participants=participant_list,
            manager_agent=manager_agent,
            max_round_count=orchestration_config.max_rounds,
            max_stall_count=5,
            checkpoint_storage=storage,
            intermediate_outputs=True,
            enable_plan_review=True,
            **prompt_kwargs,
        ).build()

        cls.logger.info(
            "Built Magentic workflow with %d participants (plan review enabled)",
            len(participant_list),
        )

        # Attach the MCP context manager so it can be cleaned up on workflow replace
        workflow._user_interaction_ctx = user_interaction_ctx

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
        team_service: TeamService = None,
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

        # Full rebuild: no workflow exists or team explicitly changed
        needs_full_rebuild = current is None or team_switched

        # Lightweight reset: workflow finished but agents are still valid
        needs_workflow_reset = not needs_full_rebuild and workflow_terminated

        if needs_full_rebuild:
            if current is not None:
                cls.logger.info(
                    "Replacing workflow (team switched), closing previous agents for user '%s'",
                    user_id,
                )
                # Close the UserInteractionAgent MCP context stack
                ui_ctx = getattr(current, "_user_interaction_ctx", None)
                if ui_ctx is not None:
                    try:
                        await ui_ctx.aclose()
                        cls.logger.debug("Closed UserInteractionAgent MCP context")
                    except (RuntimeError, Exception) as e:
                        cls.logger.debug("UI agent MCP cleanup (benign): %s", e)

                # Close prior agents — only on team switch
                for executor in current.get_executors_list():
                    agent = getattr(executor, "agent", executor)
                    agent_name = getattr(agent, "name", "") or getattr(executor, "id", "")
                    close_coro = getattr(agent, "close", None)
                    if callable(close_coro):
                        try:
                            await close_coro()
                            cls.logger.debug("Closed agent '%s'", agent_name)
                        except Exception as e:
                            cls.logger.error("Error closing agent: %s", e)

            factory = AgentFactory(team_service=team_service)
            try:
                agents = await factory.get_agents(
                    user_id=user_id,
                    team_config_input=team_config,
                    memory_store=team_service.memory_context,
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
                        agents, team_config, team_service.memory_context, user_id
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
            # Skip the MagenticManager (orchestrator) and UserInteractionAgent —
            # both will be recreated by init_orchestration.
            reusable_agents = [
                executor.agent
                for executor in current.get_executors_list()
                if hasattr(executor, "agent")
                and not getattr(executor.agent, "name", "").startswith("UserInteraction")
            ]
            cls.logger.info(
                "Reusing %d agents for new workflow", len(reusable_agents),
            )

            try:
                orchestration_config.orchestrations[user_id] = (
                    await cls.init_orchestration(
                        reusable_agents, team_config,
                        team_service.memory_context, user_id,
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

            # Initial run — stream events, collect any plan review requests
            plan_requests = await self._process_event_stream(
                workflow.run(task_text, stream=True),
                user_id=user_id,
                final_output_ref=final_output_ref,
                orchestrator_chunks=orchestrator_chunks,
                current_streaming_agent_ref=current_streaming_agent_ref,
            )

            # Resume loop — handle plan reviews until workflow completes
            while plan_requests:
                self.logger.info(
                    "Workflow paused with %d plan review request(s)",
                    len(plan_requests),
                )

                # Present each plan review to the user and collect responses
                responses = await self._handle_plan_reviews(
                    plan_requests,
                    participant_names=participant_names,
                    task_text=task_text,
                    user_id=user_id,
                )

                if responses is None:
                    # All reviews were rejected or timed out
                    raise Exception("Plan execution cancelled by user")

                self.logger.info(
                    "Resuming workflow with %d approved response(s)",
                    len(responses),
                )

                # Resume the workflow with the collected responses
                plan_requests = await self._process_event_stream(
                    workflow.run(stream=True, responses=responses),
                    user_id=user_id,
                    final_output_ref=final_output_ref,
                    orchestrator_chunks=orchestrator_chunks,
                    current_streaming_agent_ref=current_streaming_agent_ref,
                )

            # Use executor_completed Message if available; otherwise fall back to
            # accumulated orchestrator streaming chunks.
            final_text = final_output_ref[0] or "".join(orchestrator_chunks)

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

        # Close UserInteractionAgent MCP context
        ui_ctx = getattr(workflow, "_user_interaction_ctx", None)
        if ui_ctx is not None:
            try:
                await ui_ctx.aclose()
                self.logger.debug("Closed UserInteractionAgent MCP context")
            except (RuntimeError, Exception) as e:
                self.logger.debug("UserInteractionAgent MCP cleanup (benign): %s", e)
            workflow._user_interaction_ctx = None

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
                status="PENDING_APPROVAL",
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

    async def _process_event_stream(
        self,
        stream,
        *,
        user_id: str,
        final_output_ref: list,
        orchestrator_chunks: list[str],
        current_streaming_agent_ref: list,
    ) -> dict[str, "MagenticPlanReviewRequest"] | None:
        """Process a workflow event stream, collecting plan review requests.

        Follows the framework sample pattern: consume all events, collect any
        ``MagenticPlanReviewRequest`` objects, and break when the workflow
        reaches ``IDLE_WITH_PENDING_REQUESTS``. The caller is responsible for
        presenting plans to the user and resuming the workflow.

        Returns:
            A ``{request_id: MagenticPlanReviewRequest}`` dict if plan reviews
            were requested, or ``None`` if the stream completed normally.
        """
        plan_requests: dict[str, MagenticPlanReviewRequest] = {}

        async for event in stream:
            try:
                data_type = type(event.data).__name__ if event.data is not None else "None"
                executor = getattr(event, "executor_id", None) or "?"
                self.logger.debug(
                    "[EVENT] type=%s  data_type=%s  executor=%s",
                    event.type, data_type, executor,
                )

                # -------------------------------------------------------
                # Plan review request — collect, don't block
                # -------------------------------------------------------
                if event.type == "request_info" and isinstance(event.data, MagenticPlanReviewRequest):
                    request_id = event.request_id
                    self.logger.info(
                        "[PLAN_REVIEW] Collected plan review request (request_id=%s)",
                        request_id,
                    )
                    plan_requests[request_id] = event.data

                # -------------------------------------------------------
                # Status — log when idle with pending requests
                # (stream will end naturally; do NOT break)
                # -------------------------------------------------------
                elif event.type == "status" and event.state is WorkflowRunState.IDLE_WITH_PENDING_REQUESTS:
                    self.logger.info(
                        "[STATUS] Workflow idle with %d pending request(s)",
                        len(plan_requests),
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
                            display_name = executor.replace("_", " ")
                            header_text = f"\n\n---\n### {display_name}\n\n"
                            try:
                                await connection_config.send_status_update_async(
                                    AgentMessageStreaming(
                                        agent_name=executor,
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
        return plan_requests if plan_requests else None

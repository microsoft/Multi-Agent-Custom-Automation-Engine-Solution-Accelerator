"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import inspect
import logging
import re
import uuid
from typing import List, Optional

# agent_framework imports
from agent_framework_azure_ai import AzureAIClient
from agent_framework import (
    Agent,
    AgentResponseUpdate,
    ChatOptions,
    Message,
    InMemoryCheckpointStorage,
)
from agent_framework_orchestrations import MagenticBuilder
from agent_framework_orchestrations._base_group_chat_orchestrator import (
    GroupChatRequestSentEvent,
    GroupChatResponseReceivedEvent,
)
from agent_framework_orchestrations._magentic import (
    MagenticProgressLedger,
)

from common.config.app_config import config
from common.models.messages_af import PlanStatus, TeamConfiguration

from common.database.database_factory import DatabaseFactory
from common.database.database_base import DatabaseBase

from v4.common.services.team_service import TeamService
import time as _time
from v4.callbacks.response_handlers import (
    streaming_agent_response_callback,
)
from v4.config.settings import connection_config, orchestration_config
from v4.models.messages import WebsocketMessageType
from v4.orchestration.human_approval_manager import HumanApprovalMagenticManager
from v4.magentic_agents.magentic_agent_factory import MagenticAgentFactory


class OrchestrationManager:
    """Manager for handling orchestration logic using agent_framework Magentic workflow."""

    logger = logging.getLogger(f"{__name__}.OrchestrationManager")

    def __init__(self):
        self.user_id: Optional[str] = None
        self.logger = self.__class__.logger

    def _extract_response_text(self, data) -> str:
        """
        Extract text content from various agent_framework response types.

        Handles:
        - Message: Extract .text
        - AgentResponse: Extract .text
        - AgentExecutorResponse: Extract from agent_response.text or full_conversation[-1].text
        - List of any of the above
        """
        if data is None:
            return ""

        # Direct Message
        if isinstance(data, Message):
            return data.text or ""

        # Has .text attribute directly (AgentResponse, etc.)
        if hasattr(data, "text") and data.text:
            return data.text

        # AgentExecutorResponse - has agent_response and full_conversation
        if hasattr(data, "agent_response"):
            # Try to get text from agent_response first
            agent_resp = data.agent_response
            if agent_resp and hasattr(agent_resp, "text") and agent_resp.text:
                return agent_resp.text
            # Fallback to last message in full_conversation
            if hasattr(data, "full_conversation") and data.full_conversation:
                last_msg = data.full_conversation[-1]
                if isinstance(last_msg, Message) and last_msg.text:
                    return last_msg.text

        # List of items - could be AgentExecutorResponse, ChatMessage, etc.
        if isinstance(data, list) and len(data) > 0:
            texts = []
            for item in data:
                # Recursively extract from each item
                item_text = self._extract_response_text(item)
                if item_text:
                    texts.append(item_text)
            if texts:
                # Return the last non-empty response (most recent)
                return texts[-1]

        return ""

    @staticmethod
    def _plan_status_for_final_result(final_status: str) -> PlanStatus:
        """Map WebSocket final-result status strings to persisted plan statuses."""
        raw_status = (
            final_status.value if hasattr(final_status, "value") else final_status
        )
        normalized_status = str(raw_status or "").lower()
        if normalized_status == "completed":
            return PlanStatus.completed
        if normalized_status in {"canceled", "cancelled"}:
            return PlanStatus.canceled
        return PlanStatus.failed

    @classmethod
    async def _persist_terminal_plan_status(
        cls, user_id: str, plan_id: Optional[str], final_status: str, content: str
    ) -> None:
        """Persist terminal orchestration state before the UI receives a final result."""
        if not plan_id:
            cls.logger.warning(
                "Unable to persist terminal orchestration status %s; no plan_id was provided",
                final_status,
            )
            return

        memory_store = None
        try:
            memory_store = await DatabaseFactory.get_database(
                user_id=user_id, force_new=True
            )
            plan = await memory_store.get_plan_by_plan_id(plan_id=plan_id)
            if not plan:
                cls.logger.warning(
                    "Unable to persist terminal orchestration status %s; plan %s was not found",
                    final_status,
                    plan_id,
                )
                return

            plan.overall_status = cls._plan_status_for_final_result(final_status)
            plan.streaming_message = content or (
                f"Plan ended with terminal status: {final_status}"
            )
            await memory_store.update_plan(plan)
            cls.logger.info(
                "Persisted terminal orchestration status %s for plan %s",
                plan.overall_status,
                plan_id,
            )
        except Exception:
            cls.logger.exception(
                "Failed to persist terminal orchestration status %s for plan %s",
                final_status,
                plan_id,
            )
        finally:
            if memory_store:
                try:
                    await memory_store.close()
                except Exception:
                    cls.logger.exception(
                        "Failed to close terminal-status database client"
                    )

    @staticmethod
    def _get_manager_plan_id(manager) -> Optional[str]:
        manager_plan_id = getattr(manager, "persisted_plan_id", None)
        if manager_plan_id:
            return manager_plan_id

        magentic_plan = getattr(manager, "magentic_plan", None)
        if magentic_plan:
            return getattr(magentic_plan, "plan_id", None)

        return None

    @staticmethod
    def _get_workflow_terminal_manager(workflow):
        if workflow is None:
            return None
        return getattr(workflow, "__dict__", {}).get("_terminal_manager")

    @classmethod
    def _workflow_has_plan_scope(cls, workflow) -> bool:
        manager = cls._get_workflow_terminal_manager(workflow)
        return cls._get_manager_plan_id(manager) is not None

    @classmethod
    async def _close_workflow_participants(cls, workflow, reason: str) -> None:
        """Close participant resources for workflows that are no longer in use."""
        workflow_state = getattr(workflow, "__dict__", {})
        if workflow_state.get("_resources_closed"):
            return

        cleanup_handles = list(workflow_state.get("_cleanup_handles") or [])
        if not cleanup_handles:
            participants = workflow_state.get("_participants", {}) or {}
            cleanup_handles = list(participants.values())

        seen_handle_ids = set()
        for handle in cleanup_handles:
            if handle is None or id(handle) in seen_handle_ids:
                continue
            seen_handle_ids.add(id(handle))

            handle_name = getattr(
                handle, "agent_name", getattr(handle, "name", type(handle).__name__)
            )
            if handle_name == "ProxyAgent":
                continue

            close_fn = getattr(handle, "close", None)
            if callable(close_fn):
                try:
                    close_result = close_fn()
                    if inspect.isawaitable(close_result):
                        await close_result
                    cls.logger.debug("Closed resource '%s' (%s)", handle_name, reason)
                except Exception as e:
                    cls.logger.error("Error closing resource '%s': %s", handle_name, e)

        try:
            workflow._resources_closed = True
        except Exception:
            cls.logger.debug("Unable to mark workflow resources closed", exc_info=True)

    @classmethod
    def _get_non_completed_terminal_manager(cls, workflow, plan_id: Optional[str]):
        manager = cls._get_workflow_terminal_manager(workflow)
        has_terminal_result = getattr(
            manager, "has_emitted_non_completed_terminal_result", None
        )
        if (
            not manager
            or not callable(has_terminal_result)
            or not has_terminal_result()
        ):
            return None

        manager_plan_id = cls._get_manager_plan_id(manager)
        if plan_id and manager_plan_id == plan_id:
            return manager

        cls.logger.info(
            "Ignoring terminal final result state for plan '%s' from manager scoped to plan '%s'",
            plan_id,
            manager_plan_id,
        )
        return None

    @classmethod
    async def _validate_explicit_workflow_plan(
        cls, user_id: str, plan_id: Optional[str], workflow
    ) -> None:
        if not plan_id:
            return

        manager = cls._get_workflow_terminal_manager(workflow)
        manager_plan_id = getattr(manager, "persisted_plan_id", None)
        if manager_plan_id == plan_id:
            return

        raise ValueError(
            "Explicit orchestration workflow plan mismatch: "
            f"expected plan '{plan_id}', got '{manager_plan_id or 'unknown'}' "
            f"for user '{user_id}'"
        )

    async def _send_orchestration_error(
        self, user_id: str, plan_id: Optional[str], error: Exception, workflow=None
    ) -> None:
        """Persist and notify the UI about an orchestration failure."""
        terminal_manager = self._get_non_completed_terminal_manager(workflow, plan_id)
        if terminal_manager:
            self.logger.info(
                "Skipping error final result for user '%s' because terminal status '%s' was already sent",
                user_id,
                terminal_manager.terminal_final_result_status,
            )
            return

        error_content = f"Error during orchestration: {str(error)}"
        await self._persist_terminal_plan_status(
            user_id, plan_id, "error", error_content
        )
        try:
            await connection_config.send_status_update_async(
                {
                    "type": WebsocketMessageType.FINAL_RESULT_MESSAGE,
                    "data": {
                        "content": error_content,
                        "status": "error",
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                },
                user_id,
                message_type=WebsocketMessageType.FINAL_RESULT_MESSAGE,
            )
        except Exception as send_error:
            self.logger.error("Failed to send error status: %s", send_error)

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
        plan_id: Optional[str] = None,
    ):
        """
        Initialize a Magentic workflow with:
          - Provided agents (participants)
          - HumanApprovalMagenticManager as orchestrator manager
          - AzureAIClient as the underlying chat client
          - Event-based callbacks for streaming and final responses
        - Uses same deployment, endpoint, and credentials
        - Applies same execution settings (temperature, max_tokens)
        - Maintains same human approval workflow
        """
        if not user_id:
            raise ValueError("user_id is required to initialize orchestration")

        # Get credential from config (same as old version)
        credential = config.get_azure_credential(client_id=config.AZURE_CLIENT_ID)

        # Create Azure AI Agent client for orchestration using config
        # This replaces AzureChatCompletion from SK
        # Sanitize agent name: must start/end with alphanumeric, only hyphens allowed, max 63 chars
        raw_name = team_config.name if team_config.name else "OrchestratorAgent"
        # Replace spaces and invalid chars with hyphens, strip leading/trailing hyphens
        sanitized_name = re.sub(r'[^a-zA-Z0-9-]', '-', raw_name)
        sanitized_name = re.sub(r'-+', '-', sanitized_name)  # Collapse multiple hyphens
        sanitized_name = sanitized_name.strip('-')[:63]  # Trim and limit length
        agent_name = sanitized_name if sanitized_name else "OrchestratorAgent"

        try:
            # Create the chat client (AzureAIClient)
            chat_client = AzureAIClient(
                project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                model_deployment_name=team_config.deployment_name,
                agent_name=agent_name,
                credential=credential,
            )

            # New API: Create an Agent to wrap the chat client for the manager
            manager_agent = Agent(
                client=chat_client,
                name="MagenticManager",
                default_options=ChatOptions(store=False),  # Client-managed conversation to avoid stale tool call IDs across rounds
            )

            cls.logger.info(
                "Created AzureAIClient and manager Agent for orchestration with model '%s' at endpoint '%s'",
                team_config.deployment_name,
                config.AZURE_AI_PROJECT_ENDPOINT,
            )
        except Exception as e:
            cls.logger.error("Failed to create AzureAIClient: %s", e)
            raise

        # Create HumanApprovalMagenticManager with the manager agent
        # New API: StandardMagenticManager takes agent as first positional argument
        try:
            manager = HumanApprovalMagenticManager(
                user_id=user_id,
                agent=manager_agent,  # New API: pass agent instead of chat_client
                max_round_count=orchestration_config.max_rounds,
                max_stall_count=3,
                max_reset_count=2,
                terminal_status_persistor=cls._persist_terminal_plan_status,
                persisted_plan_id=plan_id,
            )
            cls.logger.info(
                "Created HumanApprovalMagenticManager for user '%s' with max_rounds=%d",
                user_id,
                orchestration_config.max_rounds,
            )
        except Exception as e:
            cls.logger.error("Failed to create manager: %s", e)
            raise

        # Build participant map: use each agent's name as key
        participants = {}
        for ag in agents:
            name = getattr(ag, "agent_name", None) or getattr(ag, "name", None)
            if not name:
                name = f"agent_{len(participants) + 1}"

            # Extract the inner Agent for wrapper templates
            # FoundryAgentTemplate wrap an Agent in self._agent
            # ProxyAgent directly extends BaseAgent and can be used as-is
            if hasattr(ag, "_agent") and ag._agent is not None:
                # This is a wrapper (FoundryAgentTemplate)
                # Use the inner Agent which implements AgentProtocol
                participants[name] = ag._agent
                cls.logger.debug("Added participant '%s' (extracted inner agent)", name)
            else:
                # This is already an agent (like ProxyAgent extending BaseAgent)
                participants[name] = ag
                cls.logger.debug("Added participant '%s'", name)

        # Assemble workflow with callback
        storage = InMemoryCheckpointStorage()

        # New SDK: participants() accepts a Sequence (list) of agents
        # The orchestrator uses agent.name to identify them
        participant_list = list(participants.values())
        cls.logger.info("Participants for workflow: %s", list(participants.keys()))

        builder = MagenticBuilder(
            participants=participant_list,
            manager=manager,
            checkpoint_storage=storage,
            max_round_count=orchestration_config.max_rounds,
            max_stall_count=3,  # Allow up to 3 stalled rounds before stopping; set to 0 to strictly prevent re-calling stalled agents.
            intermediate_outputs=True,  # Required: yield agent streaming output events, not just orchestrator output
        )

        # Build workflow
        workflow = builder.build()
        workflow._terminal_manager = manager
        workflow._cleanup_handles = [*agents, manager, manager_agent, chat_client]
        cls.logger.info(
            "Built Magentic workflow with %d participants and event callbacks",
            len(participants),
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
        team_service: TeamService = None,
        force_rebuild: bool = False,
        plan_id: Optional[str] = None,
    ):
        """
        Return an existing workflow for the user or create a new one if:
          - None exists
          - Team switched flag is True
          - force_rebuild is True (for new tasks after workflow completion)
        """
        current = orchestration_config.get_current_orchestration(user_id)
        needs_rebuild = current is None or team_switched or force_rebuild

        if needs_rebuild:
            if current is not None and (team_switched or force_rebuild):
                reason = "team switched" if team_switched else "force rebuild for new task"
                cls.logger.info(
                    "Rebuilding orchestration for user '%s' (reason: %s)", user_id, reason
                )
                if cls._workflow_has_plan_scope(current):
                    current_plan_id = cls._get_manager_plan_id(
                        cls._get_workflow_terminal_manager(current)
                    )
                    cls.logger.info(
                        "Deferring close of replaced workflow for user '%s' plan '%s' until its run completes",
                        user_id,
                        current_plan_id,
                    )
                else:
                    await cls._close_workflow_participants(current, reason)

            factory = MagenticAgentFactory(team_service=team_service)
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
                raise
            try:
                cls.logger.info("Initializing new orchestration for user '%s'", user_id)
                workflow = await cls.init_orchestration(
                    agents,
                    team_config,
                    team_service.memory_context,
                    user_id=user_id,
                    plan_id=plan_id,
                )
                orchestration_config.orchestrations[user_id] = workflow
                return workflow
            except Exception as e:
                cls.logger.error(
                    "Failed to initialize orchestration for user '%s': %s", user_id, e
                )
                raise
        return current

    # ---------------------------
    # Execution
    # ---------------------------
    async def run_orchestration(
        self, user_id: str, input_task, plan_id: Optional[str] = None, workflow=None
    ) -> None:
        """
        Execute the Magentic workflow for the provided user and task description.
        """
        explicit_workflow = workflow is not None
        job_id = str(uuid.uuid4())
        orchestration_config.set_approval_pending(job_id)
        self.logger.info(
            "Starting orchestration job '%s' for user '%s'", job_id, user_id
        )

        if workflow is not None:
            try:
                await self._validate_explicit_workflow_plan(user_id, plan_id, workflow)
            except ValueError as validation_error:
                try:
                    await self._send_orchestration_error(
                        user_id, plan_id, validation_error, workflow
                    )
                finally:
                    await self._close_workflow_participants(
                        workflow, "explicit orchestration validation failed"
                    )
                raise
        else:
            workflow = orchestration_config.get_current_orchestration(user_id)

        if workflow is None:
            error = ValueError("Orchestration not initialized for user.")
            await self._send_orchestration_error(user_id, plan_id, error)
            raise error
        # Fresh thread per participant to avoid cross-run state bleed
        executors = getattr(workflow, "executors", {})
        self.logger.debug("Executor keys at run start: %s", list(executors.keys()))

        for exec_key, executor in executors.items():
            try:
                if exec_key == "magentic_orchestrator":
                    # Orchestrator path
                    if hasattr(executor, "_conversation"):
                        conv = getattr(executor, "_conversation")
                        # Support list-like or custom container with clear()
                        if hasattr(conv, "clear") and callable(conv.clear):
                            conv.clear()
                            self.logger.debug(
                                "Cleared orchestrator conversation (%s)", exec_key
                            )
                        elif isinstance(conv, list):
                            conv[:] = []
                            self.logger.debug(
                                "Emptied orchestrator conversation list (%s)", exec_key
                            )
                        else:
                            self.logger.debug(
                                "Orchestrator conversation not clearable type (%s): %s",
                                exec_key,
                                type(conv),
                            )
                    else:
                        self.logger.debug(
                            "Orchestrator has no _conversation attribute (%s)", exec_key
                        )
                else:
                    # Agent path
                    if hasattr(executor, "_chat_history"):
                        hist = getattr(executor, "_chat_history")
                        if hasattr(hist, "clear") and callable(hist.clear):
                            hist.clear()
                            self.logger.debug(
                                "Cleared agent chat history (%s)", exec_key
                            )
                        elif isinstance(hist, list):
                            hist[:] = []
                            self.logger.debug(
                                "Emptied agent chat history list (%s)", exec_key
                            )
                        else:
                            self.logger.debug(
                                "Agent chat history not clearable type (%s): %s",
                                exec_key,
                                type(hist),
                            )
                    else:
                        self.logger.debug(
                            "Agent executor has no _chat_history attribute (%s)",
                            exec_key,
                        )
            except Exception as e:
                self.logger.warning(
                    "Failed clearing state for executor %s: %s", exec_key, e
                )
        # --- END NEW BLOCK ---

        # Build task from input (same as old version)
        task_text = getattr(input_task, "description", str(input_task))
        self.logger.debug("Task: %s", task_text)

        # Track how many times each agent is called (for debugging duplicate calls)
        agent_call_counts: dict = {}
        # Buffer streamed text per-agent so we can emit a complete AGENT_MESSAGE
        agent_stream_buffers: dict[str, str] = {}

        try:
            # Execute workflow using run() with stream=True
            # The execution settings are configured in the manager/client
            final_output: str | None = None

            self.logger.info("Starting workflow execution...")

            async for event in workflow.run(task_text, stream=True):
                try:
                    # WorkflowEvent has a .type field (string) instead of specific event classes
                    event_type = event.type if hasattr(event, "type") else type(event).__name__
                    if event_type not in ("status", "output"):
                        self.logger.info("[EVENT] type=%s", event_type)

                    # Handle orchestrator events (plan, progress ledger)
                    if event_type == "magentic_orchestrator":
                        self.logger.info(
                            "[Magentic Orchestrator Event]"
                        )
                        if isinstance(event.data, Message):
                            self.logger.info("Plan message: %s", event.data.text[:200] if event.data.text else "")
                        elif isinstance(event.data, MagenticProgressLedger):
                            self.logger.info("Progress ledger received")

                    # Handle group chat request sent
                    elif event_type == "group_chat":
                        # Check if this is a request or response via the data type
                        if isinstance(event.data, GroupChatRequestSentEvent):
                            agent_name = event.data.participant_name
                            agent_call_counts[agent_name] = agent_call_counts.get(agent_name, 0) + 1
                            call_num = agent_call_counts[agent_name]

                            self.logger.info(
                                "[REQUEST SENT (round %d)] to agent: %s (call #%d)",
                                event.data.round_index,
                                agent_name,
                                call_num
                            )

                            if call_num > 1:
                                self.logger.warning("Agent '%s' called %d times", agent_name, call_num)

                        elif isinstance(event.data, GroupChatResponseReceivedEvent):
                            agent_name = event.data.participant_name
                            self.logger.info(
                                "[RESPONSE RECEIVED (round %d)] from agent: %s",
                                event.data.round_index,
                                agent_name
                            )
                            # Flush accumulated streaming content as a complete AGENT_MESSAGE
                            buffered = agent_stream_buffers.pop(agent_name, "")
                            if buffered:
                                from v4.callbacks.response_handlers import clean_citations
                                from v4.models.messages import AgentMessage
                                cleaned = clean_citations(buffered)
                                if cleaned.strip():
                                    agent_msg = AgentMessage(
                                        agent_name=agent_name,
                                        timestamp=str(_time.time()),
                                        content=cleaned,
                                    )
                                    await connection_config.send_status_update_async(
                                        agent_msg,
                                        user_id,
                                        message_type=WebsocketMessageType.AGENT_MESSAGE,
                                    )
                                    self.logger.info(
                                        "Sent AGENT_MESSAGE for '%s' (%d chars)",
                                        agent_name, len(cleaned)
                                    )

                    # Handle executor completed - just log, don't send to UI
                    elif event_type == "executor_completed":
                        self.logger.debug(
                            "[EXECUTOR COMPLETED] agent: %s",
                            getattr(event, "executor_id", "unknown")
                        )
                        # Don't send to UI here - group_chat events already handle agent messages

                    # Handle workflow output event (streaming chunks AND final result)
                    elif event_type == "output":
                        executor_id = getattr(event, "executor_id", None)
                        output_data = event.data
                        self.logger.info(
                            "[OUTPUT] executor=%s data_type=%s",
                            executor_id, type(output_data).__name__
                        )

                        # Streaming chunk from an agent executor
                        if isinstance(output_data, AgentResponseUpdate) and executor_id:
                            chunk_text = output_data.text or ""
                            if chunk_text:
                                agent_stream_buffers[executor_id] = agent_stream_buffers.get(executor_id, "") + chunk_text
                            try:
                                await streaming_agent_response_callback(
                                    executor_id,
                                    output_data,
                                    False,
                                    user_id,
                                )
                            except Exception as e:
                                self.logger.error(
                                    "Error in streaming callback for agent %s: %s",
                                    executor_id, e
                                )
                        # Final workflow output (list[Message] or Message)
                        elif isinstance(output_data, Message):
                            final_output = output_data.text or ""
                        elif isinstance(output_data, list):
                            # Handle list of Message objects
                            texts = []
                            for item in output_data:
                                if isinstance(item, Message):
                                    if item.text:
                                        texts.append(item.text)
                                else:
                                    texts.append(str(item))
                            final_output = "\n".join(texts)
                        elif hasattr(output_data, "text"):
                            final_output = output_data.text or ""
                        else:
                            final_output = str(output_data) if output_data else ""
                        self.logger.debug("Received workflow output event")

                except Exception as e:
                    self.logger.error(
                        f"Error processing event {type(event).__name__}: {e}",
                        exc_info=True,
                    )

            # Extract final result
            final_text = final_output if final_output else ""

            # Log agent call summary
            self.logger.info("Agent call counts: %s", agent_call_counts)

            # Log results
            self.logger.info("\nAgent responses:")
            self.logger.info(
                "Orchestration completed. Final result length: %d chars",
                len(final_text),
            )
            self.logger.info("\nFinal result:\n%s", final_text)
            self.logger.info("=" * 50)

            manager = self._get_non_completed_terminal_manager(workflow, plan_id)
            if manager:
                self.logger.info(
                    "Skipping completed final result for user '%s' because terminal status '%s' was already sent",
                    user_id,
                    manager.terminal_final_result_status,
                )
                return

            # Send final result via WebSocket
            await self._persist_terminal_plan_status(
                user_id, plan_id, "completed", final_text
            )
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

            await self._send_orchestration_error(user_id, plan_id, e, workflow)
            raise
        finally:
            if explicit_workflow:
                await self._close_workflow_participants(
                    workflow, "explicit orchestration run finished"
                )

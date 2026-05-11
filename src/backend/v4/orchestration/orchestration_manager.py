"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
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
from common.models.messages_af import TeamConfiguration

from common.database.database_base import DatabaseBase

from v4.common.services.team_service import TeamService
import time as _time
from v4.callbacks.response_handlers import (
    streaming_agent_response_callback,
)
from v4.config.settings import connection_config, orchestration_config
from v4.models.messages import TokenUsageUpdate, WebsocketMessageType
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
                max_reset_count=2
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
                # Close prior agents (same logic as old version)
                for agent in getattr(current, "_participants", {}).values():
                    agent_name = getattr(
                        agent, "agent_name", getattr(agent, "name", "")
                    )
                    if agent_name != "ProxyAgent":
                        close_coro = getattr(agent, "close", None)
                        if callable(close_coro):
                            try:
                                await close_coro()
                                cls.logger.debug("Closed agent '%s'", agent_name)
                            except Exception as e:
                                cls.logger.error("Error closing agent: %s", e)

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
                    agents, team_config, team_service.memory_context, user_id
                )
                orchestration_config.orchestrations[user_id] = workflow

                # Build agent_name -> model_deployment_name map for token tracking
                agent_model_map: dict[str, str] = {}
                for ag in agents:
                    name = getattr(ag, "agent_name", None) or getattr(ag, "name", None) or ""
                    model = getattr(ag, "model_deployment_name", None) or ""
                    if name:
                        agent_model_map[name] = model
                # Also include the orchestrator manager's model
                agent_model_map["MagenticManager"] = team_config.deployment_name or ""
                orchestration_config.agent_model_maps[user_id] = agent_model_map
                cls.logger.info("Agent model map for user '%s': %s", user_id, agent_model_map)
            except Exception as e:
                cls.logger.error(
                    "Failed to initialize orchestration for user '%s': %s", user_id, e
                )
                raise
        return orchestration_config.get_current_orchestration(user_id)

    # ---------------------------
    # Token usage extraction helpers
    # ---------------------------
    def _extract_usage_from_dict(self, d: dict) -> tuple[int, int, int] | None:
        """Extract (input, output, total) from a usage dict."""
        inp = d.get("input_token_count", 0) or d.get("prompt_tokens", 0) or d.get("input_tokens", 0) or 0
        out = d.get("output_token_count", 0) or d.get("completion_tokens", 0) or d.get("output_tokens", 0) or 0
        tot = d.get("total_token_count", 0) or d.get("total_tokens", 0) or (inp + out)
        if tot > 0:
            return (inp, out, tot)
        return None

    def _extract_usage_from_response_update(self, update: AgentResponseUpdate, agent_name: str) -> tuple[int, int, int] | None:
        """
        Extract token usage from an AgentResponseUpdate by checking multiple locations:
        1. contents[] with type == 'usage' (Content objects with usage_details)
        2. contents[] that are plain dicts with usage keys
        3. raw_representation (OpenAI SDK response object)
        4. additional_properties
        """
        # 1. Check contents for Content objects with type == "usage"
        contents = getattr(update, "contents", None) or []
        for item in contents:
            # Content object: check .type == "usage"
            item_type = getattr(item, "type", None)
            if item_type == "usage":
                usage_details = getattr(item, "usage_details", None)
                if isinstance(usage_details, dict):
                    result = self._extract_usage_from_dict(usage_details)
                    if result:
                        self.logger.debug("[TOKEN] Found usage in Content(type=usage) for %s", agent_name)
                        return result

            # Content object: check .usage_details directly even if type != "usage"
            usage_details = getattr(item, "usage_details", None)
            if isinstance(usage_details, dict) and usage_details:
                result = self._extract_usage_from_dict(usage_details)
                if result:
                    self.logger.debug("[TOKEN] Found usage in Content.usage_details for %s", agent_name)
                    return result

            # Plain dict item (MutableMapping)
            if isinstance(item, dict):
                if "usage_details" in item and isinstance(item["usage_details"], dict):
                    result = self._extract_usage_from_dict(item["usage_details"])
                    if result:
                        self.logger.debug("[TOKEN] Found usage in dict content for %s", agent_name)
                        return result
                # Direct usage keys in dict
                if "input_token_count" in item or "total_token_count" in item:
                    result = self._extract_usage_from_dict(item)
                    if result:
                        return result

        # 2. Check raw_representation (OpenAI SDK response)
        raw = getattr(update, "raw_representation", None)
        if raw is not None:
            # OpenAI ChatCompletion response
            usage_obj = getattr(raw, "usage", None)
            if usage_obj is not None:
                if isinstance(usage_obj, dict):
                    result = self._extract_usage_from_dict(usage_obj)
                else:
                    inp = getattr(usage_obj, "prompt_tokens", 0) or getattr(usage_obj, "input_tokens", 0) or 0
                    out = getattr(usage_obj, "completion_tokens", 0) or getattr(usage_obj, "output_tokens", 0) or 0
                    tot = getattr(usage_obj, "total_tokens", 0) or (inp + out)
                    if tot > 0:
                        result = (inp, out, tot)
                    else:
                        result = None
                if result:
                    self.logger.debug("[TOKEN] Found usage in raw_representation.usage for %s", agent_name)
                    return result

            # Check if raw is a dict
            if isinstance(raw, dict) and "usage" in raw:
                usage_raw = raw["usage"]
                if isinstance(usage_raw, dict):
                    result = self._extract_usage_from_dict(usage_raw)
                    if result:
                        self.logger.debug("[TOKEN] Found usage in raw dict for %s", agent_name)
                        return result

        # 3. Check additional_properties
        addl = getattr(update, "additional_properties", None)
        if isinstance(addl, dict) and addl:
            if "usage" in addl:
                u = addl["usage"]
                if isinstance(u, dict):
                    result = self._extract_usage_from_dict(u)
                    if result:
                        self.logger.debug("[TOKEN] Found usage in additional_properties for %s", agent_name)
                        return result

        return None

    def _try_extract_usage_from_event(self, event_data) -> tuple[int, int, int] | None:
        """
        Try to extract token usage from any event data object by checking
        common attribute patterns.
        """
        # Check for .usage attribute
        usage = getattr(event_data, "usage", None)
        if usage is not None:
            if isinstance(usage, dict):
                return self._extract_usage_from_dict(usage)
            inp = getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_token_count", 0) or getattr(usage, "input_tokens", 0) or 0
            out = getattr(usage, "completion_tokens", 0) or getattr(usage, "output_token_count", 0) or getattr(usage, "output_tokens", 0) or 0
            tot = getattr(usage, "total_tokens", 0) or getattr(usage, "total_token_count", 0) or (inp + out)
            if tot > 0:
                return (inp, out, tot)

        # Check for .response with .usage
        response = getattr(event_data, "response", None)
        if response is not None:
            return self._try_extract_usage_from_event(response)

        # Check for .message with usage in metadata
        msg = getattr(event_data, "message", None)
        if msg is not None:
            metadata = getattr(msg, "metadata", None) or getattr(msg, "additional_properties", None)
            if isinstance(metadata, dict) and "usage" in metadata:
                u = metadata["usage"]
                if isinstance(u, dict):
                    return self._extract_usage_from_dict(u)

        # Check to_dict() for nested usage
        if hasattr(event_data, "to_dict"):
            try:
                d = event_data.to_dict()
                if isinstance(d, dict):
                    # Look for usage anywhere in the dict
                    if "usage" in d and isinstance(d["usage"], dict):
                        return self._extract_usage_from_dict(d["usage"])
                    if "usage_details" in d and isinstance(d["usage_details"], dict):
                        return self._extract_usage_from_dict(d["usage_details"])
            except Exception:
                pass

        return None

    # ---------------------------
    # Execution
    # ---------------------------
    async def run_orchestration(self, user_id: str, input_task, plan_id: str | None = None) -> None:
        """
        Execute the Magentic workflow for the provided user and task description.
        """
        job_id = str(uuid.uuid4())
        orchestration_config.set_approval_pending(job_id)
        self.logger.info(
            "Starting orchestration job '%s' for user '%s'", job_id, user_id
        )

        workflow = orchestration_config.get_current_orchestration(user_id)
        if workflow is None:
            raise ValueError("Orchestration not initialized for user.")
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

        # Load agent_name -> model_deployment_name map for token tracking
        agent_model_map: dict[str, str] = orchestration_config.agent_model_maps.get(user_id, {})

        # Track how many times each agent is called (for debugging duplicate calls)
        agent_call_counts: dict = {}
        # Buffer streamed text per-agent so we can emit a complete AGENT_MESSAGE
        agent_stream_buffers: dict[str, str] = {}
        # Token usage tracking per agent: {agent_name: {input_tokens: int, output_tokens: int, total_tokens: int, model_deployment_name: str}}
        agent_token_usage: dict[str, dict[str, int | str]] = {}
        # Token usage tracking per model: {model_deployment_name: {input_tokens: int, output_tokens: int, total_tokens: int}}
        model_token_usage: dict[str, dict[str, int]] = {}
        cumulative_input_tokens = 0
        cumulative_output_tokens = 0
        cumulative_total_tokens = 0

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

                            # Extract token usage from GroupChatResponseReceivedEvent
                            _gc_usage = self._try_extract_usage_from_event(event.data)
                            if _gc_usage:
                                inp, out, tot = _gc_usage
                                if tot > 0:
                                    agent_model = agent_model_map.get(agent_name, "")
                                    if agent_name not in agent_token_usage:
                                        agent_token_usage[agent_name] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "model_deployment_name": agent_model}
                                    agent_token_usage[agent_name]["input_tokens"] += inp
                                    agent_token_usage[agent_name]["output_tokens"] += out
                                    agent_token_usage[agent_name]["total_tokens"] += tot
                                    # Accumulate model-level usage
                                    if agent_model:
                                        if agent_model not in model_token_usage:
                                            model_token_usage[agent_model] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                                        model_token_usage[agent_model]["input_tokens"] += inp
                                        model_token_usage[agent_model]["output_tokens"] += out
                                        model_token_usage[agent_model]["total_tokens"] += tot
                                    cumulative_input_tokens += inp
                                    cumulative_output_tokens += out
                                    cumulative_total_tokens += tot
                                    self.logger.info(
                                        "[TOKEN USAGE from GroupChat] agent=%s model=%s input=%d output=%d total=%d | cumulative: %d/%d/%d",
                                        agent_name, agent_model, inp, out, tot,
                                        cumulative_input_tokens, cumulative_output_tokens, cumulative_total_tokens,
                                    )
                                    try:
                                        token_update = TokenUsageUpdate(
                                            agent_name=agent_name,
                                            input_tokens=inp, output_tokens=out, total_tokens=tot,
                                            cumulative_input_tokens=cumulative_input_tokens,
                                            cumulative_output_tokens=cumulative_output_tokens,
                                            cumulative_total_tokens=cumulative_total_tokens,
                                            model_deployment_name=agent_model,
                                        )
                                        await connection_config.send_status_update_async(
                                            token_update, user_id,
                                            message_type=WebsocketMessageType.TOKEN_USAGE_UPDATE,
                                        )
                                    except Exception as tok_err:
                                        self.logger.warning("Failed to send token usage update: %s", tok_err)

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

                            # Extract token usage from AgentResponseUpdate
                            usage_found = self._extract_usage_from_response_update(output_data, executor_id)
                            if usage_found:
                                inp, out, tot = usage_found
                                if tot > 0:
                                    executor_model = agent_model_map.get(executor_id, "")
                                    if executor_id not in agent_token_usage:
                                        agent_token_usage[executor_id] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "model_deployment_name": executor_model}
                                    agent_token_usage[executor_id]["input_tokens"] += inp
                                    agent_token_usage[executor_id]["output_tokens"] += out
                                    agent_token_usage[executor_id]["total_tokens"] += tot
                                    # Accumulate model-level usage
                                    if executor_model:
                                        if executor_model not in model_token_usage:
                                            model_token_usage[executor_model] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                                        model_token_usage[executor_model]["input_tokens"] += inp
                                        model_token_usage[executor_model]["output_tokens"] += out
                                        model_token_usage[executor_model]["total_tokens"] += tot
                                    cumulative_input_tokens += inp
                                    cumulative_output_tokens += out
                                    cumulative_total_tokens += tot
                                    self.logger.info(
                                        "[TOKEN USAGE from stream] agent=%s model=%s input=%d output=%d total=%d | cumulative: %d/%d/%d",
                                        executor_id, executor_model, inp, out, tot,
                                        cumulative_input_tokens, cumulative_output_tokens, cumulative_total_tokens,
                                    )
                                    try:
                                        token_update = TokenUsageUpdate(
                                            agent_name=executor_id,
                                            input_tokens=inp, output_tokens=out, total_tokens=tot,
                                            cumulative_input_tokens=cumulative_input_tokens,
                                            cumulative_output_tokens=cumulative_output_tokens,
                                            cumulative_total_tokens=cumulative_total_tokens,
                                            model_deployment_name=executor_model,
                                        )
                                        await connection_config.send_status_update_async(
                                            token_update, user_id,
                                            message_type=WebsocketMessageType.TOKEN_USAGE_UPDATE,
                                        )
                                    except Exception as tok_err:
                                        self.logger.warning("Failed to send token usage update: %s", tok_err)

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

            # Log token usage summary
            if agent_token_usage:
                self.logger.info(
                    "[TOKEN SUMMARY] Total: input=%d output=%d total=%d | By agent: %s | By model: %s",
                    cumulative_input_tokens, cumulative_output_tokens, cumulative_total_tokens,
                    {k: v for k, v in agent_token_usage.items()},
                    {k: v for k, v in model_token_usage.items()},
                )

                # Track token usage to Application Insights
                from common.utils.event_utils import track_event_if_configured
                track_event_if_configured("LLM_Token_Usage_Summary", {
                    "total_input_tokens": str(cumulative_input_tokens),
                    "total_output_tokens": str(cumulative_output_tokens),
                    "total_tokens": str(cumulative_total_tokens),
                    "agent_count": str(len(agent_token_usage)),
                    "model_count": str(len(model_token_usage)),
                    "user_id": user_id or "",
                })
                # Track per-agent usage
                for agent_name, usage in agent_token_usage.items():
                    track_event_if_configured("LLM_Agent_Token_Usage", {
                        "agent_name": agent_name,
                        "input_tokens": str(usage["input_tokens"]),
                        "output_tokens": str(usage["output_tokens"]),
                        "total_tokens": str(usage["total_tokens"]),
                        "model_deployment_name": str(usage.get("model_deployment_name", "")),
                        "user_id": user_id or "",
                    })
                # Track per-model usage
                for model_name, usage in model_token_usage.items():
                    track_event_if_configured("LLM_Model_Token_Usage", {
                        "model_deployment_name": model_name,
                        "input_tokens": str(usage["input_tokens"]),
                        "output_tokens": str(usage["output_tokens"]),
                        "total_tokens": str(usage["total_tokens"]),
                        "user_id": user_id or "",
                    })

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

            # Persist token usage to the plan in CosmosDB
            if plan_id and cumulative_total_tokens > 0:
                try:
                    from common.database.database_factory import DatabaseFactory
                    db = await DatabaseFactory.get_database(user_id=user_id)
                    plan = await db.get_plan_by_plan_id(plan_id=plan_id)
                    if plan:
                        plan.total_input_tokens = cumulative_input_tokens
                        plan.total_output_tokens = cumulative_output_tokens
                        plan.total_tokens = cumulative_total_tokens
                        plan.usage_by_agent = agent_token_usage
                        plan.usage_by_model = model_token_usage
                        await db.update_item(plan)
                        self.logger.info(
                            "Persisted token usage to plan '%s': total=%d",
                            plan_id, cumulative_total_tokens,
                        )
                except Exception as db_err:
                    self.logger.warning("Failed to persist token usage to plan: %s", db_err)

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

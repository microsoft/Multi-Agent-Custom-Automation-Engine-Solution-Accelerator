"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import re
import uuid
from typing import List, Optional

# agent_framework imports
from agent_framework_azure_ai import AzureAIClient
from agent_framework import (
    ChatAgent,
    ChatMessage,
    WorkflowOutputEvent,
    MagenticBuilder,
    InMemoryCheckpointStorage,
    AgentRunUpdateEvent,
    GroupChatRequestSentEvent,
    GroupChatResponseReceivedEvent,
    ExecutorCompletedEvent,
    MagenticOrchestratorEvent,
    MagenticProgressLedger,
)

from common.config.app_config import config
from common.models.messages_af import TeamConfiguration

from common.database.database_base import DatabaseBase

from v4.common.services.team_service import TeamService
from v4.callbacks.response_handlers import (
    agent_response_callback,
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
        - ChatMessage: Extract .text
        - AgentResponse: Extract .text
        - AgentExecutorResponse: Extract from agent_response.text or full_conversation[-1].text
        - List of any of the above
        """
        if data is None:
            return ""
        
        # Direct ChatMessage
        if isinstance(data, ChatMessage):
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
                if isinstance(last_msg, ChatMessage) and last_msg.text:
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

            # New API: Create a ChatAgent to wrap the chat client for the manager
            manager_agent = ChatAgent(
                chat_client=chat_client,
                name="MagenticManager",
                description="Orchestrator that coordinates the team to complete complex tasks efficiently.",
                instructions="You coordinate a team to complete complex tasks efficiently.",
            )

            cls.logger.info(
                "Created AzureAIClient and manager ChatAgent for orchestration with model '%s' at endpoint '%s'",
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

            # Extract the inner ChatAgent for wrapper templates
            # FoundryAgentTemplate wrap a ChatAgent in self._agent
            # ProxyAgent directly extends BaseAgent and can be used as-is
            if hasattr(ag, "_agent") and ag._agent is not None:
                # This is a wrapper (FoundryAgentTemplate)
                # Use the inner ChatAgent which implements AgentProtocol
                participants[name] = ag._agent
                cls.logger.debug("Added participant '%s' (extracted inner agent)", name)
            else:
                # This is already an agent (like ProxyAgent extending BaseAgent)
                participants[name] = ag
                cls.logger.debug("Added participant '%s'", name)

        # Assemble workflow with callback
        storage = InMemoryCheckpointStorage()
        
        # New API: .participants() accepts a list of agents
        participant_list = list(participants.values())
        
        builder = (
            MagenticBuilder()
            .participants(participant_list)
            .with_manager(
                manager=manager,  # Pass manager instance (extends StandardMagenticManager)
                max_round_count=orchestration_config.max_rounds,
                max_stall_count=3,
                max_reset_count=2,
            )
            .with_checkpointing(storage)
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
                print(f"Failed to create agents for user '{user_id}': {e}")
                raise
            try:
                cls.logger.info("Initializing new orchestration for user '%s'", user_id)
                print(f"[DEBUG] Initializing new orchestration for user '{user_id}'")
                workflow = await cls.init_orchestration(
                    agents, team_config, team_service.memory_context, user_id
                )
                orchestration_config.orchestrations[user_id] = workflow
                print(f"[DEBUG] Stored workflow for user '{user_id}': {workflow is not None}")
                print(f"[DEBUG] orchestrations keys: {list(orchestration_config.orchestrations.keys())}")
            except Exception as e:
                cls.logger.error(
                    "Failed to initialize orchestration for user '%s': %s", user_id, e
                )
                print(f"Failed to initialize orchestration for user '{user_id}': {e}")
                import traceback
                traceback.print_exc()
                raise
        return orchestration_config.get_current_orchestration(user_id)

    # ---------------------------
    # Execution
    # ---------------------------
    async def run_orchestration(self, user_id: str, input_task) -> None:
        """
        Execute the Magentic workflow for the provided user and task description.
        """
        job_id = str(uuid.uuid4())
        orchestration_config.set_approval_pending(job_id)
        self.logger.info(
            "Starting orchestration job '%s' for user '%s'", job_id, user_id
        )
        print(f"[DEBUG] run_orchestration called for user '{user_id}'")
        print(f"[DEBUG] orchestrations keys before get: {list(orchestration_config.orchestrations.keys())}")

        workflow = orchestration_config.get_current_orchestration(user_id)
        print(f"[DEBUG] workflow is None: {workflow is None}")
        if workflow is None:
            print(f"[ERROR] Orchestration not initialized for user '{user_id}'")
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

        try:
            # Execute workflow using run_stream with task as positional parameter
            # The execution settings are configured in the manager/client
            final_output: str | None = None

            self.logger.info("Starting workflow execution...")
            last_message_id: str | None = None
            async for event in workflow.run_stream(task_text):
                try:
                    # Only log non-streaming events (reduce noise)
                    event_type_name = type(event).__name__
                    if event_type_name != "AgentRunUpdateEvent":
                        self.logger.info("[EVENT] %s", event_type_name)
                    
                    # Handle orchestrator events (plan, progress ledger)
                    if isinstance(event, MagenticOrchestratorEvent):
                        self.logger.info(
                            "[Magentic Orchestrator Event] Type: %s",
                            event.event_type.name
                        )
                        if isinstance(event.data, ChatMessage):
                            self.logger.info("Plan message: %s", event.data.text[:200] if event.data.text else "")
                        elif isinstance(event.data, MagenticProgressLedger):
                            self.logger.info("Progress ledger received")

                    # Handle agent streaming/updates (replaces MagenticAgentDeltaEvent and MagenticAgentMessageEvent)
                    elif isinstance(event, AgentRunUpdateEvent):
                        message_id = event.data.message_id if hasattr(event.data, 'message_id') else None
                        executor_id = event.executor_id
                        
                        # Stream the update
                        try:
                            await streaming_agent_response_callback(
                                executor_id,
                                event.data,  # Pass the data object
                                False,  # Not final yet
                                user_id,
                            )
                        except Exception as e:
                            self.logger.error(
                                "Error in streaming callback for agent %s: %s",
                                executor_id, e
                            )
                        
                        # Track message for formatting
                        if message_id != last_message_id:
                            last_message_id = message_id

                    # Handle group chat request sent
                    elif isinstance(event, GroupChatRequestSentEvent):
                        self.logger.info(
                            "[REQUEST SENT (round %d)] to agent: %s",
                            event.round_index,
                            event.participant_name
                        )

                    # Handle group chat response received - THIS IS WHERE AGENT RESPONSES COME
                    elif isinstance(event, GroupChatResponseReceivedEvent):
                        self.logger.info(
                            "[RESPONSE RECEIVED (round %d)] from agent: %s",
                            event.round_index,
                            event.participant_name
                        )
                        # Send the agent response to the UI
                        if event.data:
                            response_text = self._extract_response_text(event.data)
                            
                            if response_text:
                                self.logger.info("Sending agent response to UI from %s", event.participant_name)
                                agent_response_callback(
                                    event.participant_name,
                                    ChatMessage(role="assistant", text=response_text),
                                    user_id,
                                )

                    # Handle executor completed - just log, don't send to UI (GroupChatResponseReceivedEvent handles that)
                    elif isinstance(event, ExecutorCompletedEvent):
                        self.logger.debug(
                            "[EXECUTOR COMPLETED] agent: %s",
                            event.executor_id
                        )
                        # Don't send to UI here - GroupChatResponseReceivedEvent already handles agent messages
                        # This avoids duplicate messages

                    # Handle workflow output event (captures final result)
                    elif isinstance(event, WorkflowOutputEvent):
                        output_data = event.data
                        # Handle different output formats
                        if isinstance(output_data, ChatMessage):
                            final_output = output_data.text or ""
                        elif isinstance(output_data, list):
                            # Handle list of ChatMessage objects
                            texts = []
                            for item in output_data:
                                if isinstance(item, ChatMessage):
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

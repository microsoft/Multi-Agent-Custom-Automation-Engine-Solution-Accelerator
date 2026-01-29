"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import uuid
from typing import List, Optional

# agent_framework imports
from agent_framework.azure import AzureAIClient
from agent_framework import (
    ChatMessage,
    WorkflowOutputEvent,
    MagenticBuilder,
    InMemoryCheckpointStorage,
    MagenticOrchestratorEvent,
    AgentRunUpdateEvent,
)

from common.config.app_config import config
from common.models.messages_af import TeamConfiguration

from common.database.database_base import DatabaseBase

from common.utils.agent_name_sanitizer import AgentNameSanitizer
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
        agent_name = team_config.name if team_config.name else "OrchestratorAgent"
        agent_name = AgentNameSanitizer.sanitize(agent_name)
        try:
            project_client = config.get_ai_project_client()
            chat_client = AzureAIClient(
                project_client=project_client,
                # credential=credential,
                agent_name=agent_name,
                use_latest_version=True,
                # model_deployment_name=team_config.deployment_name
            )

            cls.logger.info(
                "Created AzureAIClient for orchestration with model '%s' at endpoint '%s'",
                team_config.deployment_name,
                config.AZURE_AI_PROJECT_ENDPOINT,
            )
        except Exception as e:
            cls.logger.error("Failed to create AzureAIClient: %s", e)
            raise

        # Create HumanApprovalMagenticManager with chat_client wrapped as agent
        # Execution settings (temperature=0.1, max_tokens=4000) are configured via
        # orchestration_config.create_execution_settings() which matches old SK version
        try:
            # Convert AzureAIClient to ChatAgent to pass to StandardMagenticManager
            # StandardMagenticManager now expects an agent, not a chat_client
            orchestrator_agent = chat_client.as_agent(
                name=agent_name,
                description="Orchestrates multi-agent workflows",
                instructions=None,  # Instructions can be None
            )
            
            manager = HumanApprovalMagenticManager(
                user_id=user_id,
                agent=orchestrator_agent,
                # instructions=None removed - not needed as it's on the agent
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
                inner_agent = ag._agent
                # Ensure the inner agent has the name set
                if not getattr(inner_agent, "name", None):
                    inner_agent.name = name
                participants[name] = inner_agent
                cls.logger.debug("Added participant '%s' (extracted inner agent)", name)
            else:
                # This is already an agent (like ProxyAgent extending BaseAgent)
                # Ensure the agent has the name set
                if not getattr(ag, "name", None):
                    ag.name = name
                participants[name] = ag
                cls.logger.debug("Added participant '%s'", name)

        # Assemble workflow with callback
        storage = InMemoryCheckpointStorage()
        builder = (
            MagenticBuilder()
            .participants(list(participants.values()))  # Pass as list, not kwargs
            .with_standard_manager(
                manager=manager,
                max_round_count=orchestration_config.max_rounds,
                max_stall_count=0,
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
    ):
        """
        Return an existing workflow for the user or create a new one if:
          - None exists
          - Team switched flag is True
        """
        current = orchestration_config.get_current_orchestration(user_id)
        if current is None or team_switched:
            if current is not None and team_switched:
                cls.logger.info(
                    "Team switched, closing previous agents for user '%s'", user_id
                )
                # Close prior agents (same logic as old version)
                for agent in getattr(current, "_participants", {}).values():
                    agent_name = getattr(
                        agent, "agent_name", getattr(agent, "name", "")
                    )
                    agent_name = AgentNameSanitizer.sanitize(agent_name)
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

        try:
            # Execute workflow using run_stream with task as positional parameter
            # The execution settings are configured in the manager/client
            final_output: str | None = None

            self.logger.info("Starting workflow execution...")
            async for event in workflow.run_stream(task_text):
                try:
                    # Handle orchestrator events (plan created, updated, etc.)
                    if isinstance(event, MagenticOrchestratorEvent):
                        event_data = event.data
                        if isinstance(event_data, ChatMessage):
                            message_text = getattr(event_data, "text", "")
                            self.logger.info(f"[ORCHESTRATOR:{event.event_type.value}] {message_text}")
                        else:
                            self.logger.info(f"[ORCHESTRATOR:{event.event_type.value}] {type(event_data).__name__}")

                    # Handle streaming updates from agents
                    elif isinstance(event, AgentRunUpdateEvent):
                        try:
                            # event.data contains AgentResponseUpdate with text, role, etc.
                            await streaming_agent_response_callback(
                                event.executor_id,  # Use executor_id instead of agent_id
                                event.data,  # Pass the update data
                                False,  # Not final yet (streaming in progress)
                                user_id,
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Error in streaming callback for agent {event.executor_id}: {e}"
                            )

                    # Handle workflow output event (captures final result)
                    elif isinstance(event, WorkflowOutputEvent):
                        output_data = event.data
                        # Handle both single ChatMessage and list of ChatMessages
                        if isinstance(output_data, ChatMessage):
                            final_output = getattr(output_data, "text", None) or str(output_data)
                        elif isinstance(output_data, list):
                            # Extract text from list of ChatMessages
                            text_parts = []
                            for item in output_data:
                                if isinstance(item, ChatMessage):
                                    text_parts.append(getattr(item, "text", str(item)))
                                else:
                                    text_parts.append(str(item))
                            final_output = "\n".join(text_parts)
                        else:
                            final_output = str(output_data)
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

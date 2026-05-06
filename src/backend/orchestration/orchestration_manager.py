"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import uuid
from typing import List, Optional

from agent_framework import (
    Agent,
    AgentResponse,
    AgentResponseUpdate,
    InMemoryCheckpointStorage,
    Message,
    WorkflowEvent,
)
from agent_framework.orchestrations import (
    MagenticBuilder,
    MagenticOrchestratorEvent,
    MagenticOrchestratorEventType,
)
# agent_framework imports
from agent_framework_foundry import FoundryChatClient
from agents.agent_factory import AgentFactory
from callbacks.response_handlers import (agent_response_callback,
                                         streaming_agent_response_callback)
from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages import TeamConfiguration
from models.messages import WebsocketMessageType
from orchestration.connection_config import (connection_config,
                                             orchestration_config)
from orchestration.human_approval_manager import HumanApprovalMagenticManager
from services.team_service import TeamService


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
          - FoundryChatClient as the underlying chat client
          - Event-based callbacks for streaming and final responses
        - Uses same deployment, endpoint, and credentials
        - Applies same execution settings (temperature, max_tokens)
        - Maintains same human approval workflow
        """
        if not user_id:
            raise ValueError("user_id is required to initialize orchestration")

        # Get credential from config (same as old version)
        credential = config.get_azure_credential(client_id=config.AZURE_CLIENT_ID)

        # Create Foundry chat client for orchestration using config
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

        # Wrap the chat client in an Agent (MAF 1.x GA API: StandardMagenticManager
        # requires a SupportsAgentRun, not a raw chat client)
        manager_agent = Agent(chat_client, name="MagenticManager")

        # Create HumanApprovalMagenticManager with the manager agent
        try:
            manager = HumanApprovalMagenticManager(
                user_id=user_id,
                agent=manager_agent,
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

        # Build participant list (MAF 1.x GA: MagenticBuilder takes a sequence)
        participant_list = []
        for ag in agents:
            name = getattr(ag, "agent_name", None) or getattr(ag, "name", None)
            if not name:
                name = f"agent_{len(participant_list) + 1}"

            # Agents implementing SupportsAgentRun are used directly
            participant_list.append(ag)
            cls.logger.debug("Added participant '%s'", name)

        # Assemble and build the Magentic workflow
        storage = InMemoryCheckpointStorage()
        workflow = MagenticBuilder(
            participants=participant_list,
            manager=manager,
            max_round_count=orchestration_config.max_rounds,
            checkpoint_storage=storage,
        ).build()

        cls.logger.info(
            "Built Magentic workflow with %d participants",
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
                    if agent_name != "ProxyAgent":
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

        # Build task from input
        task_text = getattr(input_task, "description", str(input_task))
        self.logger.debug("Task: %s", task_text)

        try:
            # MAF 1.x GA: workflow.run(message, stream=True) returns an async stream of WorkflowEvent
            final_output: str | None = None

            self.logger.info("Starting workflow execution...")
            async for event in workflow.run(task_text, stream=True):
                try:
                    # Magentic orchestrator events (plan created, replanned, progress ledger)
                    if event.type == "magentic_orchestrator":
                        orch_event: MagenticOrchestratorEvent = event.data
                        self.logger.info(
                            "[ORCHESTRATOR:%s]", orch_event.event_type.value
                        )

                    # Streaming agent response chunks (AgentResponseUpdate)
                    elif event.type == "data" and isinstance(event.data, AgentResponseUpdate):
                        update: AgentResponseUpdate = event.data
                        agent_id = update.agent_id or event.executor_id or "unknown"
                        try:
                            await streaming_agent_response_callback(
                                agent_id,
                                update,
                                False,
                                user_id,
                            )
                        except Exception as cb_err:
                            self.logger.error(
                                "Error in streaming callback for agent %s: %s",
                                agent_id, cb_err,
                            )

                    # Complete agent response (AgentResponse)
                    elif event.type == "data" and isinstance(event.data, AgentResponse):
                        response: AgentResponse = event.data
                        agent_id = response.agent_id or event.executor_id or "unknown"
                        if response.messages:
                            try:
                                agent_response_callback(
                                    agent_id, response.messages[0], user_id
                                )
                            except Exception as cb_err:
                                self.logger.error(
                                    "Error in agent callback for agent %s: %s",
                                    agent_id, cb_err,
                                )

                    # Workflow output (final result)
                    elif event.type == "output":
                        output_data = event.data
                        if isinstance(output_data, (AgentResponse,)):
                            final_output = output_data.text or str(output_data)
                        elif isinstance(output_data, Message):
                            final_output = output_data.text or str(output_data)
                        elif output_data is not None:
                            final_output = str(output_data)
                        self.logger.debug("Received workflow output event")

                except Exception as e:
                    self.logger.error(
                        "Error processing event type=%s: %s",
                        getattr(event, "type", "?"), e,
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

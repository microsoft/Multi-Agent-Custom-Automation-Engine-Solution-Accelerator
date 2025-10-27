"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import uuid
from typing import List, Optional, Callable, Awaitable

# agent_framework imports
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import ChatMessage, ChatOptions, WorkflowOutputEvent, AgentRunResponseUpdate,  MagenticBuilder


from common.config.app_config import config
from common.models.messages_af import TeamConfiguration

# Existing (legacy) callbacks
from af.callbacks.response_handlers import (
    agent_response_callback,
    streaming_agent_response_callback,
)
from af.config.settings import connection_config, orchestration_config
from af.models.messages import WebsocketMessageType
from af.orchestration.human_approval_manager import HumanApprovalMagenticManager
from af.magentic_agents.magentic_agent_factory import MagenticAgentFactory

class OrchestrationManager:
    """Manager for handling orchestration logic using agent_framework Magentic workflow."""

    logger = logging.getLogger(f"{__name__}.OrchestrationManager")

    def __init__(self):
        self.user_id: Optional[str] = None
        self.logger = self.__class__.logger

    # ---------------------------
    # Internal callback adapters
    # ---------------------------
    @staticmethod
    def _user_aware_agent_callback(
        user_id: str,
    ) -> Callable[[str, ChatMessage], Awaitable[None]]:
        """Adapts agent_framework final agent ChatMessage to legacy agent_response_callback signature."""

        async def _cb(agent_id: str, message: ChatMessage):
            try:
                agent_response_callback(agent_id, message, user_id)  # Fixed: added agent_id
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).error(
                    "agent_response_callback error: %s", e
                )

        return _cb

    @staticmethod
    def _user_aware_streaming_callback(
        user_id: str,
    ) -> Callable[[str, AgentRunResponseUpdate, bool], Awaitable[None]]:
        """Adapts streaming updates to existing streaming handler."""

        async def _cb(agent_id: str, update: AgentRunResponseUpdate, is_final: bool):
            try:
                await streaming_agent_response_callback(agent_id, update, is_final, user_id)  # Fixed: removed shim
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).error(
                    "streaming_agent_response_callback error: %s", e
                )

        return _cb

    # ---------------------------
    # Orchestration construction
    # ---------------------------
    @classmethod
    async def init_orchestration(cls, agents: List, user_id: str | None = None):
        """
        Initialize a Magentic workflow with:
          - Provided agents (participants)
          - HumanApprovalMagenticManager as orchestrator manager
          - AzureAIAgentClient as the underlying chat client
          
        This mirrors the old Semantic Kernel orchestration setup:
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
        try:
            chat_client = AzureAIAgentClient(
                project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
                model_deployment_name=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                async_credential=credential,
            )
            
            cls.logger.info(
                "Created AzureAIAgentClient for orchestration with model '%s' at endpoint '%s'",
                config.AZURE_OPENAI_DEPLOYMENT_NAME,
                config.AZURE_AI_PROJECT_ENDPOINT
            )
        except Exception as e:
            cls.logger.error("Failed to create AzureAIAgentClient: %s", e)
            raise

        # Create HumanApprovalMagenticManager with the chat client
        # Execution settings (temperature=0.1, max_tokens=4000) are configured via 
        # orchestration_config.create_execution_settings() which matches old SK version
        try: 
            manager = HumanApprovalMagenticManager(
                user_id=user_id,
                chat_client=chat_client,
                instructions=None,  # Orchestrator system instructions (optional)
                max_round_count=orchestration_config.max_rounds,
            )
            cls.logger.info(
                "Created HumanApprovalMagenticManager for user '%s' with max_rounds=%d",
                user_id,
                orchestration_config.max_rounds
            )
        except Exception as e:
            cls.logger.error("Failed to create manager: %s", e)
            raise

        # Build participant map: use each agent's name as key
        participants = {}
        for ag in agents:
            name = getattr(ag, "agent_name", None) or getattr(ag, "name", None)
            if not name:
                name = f"agent_{len(participants)+1}"
            participants[name] = ag
            cls.logger.debug("Added participant '%s'", name)

        # Assemble workflow
        builder = (
            MagenticBuilder()
            .participants(**participants)
            .with_standard_manager(manager=manager)
        )

        # Build workflow
        workflow = builder.build()
        cls.logger.info("Built Magentic workflow with %d participants", len(participants))

        # Wire agent response callbacks onto orchestrator
        try:
            orchestrator = getattr(workflow, "_orchestrator", None)
            if orchestrator:
                if getattr(orchestrator, "_agent_response_callback", None) is None:
                    setattr(
                        orchestrator,
                        "_agent_response_callback",
                        cls._user_aware_agent_callback(user_id),
                    )
                if (
                    getattr(orchestrator, "_streaming_agent_response_callback", None)
                    is None
                ):
                    setattr(
                        orchestrator,
                        "_streaming_agent_response_callback",
                        cls._user_aware_streaming_callback(user_id),
                    )
                cls.logger.debug("Attached callbacks to workflow orchestrator")
        except Exception as e:
            cls.logger.warning(
                "Could not attach callbacks to workflow orchestrator: %s", e
            )

        return workflow

    # ---------------------------
    # Orchestration retrieval
    # ---------------------------
    @classmethod
    async def get_current_or_new_orchestration(
        cls, user_id: str, team_config: TeamConfiguration, team_switched: bool
    ):
        """
        Return an existing workflow for the user or create a new one if:
          - None exists
          - Team switched flag is True
        """
        current = orchestration_config.get_current_orchestration(user_id)
        if current is None or team_switched:
            if current is not None and team_switched:
                cls.logger.info("Team switched, closing previous agents for user '%s'", user_id)
                # Close prior agents (same logic as old version)
                for agent in getattr(current, "_participants", {}).values():
                    agent_name = getattr(agent, "agent_name", getattr(agent, "name", ""))
                    if agent_name != "ProxyAgent":
                        close_coro = getattr(agent, "close", None)
                        if callable(close_coro):
                            try:
                                await close_coro()
                                cls.logger.debug("Closed agent '%s'", agent_name)
                            except Exception as e:
                                cls.logger.error("Error closing agent: %s", e)

            factory = MagenticAgentFactory()
            agents = await factory.get_agents(
                user_id=user_id, team_config_input=team_config
            )
            cls.logger.info("Created %d agents for user '%s'", len(agents), user_id)
            
            orchestration_config.orchestrations[user_id] = await cls.init_orchestration(
                agents, user_id
            )
        return orchestration_config.get_current_orchestration(user_id)

    # ---------------------------
    # Execution
    # ---------------------------
    async def run_orchestration(self, user_id: str, input_task) -> None:
        """
        Execute the Magentic workflow for the provided user and task description.
        
        This mirrors the old SK orchestration:
        - Uses same execution settings (temperature=0.1, max_tokens=4000)
        - Maintains same approval workflow
        - Sends same WebSocket updates
        """
        job_id = str(uuid.uuid4())
        orchestration_config.set_approval_pending(job_id)
        self.logger.info("Starting orchestration job '%s' for user '%s'", job_id, user_id)

        workflow = orchestration_config.get_current_orchestration(user_id)
        if workflow is None:
            raise ValueError("Orchestration not initialized for user.")

        # Ensure manager tracks user_id (same as old version)
        try:
            manager = getattr(workflow, "_manager", None)
            if manager and hasattr(manager, "current_user_id"):
                manager.current_user_id = user_id
                self.logger.debug("Set user_id on manager = %s", user_id)
        except Exception as e:
            self.logger.error("Error setting user_id on manager: %s", e)

        # Build task from input (same as old version)
        task_text = getattr(input_task, "description", str(input_task))
        self.logger.debug("Task: %s", task_text)

        try:
            # Execute workflow using run_stream with task as positional parameter
            # The execution settings are configured in the manager/client
            final_output: str | None = None
            
            self.logger.info("Starting workflow execution...")
            async for event in workflow.run_stream(task_text):
                # Check if this is the final output event
                if isinstance(event, WorkflowOutputEvent):
                    final_output = str(event.data)
                    self.logger.debug("Received workflow output event")

            # Extract final result
            final_text = final_output if final_output else ""
            
            # Log results (same format as old version)
            self.logger.info("\nAgent responses:")
            self.logger.info("Orchestration completed. Final result length: %d chars", len(final_text))
            self.logger.info("\nFinal result:\n%s", final_text)
            self.logger.info("=" * 50)

            # Send final result via WebSocket (same as old version)
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
            # Error handling (enhanced from old version)
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
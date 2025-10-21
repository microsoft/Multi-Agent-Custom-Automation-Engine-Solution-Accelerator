"""Orchestration manager (agent_framework version) handling multi-agent Magentic workflow creation and execution."""

import asyncio
import logging
import uuid
from typing import List, Optional, Callable, Awaitable

from common.config.app_config import config
from common.models.messages_kernel import TeamConfiguration

# agent_framework imports
from agent_framework import ChatMessage, Role, ChatOptions
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework._workflows import (
    MagenticBuilder,
    MagenticCallbackMode,
)
from agent_framework._workflows._magentic import AgentRunResponseUpdate  # type: ignore

# Existing (legacy) callbacks expecting SK content; we'll adapt to them.
# If you've created af-native callbacks (e.g. response_handlers_af) import those instead.
from af.callbacks.response_handlers import (
    agent_response_callback,
    streaming_agent_response_callback,
)
from af.config.settings import connection_config, orchestration_config
from af.models.messages import WebsocketMessageType
from af.orchestration.human_approval_manager import HumanApprovalMagenticManager


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
    def _user_aware_agent_callback(user_id: str) -> Callable[[str, ChatMessage], Awaitable[None]]:
        """Adapts agent_framework final agent ChatMessage to legacy agent_response_callback signature."""

        async def _cb(agent_id: str, message: ChatMessage):
            # Reuse existing callback expecting (ChatMessageContent, user_id). We pass text directly.
            try:
                agent_response_callback(message, user_id)  # existing callback is sync
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).error("agent_response_callback error: %s", e)

        return _cb

    @staticmethod
    def _user_aware_streaming_callback(
        user_id: str,
    ) -> Callable[[str, AgentRunResponseUpdate, bool], Awaitable[None]]:
        """Adapts streaming updates to existing streaming handler."""

        async def _cb(agent_id: str, update: AgentRunResponseUpdate, is_final: bool):
            # Build a minimal shim object with text/content for legacy handler if needed.
            # Your converted streaming handlers (response_handlers_af) should replace this eventual shim.
            class _Shim:  # noqa: D401
                def __init__(self, agent_id: str, update: AgentRunResponseUpdate):
                    self.agent_id = agent_id
                    self.text = getattr(update, "text", None)
                    self.contents = getattr(update, "contents", None)
                    self.role = getattr(update, "role", None)

            shim = _Shim(agent_id, update)
            try:
                await streaming_agent_response_callback(shim, is_final, user_id)
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).error("streaming_agent_response_callback error: %s", e)

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
          - AzureOpenAIChatClient as the underlying chat client
        """
        if not user_id:
            raise ValueError("user_id is required to initialize orchestration")

        credential = config.get_azure_credential(client_id=config.AZURE_CLIENT_ID)

        def get_token():
            token = credential.get_token("https://cognitiveservices.azure.com/.default")
            return token.token

        # Create Azure chat client (agent_framework style) - relying on environment or explicit kwargs.
        chat_client = AzureOpenAIChatClient(
            endpoint=config.AZURE_OPENAI_ENDPOINT,
            model_deployment_name=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            azure_ad_token_provider=get_token,
        )

        # HumanApprovalMagenticManager needs the chat_client passed as 'chat_client' in its constructor signature (it subclasses StandardMagenticManager)
        manager = HumanApprovalMagenticManager(
            user_id=user_id,
            chat_client=chat_client,
            instructions=None,  # optionally supply orchestrator system instructions
            max_round_count=orchestration_config.max_rounds,
        )

        # Build participant map: use each agent's name as key
        participants = {}
        for ag in agents:
            name = getattr(ag, "agent_name", None) or getattr(ag, "name", None)
            if not name:
                name = f"agent_{len(participants)+1}"
            participants[name] = ag

        # Assemble workflow
        builder = (
            MagenticBuilder()
            .participants(**participants)
            .with_standard_manager(manager=manager)
        )

        # Register callbacks (non-streaming manager orchestration events). We'll enable streaming agent deltas via unified mode if desired later.
        # Provide direct agent + streaming callbacks (legacy adapter form).
        # The builder currently surfaces unified callback OR agent callbacks; we use agent callbacks here.
        # NOTE: If you want unified events instead, use builder.on_event(..., mode=MagenticCallbackMode.STREAMING).
        # We'll just store callbacks by augmenting manager after build via internal surfaces.
        workflow = builder.build()

        # Wire agent response callbacks onto executor layer
        # The built workflow exposes internal orchestrator/executor attributes; we rely on exported API for adding callbacks if present.
        try:
            # Attributes available: workflow._orchestrator._agent_response_callback, etc.
            # Set them if not already configured (defensive).
            orchestrator = getattr(workflow, "_orchestrator", None)
            if orchestrator:
                if getattr(orchestrator, "_agent_response_callback", None) is None:
                    setattr(
                        orchestrator,
                        "_agent_response_callback",
                        cls._user_aware_agent_callback(user_id),
                    )
                if getattr(orchestrator, "_streaming_agent_response_callback", None) is None:
                    setattr(
                        orchestrator,
                        "_streaming_agent_response_callback",
                        cls._user_aware_streaming_callback(user_id),
                    )
        except Exception as e:  # noqa: BLE001
            cls.logger.warning("Could not attach callbacks to workflow orchestrator: %s", e)

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
                # Close prior agents (skip ProxyAgent if desired)
                for agent in getattr(current, "_participants", {}).values():
                    if getattr(agent, "agent_name", getattr(agent, "name", "")) != "ProxyAgent":
                        close_coro = getattr(agent, "close", None)
                        if callable(close_coro):
                            try:
                                await close_coro()
                            except Exception as e:  # noqa: BLE001
                                cls.logger.error("Error closing agent: %s", e)

            # Build new participants via existing factory (still semantic-kernel path maybe; update separately if needed)
            from v3.magentic_agents.magentic_agent_factory import MagenticAgentFactory  # local import to avoid circular

            factory = MagenticAgentFactory()
            agents = await factory.get_agents(user_id=user_id, team_config_input=team_config)
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
        """
        job_id = str(uuid.uuid4())
        orchestration_config.set_approval_pending(job_id)

        workflow = orchestration_config.get_current_orchestration(user_id)
        if workflow is None:
            raise ValueError("Orchestration not initialized for user.")

        # Ensure manager tracks user_id
        try:
            manager = getattr(workflow, "_manager", None)
            if manager and hasattr(manager, "current_user_id"):
                manager.current_user_id = user_id
        except Exception as e:  # noqa: BLE001
            self.logger.error("Error setting user_id on manager: %s", e)

        # Build a MagenticContext-like starting message; the workflow interface likely exposes invoke(task=...)
        task_text = getattr(input_task, "description", str(input_task))

        # Provide chat options (temperature mapping from original execution_settings)
        chat_options = ChatOptions(
            temperature=0.1,
            max_output_tokens=4000,
        )

        try:
            # Invoke orchestrator; API may be workflow.invoke(task=..., chat_options=...)
            result_msg: ChatMessage = await workflow.invoke(task=task_text, chat_options=chat_options)

            final_text = result_msg.text if result_msg else ""
            self.logger.info("Final result:\n%s", final_text)
            self.logger.info("=" * 50)

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
            self.logger.info("Final result sent via WebSocket to user %s", user_id)
        except Exception as e:  # noqa: BLE001
            self.logger.error("Unexpected orchestration error: %s", e)
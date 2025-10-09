"""
Configuration settings for the Magentic Employee Onboarding system.
Handles Azure OpenAI, MCP, and environment setup.
"""

import asyncio
import json
import logging
from typing import Dict

from common.config.app_config import config
from common.models.messages_kernel import TeamConfiguration
from fastapi import WebSocket
from semantic_kernel.agents.orchestration.magentic import MagenticOrchestration
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from v3.models.messages import MPlan, WebsocketMessageType

logger = logging.getLogger(__name__)


class AzureConfig:
    """Azure OpenAI and authentication configuration."""

    def __init__(self):
        self.endpoint = config.AZURE_OPENAI_ENDPOINT
        self.reasoning_model = config.REASONING_MODEL_NAME
        self.standard_model = config.AZURE_OPENAI_DEPLOYMENT_NAME
        # self.bing_connection_name = config.AZURE_BING_CONNECTION_NAME

        # Create credential
        self.credential = config.get_azure_credentials()

    def ad_token_provider(self) -> str:
        token = self.credential.get_token(config.AZURE_COGNITIVE_SERVICES)
        return token.token

    async def create_chat_completion_service(self, use_reasoning_model: bool = False):
        """Create Azure Chat Completion service."""
        model_name = (
            self.reasoning_model if use_reasoning_model else self.standard_model
        )
        # Create Azure Chat Completion service
        return AzureChatCompletion(
            deployment_name=model_name,
            endpoint=self.endpoint,
            ad_token_provider=self.ad_token_provider,
        )

    def create_execution_settings(self):
        """Create execution settings for OpenAI."""
        return OpenAIChatPromptExecutionSettings(max_tokens=4000, temperature=0.1)


class MCPConfig:
    """MCP server configuration."""

    def __init__(self):
        self.url = config.MCP_SERVER_ENDPOINT
        self.name = config.MCP_SERVER_NAME
        self.description = config.MCP_SERVER_DESCRIPTION

    def get_headers(self, token: str):
        """Get MCP headers with authentication token."""
        return (
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            if token
            else {}
        )


class OrchestrationConfig:
    """Configuration for orchestration settings."""

    def __init__(self):
        self.orchestrations: Dict[str, MagenticOrchestration] = (
            {}
        )  # user_id -> orchestration instance
        self.plans: Dict[str, MPlan] = {}  # plan_id -> plan details
        self.approvals: Dict[str, bool] = {}  # m_plan_id -> approval status
        self.sockets: Dict[str, WebSocket] = {}  # user_id -> WebSocket
        self.clarifications: Dict[str, str] = {}  # m_plan_id -> clarification response
        self.max_rounds: int = (
            20  # Maximum number of replanning rounds 20 needed to accommodate complex tasks
        )

    def get_current_orchestration(self, user_id: str) -> MagenticOrchestration:
        """get existing orchestration instance."""
        return self.orchestrations.get(user_id, None)


class ConnectionConfig:
    """Connection manager for WebSocket connections."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        # Map user_id to process_id for context-based messaging
        self.user_to_process: Dict[str, str] = {}

    def add_connection(
        self, process_id: str, connection: WebSocket, user_id: str = None
    ):
        """Add a new connection."""
        # Close existing connection if it exists
        if process_id in self.connections:
            try:
                asyncio.create_task(self.connections[process_id].close())
            except Exception as e:
                logger.error(
                    f"Error closing existing connection for user {process_id}: {e}"
                )

        self.connections[process_id] = connection
        # Map user to process for context-based messaging
        if user_id:
            user_id = str(user_id)
            # If this user already has a different process mapped, close that old connection
            old_process_id = self.user_to_process.get(user_id)
            if old_process_id and old_process_id != process_id:
                old_connection = self.connections.get(old_process_id)
                if old_connection:
                    try:
                        asyncio.create_task(old_connection.close())
                        del self.connections[old_process_id]
                        logger.info(
                            f"Closed old connection {old_process_id} for user {user_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error closing old connection for user {user_id}: {e}"
                        )

            self.user_to_process[user_id] = process_id
            logger.info(
                f"WebSocket connection added for process: {process_id} (user: {user_id})"
            )
        else:
            logger.info(f"WebSocket connection added for process: {process_id}")

    def remove_connection(self, process_id):
        """Remove a connection."""
        process_id = str(process_id)
        if process_id in self.connections:
            del self.connections[process_id]

        # Remove from user mapping if exists
        for user_id, mapped_process_id in list(self.user_to_process.items()):
            if mapped_process_id == process_id:
                del self.user_to_process[user_id]
                logger.debug(f"Removed user mapping: {user_id} -> {process_id}")
                break

    def get_connection(self, process_id):
        """Get a connection."""
        return self.connections.get(process_id)

    async def close_connection(self, process_id):
        """Remove a connection."""
        connection = self.get_connection(process_id)
        if connection:
            try:
                await connection.close()
                logger.info("Connection closed for batch ID: %s", process_id)
            except Exception as e:
                logger.error(f"Error closing connection for {process_id}: {e}")
        else:
            logger.warning("No connection found for batch ID: %s", process_id)

        # Always remove from connections dict
        self.remove_connection(process_id)
        logger.info("Connection removed for batch ID: %s", process_id)

    async def send_status_update_async(
        self,
        message: any,
        user_id: str,
        message_type: WebsocketMessageType = WebsocketMessageType.SYSTEM_MESSAGE,
    ):
        """Send a status update to a specific client."""

        if not user_id:
            logger.warning("No user_id available for WebSocket message")
            return

        process_id = self.user_to_process.get(user_id)
        if not process_id:
            logger.warning("No active WebSocket process found for user ID: %s", user_id)
            logger.debug(
                f"Available user mappings: {list(self.user_to_process.keys())}"
            )
            return

        # Convert message to proper format for frontend
        try:
            if hasattr(message, "to_dict"):
                # Use the custom to_dict method if available
                message_data = message.to_dict()
            elif hasattr(message, "data") and hasattr(message, "type"):
                # Handle structured messages with data property
                message_data = message.data
            elif isinstance(message, dict):
                # Already a dictionary
                message_data = message
            else:
                # Convert to string if it's a simple type
                message_data = str(message)
        except Exception as e:
            logger.error("Error processing message data: %s", e)
            message_data = str(message)

        standard_message = {"type": message_type, "data": message_data}
        connection = self.get_connection(process_id)
        if connection:
            try:
                str_message = json.dumps(standard_message, default=str)
                await connection.send_text(str_message)
                logger.debug(f"Message sent to user {user_id} via process {process_id}")
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                # Clean up stale connection
                self.remove_connection(process_id)
        else:
            logger.warning(
                "No connection found for process ID: %s (user: %s)", process_id, user_id
            )
            # Clean up stale mapping
            if user_id in self.user_to_process:
                del self.user_to_process[user_id]

    def send_status_update(self, message: str, process_id: str):
        """Send a status update to a specific client (sync wrapper)."""
        process_id = str(process_id)
        connection = self.get_connection(process_id)
        if connection:
            try:
                # Use asyncio.create_task instead of run_coroutine_threadsafe
                asyncio.create_task(connection.send_text(message))
            except Exception as e:
                logger.error(f"Failed to send message to process {process_id}: {e}")
        else:
            logger.warning("No connection found for process ID: %s", process_id)


class TeamConfig:
    """Team configuration for agents."""

    def __init__(self):
        self.teams: Dict[str, TeamConfiguration] = {}

    def set_current_team(self, user_id: str, team_configuration: TeamConfiguration):
        """Add a new team configuration."""

        # To do: close current team of agents if any

        self.teams[user_id] = team_configuration

    def get_current_team(self, user_id: str) -> TeamConfiguration:
        """Get the current team configuration."""
        return self.teams.get(user_id, None)


# Global config instances
azure_config = AzureConfig()
mcp_config = MCPConfig()
orchestration_config = OrchestrationConfig()
connection_config = ConnectionConfig()
team_config = TeamConfig()

# Copyright (c) Microsoft. All rights reserved.
"""
WebSocket connection management and orchestration state configuration.

Extracted from v4/config/settings.py. Holds OrchestrationConfig, ConnectionConfig,
and TeamConfig — the three singletons imported together by the router.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from common.models.messages import TeamConfiguration
from fastapi import WebSocket
from models.messages import WebsocketMessageType
from models.plan_models import MPlan

logger = logging.getLogger(__name__)


class OrchestrationConfig:
    """Configuration and in-memory state for Magentic orchestration workflows."""

    def __init__(self):
        self.orchestrations: Dict[str, Any] = {}       # user_id -> workflow instance
        self.plans: Dict[str, MPlan] = {}              # plan_id -> plan details
        self.approvals: Dict[str, bool] = {}           # plan_id -> approval status (None = pending)
        self.sockets: Dict[str, WebSocket] = {}        # user_id -> WebSocket
        self.clarifications: Dict[str, str] = {}       # plan_id -> clarification response
        self.max_rounds: int = 10
        self.active_tasks: Dict[str, asyncio.Task] = {}  # user_id -> running asyncio.Task
        self.default_timeout: float = 300.0

        self._approval_events: Dict[str, asyncio.Event] = {}
        self._clarification_events: Dict[str, asyncio.Event] = {}

    def get_current_orchestration(self, user_id: str) -> Any:
        """Get existing orchestration workflow instance for user_id."""
        return self.orchestrations.get(user_id)

    # ------------------------------------------------------------------ #
    # Approval helpers
    # ------------------------------------------------------------------ #

    def set_approval_pending(self, plan_id: str) -> None:
        """Mark approval pending and create/reset its event."""
        self.approvals[plan_id] = None
        if plan_id not in self._approval_events:
            self._approval_events[plan_id] = asyncio.Event()
        else:
            self._approval_events[plan_id].clear()

    def set_approval_result(self, plan_id: str, approved: bool) -> None:
        """Set approval decision and trigger its event."""
        self.approvals[plan_id] = approved
        if plan_id in self._approval_events:
            self._approval_events[plan_id].set()

    async def wait_for_approval(self, plan_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for an approval decision with timeout.

        Raises:
            asyncio.TimeoutError: if timeout is exceeded.
            KeyError: if plan_id is not tracked.
        """
        logger.info("Waiting for approval: %s", plan_id)
        if timeout is None:
            timeout = self.default_timeout

        if plan_id not in self.approvals:
            raise KeyError(f"Plan ID {plan_id} not found in approvals")

        if self.approvals[plan_id] is not None:
            return self.approvals[plan_id]

        if plan_id not in self._approval_events:
            self._approval_events[plan_id] = asyncio.Event()

        try:
            await asyncio.wait_for(self._approval_events[plan_id].wait(), timeout=timeout)
            logger.info("Approval received: %s", plan_id)
            return self.approvals[plan_id]
        except asyncio.TimeoutError:
            logger.warning("Approval timeout: %s", plan_id)
            self.cleanup_approval(plan_id)
            raise
        except asyncio.CancelledError:
            logger.debug("Approval request %s was cancelled", plan_id)
            raise
        except Exception as e:
            logger.error("Unexpected error waiting for approval %s: %s", plan_id, e)
            raise
        finally:
            if plan_id in self.approvals and self.approvals[plan_id] is None:
                self.cleanup_approval(plan_id)

    def cleanup_approval(self, plan_id: str) -> None:
        """Remove approval tracking data and event."""
        self.approvals.pop(plan_id, None)
        self._approval_events.pop(plan_id, None)

    # ------------------------------------------------------------------ #
    # Clarification helpers
    # ------------------------------------------------------------------ #

    def set_clarification_pending(self, request_id: str) -> None:
        """Mark clarification pending and create/reset its event."""
        self.clarifications[request_id] = None
        if request_id not in self._clarification_events:
            self._clarification_events[request_id] = asyncio.Event()
        else:
            self._clarification_events[request_id].clear()

    def set_clarification_result(self, request_id: str, answer: str) -> None:
        """Set clarification answer and trigger event."""
        self.clarifications[request_id] = answer
        if request_id in self._clarification_events:
            self._clarification_events[request_id].set()

    async def wait_for_clarification(self, request_id: str, timeout: Optional[float] = None) -> str:
        """Wait for clarification response with timeout."""
        if timeout is None:
            timeout = self.default_timeout

        if request_id not in self.clarifications:
            raise KeyError(f"Request ID {request_id} not found in clarifications")

        if self.clarifications[request_id] is not None:
            return self.clarifications[request_id]

        if request_id not in self._clarification_events:
            self._clarification_events[request_id] = asyncio.Event()

        try:
            await asyncio.wait_for(self._clarification_events[request_id].wait(), timeout=timeout)
            return self.clarifications[request_id]
        except asyncio.TimeoutError:
            self.cleanup_clarification(request_id)
            raise
        except asyncio.CancelledError:
            logger.debug("Clarification request %s was cancelled", request_id)
            raise
        except Exception as e:
            logger.error("Unexpected error waiting for clarification %s: %s", request_id, e)
            raise
        finally:
            if request_id in self.clarifications and self.clarifications[request_id] is None:
                self.cleanup_clarification(request_id)

    def cleanup_clarification(self, request_id: str) -> None:
        """Remove clarification tracking data and event."""
        self.clarifications.pop(request_id, None)
        self._clarification_events.pop(request_id, None)


class ConnectionConfig:
    """WebSocket connection registry."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.user_to_process: Dict[str, str] = {}

    def add_connection(
        self, process_id: str, connection: WebSocket, user_id: str = None
    ) -> None:
        """Add or replace a connection for a process/user."""
        if process_id in self.connections:
            try:
                asyncio.create_task(self.connections[process_id].close())
            except Exception as e:
                logger.error(
                    "Error closing existing connection for process %s: %s", process_id, e
                )

        self.connections[process_id] = connection

        if user_id:
            user_id = str(user_id)
            old_process_id = self.user_to_process.get(user_id)
            if old_process_id and old_process_id != process_id:
                old_conn = self.connections.get(old_process_id)
                if old_conn:
                    try:
                        asyncio.create_task(old_conn.close())
                        del self.connections[old_process_id]
                        logger.info(
                            "Closed old connection %s for user %s", old_process_id, user_id
                        )
                    except Exception as e:
                        logger.error(
                            "Error closing old connection for user %s: %s", user_id, e
                        )

            self.user_to_process[user_id] = process_id
            logger.info(
                "WebSocket connection added for process: %s (user: %s)", process_id, user_id
            )
        else:
            logger.info("WebSocket connection added for process: %s", process_id)

    def remove_connection(self, process_id: str) -> None:
        """Remove a connection and associated user mapping."""
        process_id = str(process_id)
        self.connections.pop(process_id, None)
        for user_id, mapped in list(self.user_to_process.items()):
            if mapped == process_id:
                del self.user_to_process[user_id]
                logger.debug("Removed user mapping: %s -> %s", user_id, process_id)
                break

    def get_connection(self, process_id: str) -> Optional[WebSocket]:
        """Fetch a connection by process_id."""
        return self.connections.get(process_id)

    async def close_connection(self, process_id: str) -> None:
        """Close and remove a connection by process_id."""
        connection = self.get_connection(process_id)
        if connection:
            try:
                await connection.close()
                logger.info("Connection closed for process ID: %s", process_id)
            except Exception as e:
                logger.error("Error closing connection for %s: %s", process_id, e)
        else:
            logger.warning("No connection found for process ID: %s", process_id)

        self.remove_connection(process_id)

    async def send_status_update_async(
        self,
        message: Any,
        user_id: str,
        message_type: WebsocketMessageType = WebsocketMessageType.SYSTEM_MESSAGE,
    ) -> None:
        """Send a status update to a user via its mapped process connection."""
        if not user_id:
            logger.warning("No user_id provided for WebSocket message")
            return

        process_id = self.user_to_process.get(user_id)
        if not process_id:
            # Fallback: the LLM may have passed a wrong user_id (e.g. "default",
            # "USER").  If there is exactly one connected user, use that instead.
            if len(self.user_to_process) == 1:
                fallback_user_id = next(iter(self.user_to_process))
                logger.warning(
                    "No WebSocket for user_id '%s' — falling back to sole "
                    "connected user '%s'",
                    user_id,
                    fallback_user_id,
                )
                process_id = self.user_to_process[fallback_user_id]
            else:
                logger.warning(
                    "No active WebSocket process found for user ID: %s", user_id
                )
                return

        try:
            if hasattr(message, "to_dict"):
                message_data = message.to_dict()
            elif isinstance(message, dict):
                message_data = message
            else:
                message_data = str(message)
        except Exception as e:
            logger.error("Error processing message data: %s", e)
            message_data = str(message)

        payload = {"type": message_type, "data": message_data}
        connection = self.get_connection(process_id)
        if connection:
            try:
                await connection.send_text(json.dumps(payload, default=str))
                logger.debug(
                    "Message sent to user %s via process %s", user_id, process_id
                )
            except Exception as e:
                logger.error("Failed to send message to user %s: %s", user_id, e)
                self.remove_connection(process_id)
        else:
            logger.warning(
                "No connection found for process ID: %s (user: %s)", process_id, user_id
            )
            self.user_to_process.pop(user_id, None)

    def send_status_update(self, message: str, process_id: str) -> None:
        """Sync helper to send a message by process_id."""
        process_id = str(process_id)
        connection = self.get_connection(process_id)
        if connection:
            try:
                asyncio.create_task(connection.send_text(message))
            except Exception as e:
                logger.error(
                    "Failed to send message to process %s: %s", process_id, e
                )
        else:
            logger.warning("No connection found for process ID: %s", process_id)


class TeamConfig:
    """Per-user team configuration store."""

    def __init__(self):
        self._teams: Dict[str, TeamConfiguration] = {}

    def set_current_team(
        self, user_id: str, team_configuration: TeamConfiguration
    ) -> None:
        """Store current team configuration for user."""
        self._teams[user_id] = team_configuration

    def get_current_team(self, user_id: str) -> Optional[TeamConfiguration]:
        """Retrieve current team configuration for user."""
        return self._teams.get(user_id)


# Module-level singletons
orchestration_config = OrchestrationConfig()
connection_config = ConnectionConfig()
team_config = TeamConfig()

"""
WebSocket endpoint for real-time plan execution streaming
This is a basic implementation that can be expanded based on your backend framework
"""

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.plan_subscriptions: Dict[str, Set[str]] = {}  # plan_id -> set of connection_ids

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connection established: {connection_id}")

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Remove from all plan subscriptions
        for plan_id, subscribers in self.plan_subscriptions.items():
            subscribers.discard(connection_id)

        logger.info(f"WebSocket connection closed: {connection_id}")

    async def send_personal_message(self, message: dict, connection_id: str):
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)

    async def broadcast_to_plan(self, message: dict, plan_id: str):
        """Broadcast message to all subscribers of a specific plan"""
        if plan_id not in self.plan_subscriptions:
            return

        disconnected_connections = []

        for connection_id in self.plan_subscriptions[plan_id].copy():
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection_id}: {e}")
                    disconnected_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in disconnected_connections:
            self.disconnect(connection_id)

    def subscribe_to_plan(self, connection_id: str, plan_id: str):
        if plan_id not in self.plan_subscriptions:
            self.plan_subscriptions[plan_id] = set()

        self.plan_subscriptions[plan_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to plan {plan_id}")

    def unsubscribe_from_plan(self, connection_id: str, plan_id: str):
        if plan_id in self.plan_subscriptions:
            self.plan_subscriptions[plan_id].discard(connection_id)
            logger.info(f"Connection {connection_id} unsubscribed from plan {plan_id}")


# Global WebSocket manager instance
ws_manager = WebSocketManager()


# WebSocket endpoint
async def websocket_streaming_endpoint(websocket: WebSocket):
    connection_id = f"conn_{id(websocket)}"
    await ws_manager.connect(websocket, connection_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            message_type = message.get("type")

            if message_type == "subscribe_plan":
                plan_id = message.get("plan_id")
                if plan_id:
                    ws_manager.subscribe_to_plan(connection_id, plan_id)

                    # Send confirmation
                    await ws_manager.send_personal_message(
                        {"type": "subscription_confirmed", "plan_id": plan_id},
                        connection_id,
                    )

            elif message_type == "unsubscribe_plan":
                plan_id = message.get("plan_id")
                if plan_id:
                    ws_manager.unsubscribe_from_plan(connection_id, plan_id)

            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        ws_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(connection_id)


# Example function to send plan updates (call this from your plan execution logic)
async def send_plan_update(
    plan_id: str,
    step_id: str = None,
    agent_name: str = None,
    content: str = None,
    status: str = "in_progress",
    message_type: str = "action",
):
    """
    Send a streaming update for a specific plan
    """
    message = {
        "type": "plan_update",
        "data": {
            "plan_id": plan_id,
            "step_id": step_id,
            "agent_name": agent_name,
            "content": content,
            "status": status,
            "message_type": message_type,
            "timestamp": asyncio.get_event_loop().time(),
        },
    }

    await ws_manager.broadcast_to_plan(message, plan_id)


# Example function to send agent messages
async def send_agent_message(
    plan_id: str, agent_name: str, content: str, message_type: str = "thinking"
):
    """
    Send a streaming message from an agent
    """
    message = {
        "type": "agent_message",
        "data": {
            "plan_id": plan_id,
            "agent_name": agent_name,
            "content": content,
            "message_type": message_type,
            "timestamp": asyncio.get_event_loop().time(),
        },
    }

    await ws_manager.broadcast_to_plan(message, plan_id)


# Example function to send step updates
async def send_step_update(
    plan_id: str, step_id: str, status: str, content: str = None
):
    """
    Send a streaming update for a specific step
    """
    message = {
        "type": "step_update",
        "data": {
            "plan_id": plan_id,
            "step_id": step_id,
            "status": status,
            "content": content,
            "timestamp": asyncio.get_event_loop().time(),
        },
    }

    await ws_manager.broadcast_to_plan(message, plan_id)


# Example integration with FastAPI
"""
from fastapi import FastAPI

app = FastAPI()

@app.websocket("/ws/streaming")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_streaming_endpoint(websocket)

# Example usage in your plan execution logic:
async def execute_plan_step(plan_id: str, step_id: str):
    # Send initial update
    await send_step_update(plan_id, step_id, "in_progress", "Starting step execution...")
    # Simulate some work
    await asyncio.sleep(2)
    # Send agent thinking message
    await send_agent_message(plan_id, "Data Analyst", "Analyzing the requirements...", "thinking")
    await asyncio.sleep(1)
    # Send agent action message
    await send_agent_message(plan_id, "Data Analyst", "Processing data and generating insights...", "action")
    await asyncio.sleep(3)
    # Send completion update
    await send_step_update(plan_id, step_id, "completed", "Step completed successfully!")
"""

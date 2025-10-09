"""
Enhanced response callbacks for employee onboarding agent system.
Provides detailed monitoring and response handling for different agent types.
"""

import asyncio
import logging
import time

from semantic_kernel.contents import ChatMessageContent, StreamingChatMessageContent
from v3.config.settings import connection_config
from v3.models.messages import (
    AgentMessage,
    AgentMessageStreaming,
    AgentToolCall,
    AgentToolMessage,
    WebsocketMessageType,
)


def agent_response_callback(message: ChatMessageContent, user_id: str = None) -> None:
    """Observer function to print detailed information about streaming messages."""
    # import sys

    # Get agent name to determine handling
    agent_name = message.name or "Unknown Agent"

    role = getattr(message, "role", "unknown")

    # Send to WebSocket
    if user_id:
        try:
            if message.items and message.items[0].content_type == "function_call":
                final_message = AgentToolMessage(agent_name=agent_name)
                for item in message.items:
                    if item.content_type == "function_call":
                        tool_call = AgentToolCall(
                            tool_name=item.name or "unknown_tool",
                            arguments=item.arguments or {},
                        )
                        final_message.tool_calls.append(tool_call)

                asyncio.create_task(
                    connection_config.send_status_update_async(
                        final_message,
                        user_id,
                        message_type=WebsocketMessageType.AGENT_TOOL_MESSAGE,
                    )
                )
                logging.info(f"Function call: {final_message}")
            elif message.items and message.items[0].content_type == "function_result":
                # skip returning these results for now - agent will return in a later message
                pass
            else:
                final_message = AgentMessage(
                    agent_name=agent_name,
                    timestamp=time.time() or "",
                    content=message.content or "",
                )

                asyncio.create_task(
                    connection_config.send_status_update_async(
                        final_message,
                        user_id,
                        message_type=WebsocketMessageType.AGENT_MESSAGE,
                    )
                )
                logging.info(f"{role.capitalize()} message: {final_message}")
        except Exception as e:
            logging.error(f"Response_callback: Error sending WebSocket message: {e}")


async def streaming_agent_response_callback(
    streaming_message: StreamingChatMessageContent, is_final: bool, user_id: str = None
) -> None:
    """Simple streaming callback to show real-time agent responses."""
    # process only content messages
    if hasattr(streaming_message, "content") and streaming_message.content:
        if user_id:
            try:
                message = AgentMessageStreaming(
                    agent_name=streaming_message.name or "Unknown Agent",
                    content=streaming_message.content,
                    is_final=is_final,
                )
                await connection_config.send_status_update_async(
                    message,
                    user_id,
                    message_type=WebsocketMessageType.AGENT_MESSAGE_STREAMING,
                )
            except Exception as e:
                logging.error(
                    f"Response_callback: Error sending streaming WebSocket message: {e}"
                )

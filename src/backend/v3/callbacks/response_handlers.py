"""
Enhanced response callbacks for employee onboarding agent system.
Provides detailed monitoring and response handling for different agent types.
"""

import asyncio
import logging
import time
import re
from semantic_kernel.contents import ChatMessageContent, StreamingChatMessageContent
from v3.config.settings import connection_config
from v3.models.messages import (
    AgentMessage,
    AgentMessageStreaming,
    AgentToolCall,
    AgentToolMessage,
    WebsocketMessageType,
)

logger = logging.getLogger(__name__)


def clean_citations(text: str) -> str:
    """Remove citation markers from agent responses while preserving formatting."""
    if not text:
        return text

    # Remove citation patterns like [9:0|source], [9:1|source], etc.
    text = re.sub(r'\[\d+:\d+\|source\]', '', text)

    # Remove other common citation pattern
    text = re.sub(r'\[\s*source\s*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'【[^】]*】', '', text)  # Unicode brackets
    text = re.sub(r'\(source:[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[source:[^\]]*\]', '', text, flags=re.IGNORECASE)

    return text


def agent_response_callback(message: ChatMessageContent, user_id: str = None) -> None:
    """Observer function to print detailed information about streaming messages."""
    # import sys

    # Get agent name to determine handling
    agent_name = message.name or "Unknown Agent"

    logger.info(f"🤖 Agent Response from '{agent_name}' for user: {user_id}")

    role = getattr(message, "role", "unknown")

    # Send to WebSocket
    if user_id:
        try:
            if message.items and message.items[0].content_type == "function_call":
                logger.info(f" Message content_type: {message.items[0].content_type}")
                logger.info(f"🔧 Tool calls detected from agent: {agent_name}")
                final_message = AgentToolMessage(agent_name=agent_name)
                for item in message.items:
                    if item.content_type == "function_call":
                        tool_name = item.name or "unknown_tool"
                        tool_args = item.arguments or {}
                        logger.info(f"🛠️ Tool call: {tool_name} with args: {str(tool_args)[:200]}...")

                        tool_call = AgentToolCall(
                            tool_name=tool_name,
                            arguments=tool_args,
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
                # Log function results for debugging
                logger.info(f" Message content_type: {message.items[0].content_type}")
                logger.info(f"📥 Function result received from agent: {agent_name}")
                for item in message.items:
                    if item.content_type == "function_result":
                        result_content = str(item.result)[:300] if hasattr(item, 'result') else "No result"
                        logger.info(f"🔍 Function result: {result_content}...")
                # skip returning these results for now - agent will return in a later message
                pass
            else:
                logger.info(f" Message content_type: {message.items[0].content_type}")
                logger.info(f"💬 Text message from agent: {agent_name}")
                final_message = AgentMessage(
                    agent_name=agent_name,
                    timestamp=time.time() or "",
                    content=clean_citations(message.content) or "",
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
                    content=clean_citations(streaming_message.content),
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

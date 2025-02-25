import pytest
from unittest.mock import Mock
from src.backend.handlers.runtime_interrupt import (
    NeedsUserInputHandler,
    AssistantResponseHandler,
)
from src.backend.models.messages import GetHumanInputMessage, GroupChatMessage
from autogen_core.base import AgentId


@pytest.mark.asyncio
async def test_needs_user_input_handler_on_publish_human_input():
    """Test on_publish with GetHumanInputMessage."""
    handler = NeedsUserInputHandler()

    mock_message = Mock(spec=GetHumanInputMessage)
    mock_message.content = "This is a question for the human."

    mock_sender = Mock(spec=AgentId)
    mock_sender.type = "human_agent"
    mock_sender.key = "human_key"

    await handler.on_publish(mock_message, sender=mock_sender)

    assert handler.needs_human_input is True
    assert handler.question_content == "This is a question for the human."
    assert len(handler.messages) == 1
    assert handler.messages[0]["agent"]["type"] == "human_agent"
    assert handler.messages[0]["agent"]["key"] == "human_key"
    assert handler.messages[0]["content"] == "This is a question for the human."


@pytest.mark.asyncio
async def test_needs_user_input_handler_on_publish_group_chat():
    """Test on_publish with GroupChatMessage."""
    handler = NeedsUserInputHandler()

    mock_message = Mock(spec=GroupChatMessage)
    mock_message.body = Mock(content="This is a group chat message.")

    mock_sender = Mock(spec=AgentId)
    mock_sender.type = "group_agent"
    mock_sender.key = "group_key"

    await handler.on_publish(mock_message, sender=mock_sender)

    assert len(handler.messages) == 1
    assert handler.messages[0]["agent"]["type"] == "group_agent"
    assert handler.messages[0]["agent"]["key"] == "group_key"
    assert handler.messages[0]["content"] == "This is a group chat message."


@pytest.mark.asyncio
async def test_needs_user_input_handler_get_messages():
    """Test get_messages method."""
    handler = NeedsUserInputHandler()

    # Add mock messages
    mock_message = Mock(spec=GroupChatMessage)
    mock_message.body = Mock(content="Group chat content.")
    mock_sender = Mock(spec=AgentId)
    mock_sender.type = "group_agent"
    mock_sender.key = "group_key"

    await handler.on_publish(mock_message, sender=mock_sender)

    # Retrieve messages
    messages = handler.get_messages()

    assert len(messages) == 1
    assert messages[0]["agent"]["type"] == "group_agent"
    assert messages[0]["agent"]["key"] == "group_key"
    assert messages[0]["content"] == "Group chat content."
    assert len(handler.messages) == 0  # Ensure messages are cleared


def test_needs_user_input_handler_properties():
    """Test properties of NeedsUserInputHandler."""
    handler = NeedsUserInputHandler()

    # Initially no human input
    assert handler.needs_human_input is False
    assert handler.question_content is None

    # Add a question
    mock_message = Mock(spec=GetHumanInputMessage)
    mock_message.content = "Human question?"
    handler.question_for_human = mock_message

    assert handler.needs_human_input is True
    assert handler.question_content == "Human question?"


@pytest.mark.asyncio
async def test_assistant_response_handler_on_publish():
    """Test on_publish in AssistantResponseHandler."""
    handler = AssistantResponseHandler()

    mock_message = Mock()
    mock_message.body = Mock(content="Assistant response content.")

    mock_sender = Mock(spec=AgentId)
    mock_sender.type = "writer"
    mock_sender.key = "assistant_key"

    await handler.on_publish(mock_message, sender=mock_sender)

    assert handler.has_response is True
    assert handler.get_response() == "Assistant response content."


def test_assistant_response_handler_properties():
    """Test properties of AssistantResponseHandler."""
    handler = AssistantResponseHandler()

    # Initially no response
    assert handler.has_response is False
    assert handler.get_response() is None

    # Set a response
    handler.assistant_response = "Assistant response"

    assert handler.has_response is True
    assert handler.get_response() == "Assistant response"

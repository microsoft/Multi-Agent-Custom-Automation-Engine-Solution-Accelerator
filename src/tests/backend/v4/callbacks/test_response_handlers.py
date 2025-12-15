"""
Unit tests for v4 response_handlers module.

Tests cover:
- Citation cleaning functionality
- Function call detection and extraction
- Agent response callback (non-streaming)
- Streaming agent response callback
- Error handling for WebSocket communications
- Edge cases and boundary conditions
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import sys
import os
from pathlib import Path
import types

# Mock environment variables before any imports
os.environ['APPLICATIONINSIGHTS_CONNECTION_STRING'] = 'mock_connection_string'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://mock.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'mock_api_key'
os.environ['AZURE_OPENAI_API_VERSION'] = '2023-12-01-preview'
os.environ['AZURE_COSMOS_DB_ENDPOINT'] = 'https://mock.cosmos.azure.com'
os.environ['AZURE_COSMOS_DB_KEY'] = 'mock_cosmos_key'

# Mock agent_framework before any imports
agent_framework = types.ModuleType('agent_framework')
agent_framework.ChatMessage = type('ChatMessage', (), {})
agent_framework.ChatAgent = type('ChatAgent', (), {})
agent_framework.Role = type('Role', (), {'USER': 'user', 'ASSISTANT': 'assistant'})

# Create temporary mocks for agent_framework (only during this test file execution)
import types
agent_framework = types.ModuleType('agent_framework')
agent_framework.ChatMessage = type('ChatMessage', (), {})  # Add missing ChatMessage class
workflows_module = types.ModuleType('agent_framework._workflows')
magentic_module = types.ModuleType('agent_framework._workflows._magentic')
magentic_module.AgentRunResponseUpdate = type('AgentRunResponseUpdate', (), {})
workflows_module._magentic = magentic_module
agent_framework._workflows = workflows_module

# Mock fastapi module
mock_fastapi = types.ModuleType('fastapi')
mock_fastapi.WebSocket = type('WebSocket', (), {})

# REMOVED: sys.modules pollution that causes isinstance() failures across test files
# Each test should use @patch decorators for its specific mocking needs

# Set required environment variables for testing
os.environ.setdefault('AZURE_AI_SUBSCRIPTION_ID', 'test_subscription_id')
os.environ.setdefault('AZURE_AI_RESOURCE_GROUP', 'test_resource_group')
os.environ.setdefault('AZURE_AI_PROJECT_NAME', 'test_project_name')
os.environ.setdefault('AZURE_AI_AGENT_ENDPOINT', 'https://test.agent.azure.com/')
os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com/')
os.environ.setdefault('AZURE_OPENAI_API_KEY', 'test_key')
os.environ.setdefault('AZURE_OPENAI_DEPLOYMENT_NAME', 'test_deployment')
os.environ.setdefault('AZURE_OPENAI_RAI_DEPLOYMENT_NAME', 'test_rai_deployment')
os.environ.setdefault('APP_ENV', 'dev')

# Add proper mocking for imports without global pollution
if 'agent_framework._workflows' not in sys.modules:
    workflows_module = types.ModuleType('agent_framework._workflows')
    workflows_module._magentic = types.ModuleType('agent_framework._workflows._magentic')
    workflows_module._magentic.AgentRunResponseUpdate = type('AgentRunResponseUpdate', (), {})
    sys.modules['agent_framework._workflows'] = workflows_module
    sys.modules['agent_framework._workflows._magentic'] = workflows_module._magentic

# Add agent_framework base module with ChatOptions and ChatMessage
if 'agent_framework' not in sys.modules:
    agent_framework_module = types.ModuleType('agent_framework')
    agent_framework_module.ChatOptions = type('ChatOptions', (), {'__init__': lambda self, *args, **kwargs: None})
    agent_framework_module.ChatMessage = type('ChatMessage', (), {'__init__': lambda self, *args, **kwargs: None})
    sys.modules['agent_framework'] = agent_framework_module

# Add agent_framework.azure mock for settings import
if 'agent_framework.azure' not in sys.modules:
    azure_module = types.ModuleType('agent_framework.azure')
    azure_module.AzureOpenAIChatClient = type('AzureOpenAIChatClient', (), {})
    sys.modules['agent_framework.azure'] = azure_module
    sys.modules['agent_framework'].azure = azure_module

# Add the backend path to sys.path for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from v4.callbacks.response_handlers import (
    clean_citations,
    _is_function_call_item,
    _extract_tool_calls_from_contents,
    agent_response_callback,
    streaming_agent_response_callback,
)
from v4.models.messages import (
    AgentMessage,
    AgentMessageStreaming,
    AgentToolCall,
    AgentToolMessage,
    WebsocketMessageType,
)

# Filter out ResourceWarning messages
pytestmark = pytest.mark.filterwarnings("ignore::ResourceWarning")


class TestCleanCitations:
    """Test cases for clean_citations function."""

    def test_clean_citations_empty_string(self):
        """Test citation cleaning with empty string."""
        result = clean_citations("")
        assert result == ""

    def test_clean_citations_none_input(self):
        """Test citation cleaning with None input."""
        result = clean_citations(None)
        assert result is None

    def test_clean_citations_no_citations(self):
        """Test citation cleaning with text containing no citations."""
        text = "This is a simple text without any citations."
        result = clean_citations(text)
        assert result == text

    def test_clean_citations_numbered_source_format(self):
        """Test removing [1:2|source] style citations."""
        text = "This is a test[1:2|source] with citations[3:4|source]."
        result = clean_citations(text)
        assert result == "This is a test with citations."
        assert "[1:2|source]" not in result
        assert "[3:4|source]" not in result

    def test_clean_citations_source_keyword(self):
        """Test removing [source] style citations."""
        text = "Information here[source] and more[SOURCE]."
        result = clean_citations(text)
        assert result == "Information here and more."
        assert "[source]" not in result.lower()

    def test_clean_citations_numbered_brackets(self):
        """Test removing [1] style citations."""
        text = "Reference one[1] and reference two[2]."
        result = clean_citations(text)
        assert result == "Reference one and reference two."
        assert "[1]" not in result
        assert "[2]" not in result

    def test_clean_citations_unicode_brackets(self):
        """Test removing 【citation】 style citations."""
        text = "Some text【citation here】with unicode markers【another】."
        result = clean_citations(text)
        # The regex removes everything between unicode brackets including the space before "with"
        assert result == "Some textwith unicode markers."
        assert "【" not in result
        assert "】" not in result

    def test_clean_citations_source_with_parentheses(self):
        """Test removing (source:...) style citations."""
        text = "Data from report(source:report.pdf) and another(SOURCE:data.xlsx)."
        result = clean_citations(text)
        assert result == "Data from report and another."
        assert "(source:" not in result.lower()

    def test_clean_citations_source_with_square_brackets(self):
        """Test removing [source:...] style citations."""
        text = "According to study[source:study.pdf] findings[SOURCE:report.doc]."
        result = clean_citations(text)
        assert result == "According to study findings."
        assert "[source:" not in result.lower()

    def test_clean_citations_multiple_types(self):
        """Test removing multiple citation types in one text."""
        text = "Text[1] with various[source] citations[2:3|source]【ref】(source:doc.pdf)."
        result = clean_citations(text)
        assert "[1]" not in result
        assert "[source]" not in result
        assert "[2:3|source]" not in result
        assert "【ref】" not in result
        assert "(source:doc.pdf)" not in result

    def test_clean_citations_preserves_formatting(self):
        """Test that citation cleaning preserves text formatting."""
        text = "Start\nNewline[1] text\t\tTabs[source] end."
        result = clean_citations(text)
        assert "\n" in result
        assert "\t" in result
        assert result == "Start\nNewline text\t\tTabs end."

    def test_clean_citations_whitespace_handling(self):
        """Test citation cleaning with various whitespace."""
        text = "Text [  source  ] with spaces."
        result = clean_citations(text)
        assert "[  source  ]" not in result


class TestIsFunctionCallItem:
    """Test cases for _is_function_call_item function."""

    def test_is_function_call_none_input(self):
        """Test function call detection with None input."""
        result = _is_function_call_item(None)
        assert result is False

    def test_is_function_call_with_content_type(self):
        """Test function call detection with content_type attribute."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        
        result = _is_function_call_item(mock_item)
        assert result is True

    def test_is_function_call_with_name_and_arguments(self):
        """Test function call detection with name and arguments attributes."""
        mock_item = Mock()
        mock_item.name = "test_function"
        mock_item.arguments = {"arg1": "value1"}
        delattr(mock_item, "text")  # Ensure no text attribute
        
        result = _is_function_call_item(mock_item)
        assert result is True

    def test_is_function_call_with_text_attribute(self):
        """Test function call detection fails when text attribute exists."""
        mock_item = Mock()
        mock_item.name = "test_function"
        mock_item.arguments = {"arg1": "value1"}
        mock_item.text = "Some text"
        
        result = _is_function_call_item(mock_item)
        assert result is False

    def test_is_function_call_missing_attributes(self):
        """Test function call detection with missing attributes."""
        mock_item = Mock()
        
        result = _is_function_call_item(mock_item)
        assert result is False

    def test_is_function_call_wrong_content_type(self):
        """Test function call detection with wrong content_type."""
        mock_item = Mock()
        mock_item.content_type = "text"
        
        result = _is_function_call_item(mock_item)
        assert result is False


class TestExtractToolCallsFromContents:
    """Test cases for _extract_tool_calls_from_contents function."""

    def test_extract_tool_calls_empty_list(self):
        """Test tool extraction with empty contents list."""
        result = _extract_tool_calls_from_contents([])
        assert result == []
        assert isinstance(result, list)

    def test_extract_tool_calls_no_function_items(self):
        """Test tool extraction with no function call items."""
        mock_item1 = Mock()
        mock_item1.text = "Regular text"
        mock_item2 = Mock()
        mock_item2.content_type = "text"
        
        result = _extract_tool_calls_from_contents([mock_item1, mock_item2])
        assert result == []

    def test_extract_tool_calls_single_function(self):
        """Test tool extraction with single function call."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        mock_item.name = "get_employee_info"
        mock_item.arguments = {"employee_id": "123"}
        
        result = _extract_tool_calls_from_contents([mock_item])
        
        assert len(result) == 1
        assert isinstance(result[0], AgentToolCall)
        assert result[0].tool_name == "get_employee_info"
        assert result[0].arguments == {"employee_id": "123"}

    def test_extract_tool_calls_multiple_functions(self):
        """Test tool extraction with multiple function calls."""
        mock_item1 = Mock()
        mock_item1.content_type = "function_call"
        mock_item1.name = "function_one"
        mock_item1.arguments = {"arg1": "val1"}
        
        mock_item2 = Mock()
        mock_item2.content_type = "function_call"
        mock_item2.name = "function_two"
        mock_item2.arguments = {"arg2": "val2"}
        
        result = _extract_tool_calls_from_contents([mock_item1, mock_item2])
        
        assert len(result) == 2
        assert result[0].tool_name == "function_one"
        assert result[1].tool_name == "function_two"

    def test_extract_tool_calls_mixed_content(self):
        """Test tool extraction with mixed content types."""
        mock_text = Mock()
        mock_text.text = "Some text"
        
        mock_function = Mock()
        mock_function.content_type = "function_call"
        mock_function.name = "test_func"
        mock_function.arguments = {}
        
        result = _extract_tool_calls_from_contents([mock_text, mock_function, mock_text])
        
        assert len(result) == 1
        assert result[0].tool_name == "test_func"

    def test_extract_tool_calls_missing_name(self):
        """Test tool extraction with missing name attribute."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        delattr(mock_item, "name")
        mock_item.arguments = {}
        
        result = _extract_tool_calls_from_contents([mock_item])
        
        assert len(result) == 1
        assert result[0].tool_name == "unknown_tool"

    def test_extract_tool_calls_missing_arguments(self):
        """Test tool extraction with missing arguments attribute."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        mock_item.name = "test_function"
        delattr(mock_item, "arguments")
        
        result = _extract_tool_calls_from_contents([mock_item])
        
        assert len(result) == 1
        assert result[0].arguments == {}

    def test_extract_tool_calls_none_arguments(self):
        """Test tool extraction with None arguments."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        mock_item.name = "test_function"
        mock_item.arguments = None
        
        result = _extract_tool_calls_from_contents([mock_item])
        
        assert len(result) == 1
        assert result[0].arguments == {}


class TestAgentResponseCallback:
    """Test cases for agent_response_callback function."""

    @pytest.fixture
    def mock_chat_message(self):
        """Create a mock ChatMessage object."""
        mock_msg = Mock()
        mock_msg.author_name = "TestAgent"
        mock_msg.role = "assistant"
        mock_msg.text = "This is a test response"
        return mock_msg

    @pytest.fixture
    def mock_connection_config(self):
        """Mock connection_config for WebSocket communication."""
        with patch("v4.callbacks.response_handlers.connection_config") as mock:
            mock.send_status_update_async = AsyncMock()
            yield mock

    def test_agent_response_callback_no_user_id(self, mock_chat_message, mock_connection_config):
        """Test agent response callback without user_id."""
        agent_response_callback("agent-123", mock_chat_message, user_id=None)
        
        # Should not send WebSocket message
        mock_connection_config.send_status_update_async.assert_not_called()

    def test_agent_response_callback_success(self, mock_chat_message, mock_connection_config):
        """Test successful agent response callback."""
        agent_response_callback("agent-123", mock_chat_message, user_id="user-456")
        
        # Verify WebSocket message was sent
        mock_connection_config.send_status_update_async.assert_called_once()
        
        # Verify message content
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        user_id = call_args[0][1]
        message_type = call_args[1]["message_type"]
        
        assert isinstance(sent_message, AgentMessage)
        assert sent_message.agent_name == "TestAgent"
        assert sent_message.content == "This is a test response"
        assert user_id == "user-456"
        assert message_type == WebsocketMessageType.AGENT_MESSAGE

    def test_agent_response_callback_with_citations(self, mock_connection_config):
        """Test agent response callback removes citations."""
        mock_msg = Mock()
        mock_msg.author_name = "TestAgent"
        mock_msg.role = "assistant"
        mock_msg.text = "Response with citation[1] and [source]."
        
        agent_response_callback("agent-123", mock_msg, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert "[1]" not in sent_message.content
        assert "[source]" not in sent_message.content
        assert sent_message.content == "Response with citation and ."

    def test_agent_response_callback_fallback_agent_name(self, mock_connection_config):
        """Test agent response callback with missing author_name."""
        mock_msg = Mock()
        mock_msg.role = "assistant"
        mock_msg.text = "Test response"
        delattr(mock_msg, "author_name")
        
        agent_response_callback("fallback-agent", mock_msg, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert sent_message.agent_name == "fallback-agent"

    def test_agent_response_callback_non_chat_message(self, mock_connection_config):
        """Test agent response callback with non-ChatMessage object."""
        mock_msg = Mock()
        mock_msg.author_name = "TestAgent"
        mock_msg.role = "assistant"
        mock_msg.text = "Direct text attribute"
        # Remove the ChatMessage type check
        type(mock_msg).__name__ = "SomeOtherMessage"
        
        agent_response_callback("agent-123", mock_msg, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert sent_message.content == "Direct text attribute"

    def test_agent_response_callback_empty_text(self, mock_connection_config):
        """Test agent response callback with empty text."""
        mock_msg = Mock()
        mock_msg.author_name = "TestAgent"
        mock_msg.role = "assistant"
        mock_msg.text = ""
        
        agent_response_callback("agent-123", mock_msg, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert sent_message.content == ""

    def test_agent_response_callback_websocket_error(self, mock_chat_message):
        """Test agent response callback handles WebSocket errors gracefully."""
        with patch("v4.callbacks.response_handlers.connection_config") as mock_config:
            mock_config.send_status_update_async = AsyncMock(
                side_effect=Exception("WebSocket error")
            )
            
            # Should not raise exception
            agent_response_callback("agent-123", mock_chat_message, user_id="user-456")

    def test_agent_response_callback_timestamp(self, mock_chat_message, mock_connection_config):
        """Test agent response callback includes timestamp."""
        before = time.time()
        agent_response_callback("agent-123", mock_chat_message, user_id="user-456")
        after = time.time()
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert before <= sent_message.timestamp <= after


class TestStreamingAgentResponseCallback:
    """Test cases for streaming_agent_response_callback function."""

    @pytest.fixture
    def mock_update(self):
        """Create a mock AgentRunResponseUpdate object."""
        mock = Mock()
        mock.text = "Streaming text chunk"
        mock.contents = []
        return mock

    @pytest.fixture
    def mock_connection_config(self):
        """Mock connection_config for WebSocket communication."""
        with patch("v4.callbacks.response_handlers.connection_config") as mock:
            mock.send_status_update_async = AsyncMock()
            yield mock

    @pytest.mark.asyncio
    async def test_streaming_callback_no_user_id(self, mock_update, mock_connection_config):
        """Test streaming callback without user_id."""
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id=None)
        
        mock_connection_config.send_status_update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_streaming_callback_success(self, mock_update, mock_connection_config):
        """Test successful streaming callback."""
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        mock_connection_config.send_status_update_async.assert_called_once()
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        user_id = call_args[0][1]
        message_type = call_args[1]["message_type"]
        
        assert isinstance(sent_message, AgentMessageStreaming)
        assert sent_message.agent_name == "agent-123"
        assert sent_message.content == "Streaming text chunk"
        assert sent_message.is_final is False
        assert user_id == "user-456"
        assert message_type == WebsocketMessageType.AGENT_MESSAGE_STREAMING

    @pytest.mark.asyncio
    async def test_streaming_callback_final_message(self, mock_update, mock_connection_config):
        """Test streaming callback with final message."""
        await streaming_agent_response_callback("agent-123", mock_update, True, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert sent_message.is_final is True

    @pytest.mark.asyncio
    async def test_streaming_callback_no_direct_text(self, mock_connection_config):
        """Test streaming callback extracts text from contents."""
        mock_update = Mock()
        delattr(mock_update, "text")
        
        mock_content1 = Mock()
        mock_content1.text = "First "
        mock_content2 = Mock()
        mock_content2.text = "Second"
        
        mock_update.contents = [mock_content1, mock_content2]
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert sent_message.content == "First Second"

    @pytest.mark.asyncio
    async def test_streaming_callback_with_tool_calls(self, mock_connection_config):
        """Test streaming callback with tool calls."""
        mock_update = Mock()
        mock_update.text = "Some text"
        
        mock_tool = Mock()
        mock_tool.content_type = "function_call"
        mock_tool.name = "test_tool"
        mock_tool.arguments = {"arg": "value"}
        
        mock_update.contents = [mock_tool]
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        # Should send two messages: tool message and streaming message
        assert mock_connection_config.send_status_update_async.call_count == 2
        
        # First call should be tool message
        first_call = mock_connection_config.send_status_update_async.call_args_list[0]
        tool_message = first_call[0][0]
        assert isinstance(tool_message, AgentToolMessage)
        assert len(tool_message.tool_calls) == 1
        assert tool_message.tool_calls[0].tool_name == "test_tool"

    @pytest.mark.asyncio
    async def test_streaming_callback_with_citations(self, mock_connection_config):
        """Test streaming callback removes citations."""
        mock_update = Mock()
        mock_update.text = "Text with citation[1] and [source]."
        mock_update.contents = []
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        call_args = mock_connection_config.send_status_update_async.call_args
        sent_message = call_args[0][0]
        
        assert "[1]" not in sent_message.content
        assert "[source]" not in sent_message.content

    @pytest.mark.asyncio
    async def test_streaming_callback_empty_text(self, mock_connection_config):
        """Test streaming callback with empty text."""
        mock_update = Mock()
        mock_update.text = ""
        mock_update.contents = []
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        # Should not send message if text is empty
        mock_connection_config.send_status_update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_streaming_callback_only_tool_calls(self, mock_connection_config):
        """Test streaming callback with only tool calls, no text."""
        mock_update = Mock()
        delattr(mock_update, "text")
        
        mock_tool = Mock()
        mock_tool.content_type = "function_call"
        mock_tool.name = "test_tool"
        mock_tool.arguments = {}
        
        mock_update.contents = [mock_tool]
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        # Should send tool message and possibly streaming message if there's any cleaned text
        assert mock_connection_config.send_status_update_async.call_count >= 1
        
        # Check that at least one call is for a tool message
        call_args_list = mock_connection_config.send_status_update_async.call_args_list
        tool_message_calls = [call for call in call_args_list if isinstance(call[0][0], AgentToolMessage)]
        assert len(tool_message_calls) >= 1

    @pytest.mark.asyncio
    async def test_streaming_callback_websocket_error(self, mock_update):
        """Test streaming callback handles WebSocket errors gracefully."""
        with patch("v4.callbacks.response_handlers.connection_config") as mock_config:
            mock_config.send_status_update_async = AsyncMock(
                side_effect=Exception("WebSocket error")
            )
            
            # Should not raise exception
            await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")

    @pytest.mark.asyncio
    async def test_streaming_callback_multiple_tool_calls(self, mock_connection_config):
        """Test streaming callback with multiple tool calls."""
        mock_update = Mock()
        mock_update.text = "Processing"
        
        mock_tool1 = Mock()
        mock_tool1.content_type = "function_call"
        mock_tool1.name = "tool_one"
        mock_tool1.arguments = {"arg1": "val1"}
        
        mock_tool2 = Mock()
        mock_tool2.content_type = "function_call"
        mock_tool2.name = "tool_two"
        mock_tool2.arguments = {"arg2": "val2"}
        
        mock_update.contents = [mock_tool1, mock_tool2]
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        # First call should be tool message with both tools
        first_call = mock_connection_config.send_status_update_async.call_args_list[0]
        tool_message = first_call[0][0]
        assert len(tool_message.tool_calls) == 2

    @pytest.mark.asyncio
    async def test_streaming_callback_contents_none(self, mock_connection_config):
        """Test streaming callback handles None contents."""
        mock_update = Mock()
        mock_update.text = "Test text"
        mock_update.contents = None
        
        await streaming_agent_response_callback("agent-123", mock_update, False, user_id="user-456")
        
        # Should still send streaming message
        mock_connection_config.send_status_update_async.assert_called_once()


class TestIntegrationScenarios:
    """Integration test scenarios for response handlers."""

    @pytest.fixture
    def mock_connection_config(self):
        """Mock connection_config for integration tests."""
        with patch("v4.callbacks.response_handlers.connection_config") as mock:
            mock.send_status_update_async = AsyncMock()
            yield mock

    @pytest.mark.asyncio
    async def test_full_streaming_to_final_flow(self, mock_connection_config):
        """Test complete flow from streaming to final message."""
        # Send streaming chunks
        for i in range(3):
            mock_update = Mock()
            mock_update.text = f"Chunk {i}"
            mock_update.contents = []
            is_final = (i == 2)
            
            await streaming_agent_response_callback(
                "agent-123", mock_update, is_final, user_id="user-456"
            )
        
        # Send final message
        mock_final = Mock()
        mock_final.author_name = "TestAgent"
        mock_final.role = "assistant"
        mock_final.text = "Complete response"
        
        agent_response_callback("agent-123", mock_final, user_id="user-456")
        
        # Verify total messages sent
        assert mock_connection_config.send_status_update_async.call_count == 4

    def test_citation_cleaning_consistency(self):
        """Test citation cleaning produces consistent results."""
        text = "Test[1] citation[source] removal【ref】."
        
        # Clean multiple times
        result1 = clean_citations(text)
        result2 = clean_citations(text)
        result3 = clean_citations(result1)
        
        assert result1 == result2
        assert result2 == result3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
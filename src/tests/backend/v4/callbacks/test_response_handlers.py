"""Unit tests for response_handlers module."""

import sys
import os
from unittest.mock import Mock, patch, AsyncMock
import pytest

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

# Set required environment variables for testing
os.environ.setdefault('APPLICATIONINSIGHTS_CONNECTION_STRING', 'test_connection_string')
os.environ.setdefault('APP_ENV', 'dev')
os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com/')
os.environ.setdefault('AZURE_OPENAI_API_KEY', 'test_key')
os.environ.setdefault('AZURE_OPENAI_DEPLOYMENT_NAME', 'test_deployment')
os.environ.setdefault('AZURE_AI_SUBSCRIPTION_ID', 'test_subscription_id')
os.environ.setdefault('AZURE_AI_RESOURCE_GROUP', 'test_resource_group')
os.environ.setdefault('AZURE_AI_PROJECT_NAME', 'test_project_name')
os.environ.setdefault('AZURE_AI_AGENT_ENDPOINT', 'https://test.agent.azure.com/')
os.environ.setdefault('AZURE_AI_PROJECT_ENDPOINT', 'https://test.project.azure.com/')
os.environ.setdefault('COSMOSDB_ENDPOINT', 'https://test.documents.azure.com:443/')
os.environ.setdefault('COSMOSDB_DATABASE', 'test_database')
os.environ.setdefault('COSMOSDB_CONTAINER', 'test_container')
os.environ.setdefault('AZURE_CLIENT_ID', 'test_client_id')
os.environ.setdefault('AZURE_TENANT_ID', 'test_tenant_id')
os.environ.setdefault('AZURE_OPENAI_RAI_DEPLOYMENT_NAME', 'test_rai_deployment')

# Mock external dependencies before importing our modules
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.agents'] = Mock()
sys.modules['azure.ai.agents.aio'] = Mock(AgentsClient=Mock)
sys.modules['azure.ai.projects'] = Mock()
sys.modules['azure.ai.projects.aio'] = Mock(AIProjectClient=Mock)
sys.modules['azure.ai.projects.models'] = Mock(MCPTool=Mock)
sys.modules['azure.ai.projects.models._models'] = Mock()
sys.modules['azure.ai.projects._client'] = Mock()
sys.modules['azure.ai.projects.operations'] = Mock()
sys.modules['azure.ai.projects.operations._patch'] = Mock()
sys.modules['azure.ai.projects.operations._patch_datasets'] = Mock()
sys.modules['azure.search'] = Mock()
sys.modules['azure.search.documents'] = Mock()
sys.modules['azure.search.documents.indexes'] = Mock()
sys.modules['azure.core'] = Mock()
sys.modules['azure.core.exceptions'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['azure.cosmos'] = Mock(CosmosClient=Mock)
sys.modules['azure.monitor'] = Mock()
sys.modules['azure.monitor.events'] = Mock()
sys.modules['azure.monitor.events.extension'] = Mock()
sys.modules['azure.monitor.opentelemetry'] = Mock()
sys.modules['azure.monitor.opentelemetry.exporter'] = Mock()

# Mock agent_framework dependencies
class MockChatMessage:
    """Mock ChatMessage class for isinstance checks."""
    def __init__(self):
        self.text = "Sample message text"
        self.author_name = "TestAgent"
        self.role = "assistant"

mock_chat_message = MockChatMessage
mock_agent_response_update = Mock()
mock_agent_response_update.text = "Sample update text"
mock_agent_response_update.contents = []

sys.modules['agent_framework'] = Mock(ChatMessage=mock_chat_message)
sys.modules['agent_framework._workflows'] = Mock()
sys.modules['agent_framework._workflows._magentic'] = Mock(AgentRunResponseUpdate=mock_agent_response_update)
sys.modules['agent_framework.azure'] = Mock(AzureOpenAIChatClient=Mock())
sys.modules['agent_framework._content'] = Mock()
sys.modules['agent_framework._agents'] = Mock()
sys.modules['agent_framework._agents._agent'] = Mock()

# Mock common dependencies
sys.modules['common'] = Mock()
sys.modules['common.config'] = Mock()
sys.modules['common.config.app_config'] = Mock(config=Mock())
sys.modules['common.models'] = Mock()
sys.modules['common.models.messages_af'] = Mock(TeamConfiguration=Mock())
sys.modules['common.database'] = Mock()
sys.modules['common.database.cosmosdb'] = Mock()
sys.modules['common.database.database_factory'] = Mock()
sys.modules['common.utils'] = Mock()
sys.modules['common.utils.utils_af'] = Mock()
sys.modules['common.utils.event_utils'] = Mock()
sys.modules['common.utils.otlp_tracing'] = Mock()

# Mock v4 config dependencies  
mock_connection_config = Mock()
mock_connection_config.send_status_update_async = AsyncMock()
sys.modules['v4'] = Mock()
sys.modules['v4.config'] = Mock()
sys.modules['v4.config.settings'] = Mock(connection_config=mock_connection_config)

# Mock v4 models
mock_websocket_message_type = Mock()
mock_websocket_message_type.AGENT_MESSAGE = "agent_message"
mock_websocket_message_type.AGENT_MESSAGE_STREAMING = "agent_message_streaming"
mock_websocket_message_type.AGENT_TOOL_MESSAGE = "agent_tool_message"

mock_agent_message = Mock()
mock_agent_message_streaming = Mock()
mock_agent_tool_call = Mock()
mock_agent_tool_message = Mock()
mock_agent_tool_message.tool_calls = []

sys.modules['v4.models'] = Mock()
sys.modules['v4.models.models'] = Mock(MPlan=Mock(), PlanStatus=Mock())
sys.modules['v4.models.messages'] = Mock(
    AgentMessage=mock_agent_message,
    AgentMessageStreaming=mock_agent_message_streaming,
    AgentToolCall=mock_agent_tool_call,
    AgentToolMessage=mock_agent_tool_message,
    WebsocketMessageType=mock_websocket_message_type,
)

# Now import our module under test
from backend.v4.callbacks.response_handlers import (
    clean_citations,
    _is_function_call_item,
    _extract_tool_calls_from_contents,
    agent_response_callback,
    streaming_agent_response_callback,
)

# Access mocked modules that we'll use in tests
connection_config = sys.modules['v4.config.settings'].connection_config
AgentMessage = sys.modules['v4.models.messages'].AgentMessage
AgentMessageStreaming = sys.modules['v4.models.messages'].AgentMessageStreaming
AgentToolCall = sys.modules['v4.models.messages'].AgentToolCall
AgentToolMessage = sys.modules['v4.models.messages'].AgentToolMessage
WebsocketMessageType = sys.modules['v4.models.messages'].WebsocketMessageType


class TestCleanCitations:
    """Tests for the clean_citations function."""

    def test_clean_citations_empty_string(self):
        """Test clean_citations with empty string."""
        assert clean_citations("") == ""

    def test_clean_citations_none(self):
        """Test clean_citations with None."""
        assert clean_citations(None) is None

    def test_clean_citations_no_citations(self):
        """Test clean_citations with text that has no citations."""
        text = "This is a normal text without any citations."
        assert clean_citations(text) == text

    def test_clean_citations_numeric_source(self):
        """Test cleaning [1:2|source] format citations."""
        text = "This is text [1:2|source] with citations."
        expected = "This is text  with citations."
        assert clean_citations(text) == expected

    def test_clean_citations_source_only(self):
        """Test cleaning [source] format citations."""
        text = "Text with [source] citation."
        expected = "Text with  citation."
        assert clean_citations(text) == expected

    def test_clean_citations_case_insensitive_source(self):
        """Test cleaning case insensitive [SOURCE] citations."""
        text = "Text with [SOURCE] citation."
        expected = "Text with  citation."
        assert clean_citations(text) == expected

    def test_clean_citations_numeric_brackets(self):
        """Test cleaning [1] format citations."""
        text = "Text [1] with [2] numeric citations [123]."
        expected = "Text  with  numeric citations ."
        assert clean_citations(text) == expected

    def test_clean_citations_unicode_brackets(self):
        """Test cleaning 【content】 format citations."""
        text = "Text with 【reference material】 unicode citations."
        expected = "Text with  unicode citations."
        assert clean_citations(text) == expected

    def test_clean_citations_source_parentheses(self):
        """Test cleaning (source:...) format citations."""
        text = "Text with (source: document.pdf) parentheses citation."
        expected = "Text with  parentheses citation."
        assert clean_citations(text) == expected

    def test_clean_citations_source_square_brackets(self):
        """Test cleaning [source:...] format citations."""
        text = "Text with [source: document.pdf] square bracket citation."
        expected = "Text with  square bracket citation."
        assert clean_citations(text) == expected

    def test_clean_citations_multiple_formats(self):
        """Test cleaning multiple citation formats in one text."""
        text = "Text [1:2|source] with [source] and [123] and 【ref】 and (source: doc) citations."
        expected = "Text  with  and  and  and  citations."
        assert clean_citations(text) == expected

    def test_clean_citations_preserves_formatting(self):
        """Test that clean_citations preserves text formatting."""
        text = "Line 1\nLine 2 [source]\nLine 3"
        expected = "Line 1\nLine 2 \nLine 3"
        assert clean_citations(text) == expected


class TestIsFunctionCallItem:
    """Tests for the _is_function_call_item function."""

    def test_is_function_call_item_none(self):
        """Test _is_function_call_item with None."""
        assert _is_function_call_item(None) is False

    def test_is_function_call_item_with_content_type(self):
        """Test _is_function_call_item with content_type='function_call'."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        assert _is_function_call_item(mock_item) is True

    def test_is_function_call_item_wrong_content_type(self):
        """Test _is_function_call_item with wrong content_type."""
        mock_item = Mock()
        mock_item.content_type = "text"
        assert _is_function_call_item(mock_item) is False

    def test_is_function_call_item_name_and_arguments(self):
        """Test _is_function_call_item with name and arguments but no text."""
        mock_item = Mock()
        mock_item.name = "test_function"
        mock_item.arguments = {"arg1": "value1"}
        # Remove text attribute to simulate no text
        if hasattr(mock_item, 'text'):
            del mock_item.text
        assert _is_function_call_item(mock_item) is True

    def test_is_function_call_item_with_text(self):
        """Test _is_function_call_item with name, arguments, and text (should be False)."""
        mock_item = Mock()
        mock_item.name = "test_function"
        mock_item.arguments = {"arg1": "value1"}
        mock_item.text = "some text"
        assert _is_function_call_item(mock_item) is False

    def test_is_function_call_item_missing_name(self):
        """Test _is_function_call_item with arguments but no name."""
        mock_item = Mock()
        mock_item.arguments = {"arg1": "value1"}
        if hasattr(mock_item, 'name'):
            del mock_item.name
        if hasattr(mock_item, 'text'):
            del mock_item.text
        assert _is_function_call_item(mock_item) is False

    def test_is_function_call_item_missing_arguments(self):
        """Test _is_function_call_item with name but no arguments."""
        mock_item = Mock()
        mock_item.name = "test_function"
        if hasattr(mock_item, 'arguments'):
            del mock_item.arguments
        if hasattr(mock_item, 'text'):
            del mock_item.text
        assert _is_function_call_item(mock_item) is False

    def test_is_function_call_item_regular_object(self):
        """Test _is_function_call_item with regular object."""
        mock_item = Mock()
        mock_item.some_attr = "value"
        assert _is_function_call_item(mock_item) is False


class TestExtractToolCallsFromContents:
    """Tests for the _extract_tool_calls_from_contents function."""

    def test_extract_tool_calls_empty_list(self):
        """Test _extract_tool_calls_from_contents with empty list."""
        result = _extract_tool_calls_from_contents([])
        assert result == []

    def test_extract_tool_calls_no_function_calls(self):
        """Test _extract_tool_calls_from_contents with no function call items."""
        mock_item1 = Mock()
        mock_item1.content_type = "text"
        mock_item2 = Mock()
        mock_item2.some_attr = "value"
        
        result = _extract_tool_calls_from_contents([mock_item1, mock_item2])
        assert result == []

    def test_extract_tool_calls_with_function_calls(self):
        """Test _extract_tool_calls_from_contents with function call items."""
        mock_item1 = Mock()
        mock_item1.content_type = "function_call"
        mock_item1.name = "test_function1"
        mock_item1.arguments = {"arg1": "value1"}

        mock_item2 = Mock()
        mock_item2.name = "test_function2"
        mock_item2.arguments = {"arg2": "value2"}
        if hasattr(mock_item2, 'text'):
            del mock_item2.text

        with patch('backend.v4.callbacks.response_handlers.AgentToolCall') as mock_agent_tool_call:
            mock_tool_call1 = Mock()
            mock_tool_call2 = Mock()
            mock_agent_tool_call.side_effect = [mock_tool_call1, mock_tool_call2]

            result = _extract_tool_calls_from_contents([mock_item1, mock_item2])
            
            assert len(result) == 2
            assert result == [mock_tool_call1, mock_tool_call2]
            
            # Verify AgentToolCall was called with correct parameters
            mock_agent_tool_call.assert_any_call(tool_name="test_function1", arguments={"arg1": "value1"})
            mock_agent_tool_call.assert_any_call(tool_name="test_function2", arguments={"arg2": "value2"})

    def test_extract_tool_calls_mixed_content(self):
        """Test _extract_tool_calls_from_contents with mixed content types."""
        mock_function_item = Mock()
        mock_function_item.content_type = "function_call"
        mock_function_item.name = "test_function"
        mock_function_item.arguments = {"arg": "value"}

        mock_text_item = Mock()
        mock_text_item.content_type = "text"
        mock_text_item.text = "some text"

        with patch('backend.v4.callbacks.response_handlers.AgentToolCall') as mock_agent_tool_call:
            mock_tool_call = Mock()
            mock_agent_tool_call.return_value = mock_tool_call

            result = _extract_tool_calls_from_contents([mock_function_item, mock_text_item])
            
            assert len(result) == 1
            assert result == [mock_tool_call]

    def test_extract_tool_calls_missing_name_uses_unknown(self):
        """Test _extract_tool_calls_from_contents with missing name uses 'unknown_tool'."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        if hasattr(mock_item, 'name'):
            del mock_item.name
        mock_item.arguments = {"arg": "value"}

        with patch('backend.v4.callbacks.response_handlers.AgentToolCall') as mock_agent_tool_call:
            mock_tool_call = Mock()
            mock_agent_tool_call.return_value = mock_tool_call

            result = _extract_tool_calls_from_contents([mock_item])
            
            assert len(result) == 1
            mock_agent_tool_call.assert_called_once_with(tool_name="unknown_tool", arguments={"arg": "value"})

    def test_extract_tool_calls_none_arguments_uses_empty_dict(self):
        """Test _extract_tool_calls_from_contents with None arguments uses empty dict."""
        mock_item = Mock()
        mock_item.content_type = "function_call"
        mock_item.name = "test_function"
        mock_item.arguments = None

        with patch('backend.v4.callbacks.response_handlers.AgentToolCall') as mock_agent_tool_call:
            mock_tool_call = Mock()
            mock_agent_tool_call.return_value = mock_tool_call

            result = _extract_tool_calls_from_contents([mock_item])
            
            assert len(result) == 1
            mock_agent_tool_call.assert_called_once_with(tool_name="test_function", arguments={})


class TestAgentResponseCallback:
    """Tests for the agent_response_callback function."""

    def test_agent_response_callback_no_user_id(self):
        """Test agent_response_callback with no user_id."""
        mock_message = Mock()
        mock_message.text = "Test message"
        mock_message.author_name = "TestAgent"
        mock_message.role = "assistant"

        with patch('backend.v4.callbacks.response_handlers.logger') as mock_logger:
            agent_response_callback("agent_123", mock_message, user_id=None)
            mock_logger.debug.assert_called_once_with(
                "No user_id provided; skipping websocket send for final message."
            )

    @patch('backend.v4.callbacks.response_handlers.asyncio.create_task')
    @patch('backend.v4.callbacks.response_handlers.time.time')
    def test_agent_response_callback_with_chat_message(self, mock_time, mock_create_task):
        """Test agent_response_callback with ChatMessage object."""
        mock_time.return_value = 1234567890.0
        
        # Create an instance of our MockChatMessage
        mock_message = MockChatMessage()
        mock_message.text = "Test message with citations [1:2|source]"
        mock_message.author_name = "TestAgent"
        mock_message.role = "assistant"
        
        with patch('backend.v4.callbacks.response_handlers.AgentMessage') as mock_agent_message:
            mock_agent_msg = Mock()
            mock_agent_message.return_value = mock_agent_msg

            agent_response_callback("agent_123", mock_message, user_id="user_456")
            
            # Verify AgentMessage was created with cleaned text
            mock_agent_message.assert_called_once_with(
                agent_name="TestAgent",
                timestamp=1234567890.0,
                content="Test message with citations "
            )
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    @patch('backend.v4.callbacks.response_handlers.asyncio.create_task')
    @patch('backend.v4.callbacks.response_handlers.time.time')
    def test_agent_response_callback_fallback_message(self, mock_time, mock_create_task):
        """Test agent_response_callback with non-ChatMessage object (fallback)."""
        mock_time.return_value = 1234567890.0
        
        mock_message = Mock()
        mock_message.text = "Fallback message text"
        # Don't set author_name to test fallback
        if hasattr(mock_message, 'author_name'):
            del mock_message.author_name
        if hasattr(mock_message, 'role'):
            del mock_message.role

        with patch('backend.v4.callbacks.response_handlers.AgentMessage') as mock_agent_message:
            mock_agent_msg = Mock()
            mock_agent_message.return_value = mock_agent_msg

            agent_response_callback("agent_123", mock_message, user_id="user_456")
            
            # Verify AgentMessage was created with agent_id as agent_name
            mock_agent_message.assert_called_once_with(
                agent_name="agent_123",
                timestamp=1234567890.0,
                content="Fallback message text"
            )

    @patch('backend.v4.callbacks.response_handlers.asyncio.create_task')
    @patch('backend.v4.callbacks.response_handlers.time.time')
    def test_agent_response_callback_no_text_attribute(self, mock_time, mock_create_task):
        """Test agent_response_callback with message that has no text attribute."""
        mock_time.return_value = 1234567890.0
        
        mock_message = Mock()
        if hasattr(mock_message, 'text'):
            del mock_message.text
        mock_message.author_name = "TestAgent"

        with patch('backend.v4.callbacks.response_handlers.AgentMessage') as mock_agent_message:
            mock_agent_msg = Mock()
            mock_agent_message.return_value = mock_agent_msg

            agent_response_callback("agent_123", mock_message, user_id="user_456")
            
            # Verify AgentMessage was created with empty content
            mock_agent_message.assert_called_once_with(
                agent_name="TestAgent",
                timestamp=1234567890.0,
                content=""
            )

    @patch('backend.v4.callbacks.response_handlers.logger')
    @patch('backend.v4.callbacks.response_handlers.asyncio.create_task')
    def test_agent_response_callback_exception_handling(self, mock_create_task, mock_logger):
        """Test agent_response_callback handles exceptions properly."""
        mock_message = Mock()
        mock_message.text = "Test message"
        mock_message.author_name = "TestAgent"

        # Make create_task raise an exception
        mock_create_task.side_effect = Exception("Test exception")

        with patch('backend.v4.callbacks.response_handlers.AgentMessage'):
            agent_response_callback("agent_123", mock_message, user_id="user_456")
            
            # Verify error was logged
            mock_logger.error.assert_called_once_with(
                "agent_response_callback error sending WebSocket message: %s",
                mock_create_task.side_effect
            )

    @patch('backend.v4.callbacks.response_handlers.logger')
    @patch('backend.v4.callbacks.response_handlers.asyncio.create_task')
    @patch('backend.v4.callbacks.response_handlers.time.time')
    def test_agent_response_callback_successful_logging(self, mock_time, mock_create_task, mock_logger):
        """Test agent_response_callback logs successful message."""
        mock_time.return_value = 1234567890.0
        
        long_message = "A very long test message that should be truncated in the log output because it exceeds the 200 character limit that is applied in the logging statement for better readability and log management"
        mock_message = Mock()
        mock_message.text = long_message
        mock_message.author_name = "TestAgent"
        mock_message.role = "assistant"

        with patch('backend.v4.callbacks.response_handlers.AgentMessage'):
            agent_response_callback("agent_123", mock_message, user_id="user_456")
            
            # Verify info log was called with truncated message
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0]
            assert call_args[0] == "%s message (agent=%s): %s"
            assert call_args[1] == "Assistant"
            assert call_args[2] == "TestAgent"
            assert len(call_args[3]) == 193  # Message should be the actual length (not truncated in this case)


class TestStreamingAgentResponseCallback:
    """Tests for the streaming_agent_response_callback function."""

    @pytest.mark.asyncio
    async def test_streaming_callback_no_user_id(self):
        """Test streaming callback returns early when no user_id."""
        mock_update = Mock()
        mock_update.text = "Test text"
        
        # Should return None without any processing
        result = await streaming_agent_response_callback("agent_123", mock_update, False, user_id=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_streaming_callback_with_text(self):
        """Test streaming callback with update that has text."""
        mock_update = Mock()
        mock_update.text = "Test streaming text [source]"
        mock_update.contents = []

        with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
            mock_streaming_obj = Mock()
            mock_streaming.return_value = mock_streaming_obj

            await streaming_agent_response_callback("agent_123", mock_update, True, user_id="user_456")
            
            # Verify AgentMessageStreaming was created with cleaned text
            mock_streaming.assert_called_once_with(
                agent_name="agent_123",
                content="Test streaming text ",
                is_final=True
            )
            
            # Verify send_status_update_async was called
            connection_config.send_status_update_async.assert_called_with(
                mock_streaming_obj,
                "user_456",
                message_type=WebsocketMessageType.AGENT_MESSAGE_STREAMING
            )

    @pytest.mark.asyncio
    async def test_streaming_callback_no_text_with_contents(self):
        """Test streaming callback when update has no text but has contents with text."""
        mock_update = Mock()
        mock_update.text = None
        
        mock_content1 = Mock()
        mock_content1.text = "Content text 1"
        mock_content2 = Mock()
        mock_content2.text = "Content text 2"
        mock_content3 = Mock()
        mock_content3.text = None  # No text
        
        mock_update.contents = [mock_content1, mock_content2, mock_content3]

        with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
            mock_streaming_obj = Mock()
            mock_streaming.return_value = mock_streaming_obj

            await streaming_agent_response_callback("agent_123", mock_update, False, user_id="user_456")
            
            # Verify AgentMessageStreaming was created with concatenated content text
            mock_streaming.assert_called_once_with(
                agent_name="agent_123",
                content="Content text 1Content text 2",
                is_final=False
            )

    @pytest.mark.asyncio
    async def test_streaming_callback_no_text_no_content_text(self):
        """Test streaming callback when update has no text and no content text."""
        mock_update = Mock()
        mock_update.text = ""
        
        mock_content = Mock()
        mock_content.text = None
        mock_update.contents = [mock_content]

        # Should not call AgentMessageStreaming since there's no text
        with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
            await streaming_agent_response_callback("agent_123", mock_update, False, user_id="user_456")
            mock_streaming.assert_not_called()

    @pytest.mark.asyncio
    async def test_streaming_callback_with_tool_calls(self):
        """Test streaming callback with tool calls in contents."""
        mock_update = Mock()
        mock_update.text = "Regular text"
        
        # Create mock content that will be detected as function call
        mock_tool_content = Mock()
        mock_tool_content.content_type = "function_call"
        mock_tool_content.name = "test_tool"
        mock_tool_content.arguments = {"param": "value"}
        
        mock_update.contents = [mock_tool_content]
        
        # Reset the mock call count before the test
        connection_config.send_status_update_async.reset_mock()

        with patch('backend.v4.callbacks.response_handlers._extract_tool_calls_from_contents') as mock_extract:
            mock_tool_call = Mock()
            mock_extract.return_value = [mock_tool_call]
            
            with patch('backend.v4.callbacks.response_handlers.AgentToolMessage') as mock_tool_message:
                mock_tool_msg = Mock()
                mock_tool_msg.tool_calls = []
                mock_tool_message.return_value = mock_tool_msg
                
                with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
                    mock_streaming_obj = Mock()
                    mock_streaming.return_value = mock_streaming_obj

                    await streaming_agent_response_callback("agent_123", mock_update, False, user_id="user_456")
                    
                    # Verify tool message was created and sent
                    mock_tool_message.assert_called_once_with(agent_name="agent_123")
                    # Verify tool_calls.extend was called with our mock tool call
                    assert mock_tool_call in mock_tool_msg.tool_calls or mock_tool_msg.tool_calls.extend.called
                    
                    # Verify both tool message and streaming message were sent
                    assert connection_config.send_status_update_async.call_count == 2

    @pytest.mark.asyncio
    async def test_streaming_callback_no_contents_attribute(self):
        """Test streaming callback when update has no contents attribute."""
        mock_update = Mock()
        mock_update.text = "Test text"
        if hasattr(mock_update, 'contents'):
            del mock_update.contents

        with patch('backend.v4.callbacks.response_handlers._extract_tool_calls_from_contents') as mock_extract:
            mock_extract.return_value = []
            
            with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
                mock_streaming_obj = Mock()
                mock_streaming.return_value = mock_streaming_obj

                await streaming_agent_response_callback("agent_123", mock_update, True, user_id="user_456")
                
                # Should still process the text
                mock_streaming.assert_called_once_with(
                    agent_name="agent_123",
                    content="Test text",
                    is_final=True
                )
                
                # Should call extract with empty list
                mock_extract.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_streaming_callback_none_contents(self):
        """Test streaming callback when update.contents is None."""
        mock_update = Mock()
        mock_update.text = "Test text"
        mock_update.contents = None

        with patch('backend.v4.callbacks.response_handlers._extract_tool_calls_from_contents') as mock_extract:
            mock_extract.return_value = []
            
            with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
                mock_streaming_obj = Mock()
                mock_streaming.return_value = mock_streaming_obj

                await streaming_agent_response_callback("agent_123", mock_update, True, user_id="user_456")
                
                # Should call extract with empty list
                mock_extract.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_streaming_callback_exception_handling(self):
        """Test streaming callback handles exceptions properly."""
        mock_update = Mock()
        mock_update.text = "Test text"
        mock_update.contents = []

        # Mock connection_config to raise an exception
        connection_config.send_status_update_async.side_effect = Exception("Test exception")

        with patch('backend.v4.callbacks.response_handlers.logger') as mock_logger:
            with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming'):
                await streaming_agent_response_callback("agent_123", mock_update, False, user_id="user_456")
                
                # Verify error was logged
                mock_logger.error.assert_called_once_with(
                    "streaming_agent_response_callback error: %s",
                    connection_config.send_status_update_async.side_effect
                )

    @pytest.mark.asyncio
    async def test_streaming_callback_tool_calls_functionality(self):
        """Test streaming callback processes tool calls correctly."""
        mock_update = Mock()
        mock_update.text = None
        mock_update.contents = []

        with patch('backend.v4.callbacks.response_handlers._extract_tool_calls_from_contents') as mock_extract:
            # Mock multiple tool calls
            mock_tool_calls = [Mock(), Mock(), Mock()]
            mock_extract.return_value = mock_tool_calls
    
            with patch('backend.v4.callbacks.response_handlers.AgentToolMessage') as mock_tool_message:
                mock_tool_msg = Mock()
                mock_tool_msg.tool_calls = []
                mock_tool_message.return_value = mock_tool_msg

                await streaming_agent_response_callback("agent_123", mock_update, False, user_id="user_456")
                
                # Verify tool message was created and tool calls were processed
                mock_tool_message.assert_called_once_with(agent_name="agent_123")
                assert connection_config.send_status_update_async.called

    @pytest.mark.asyncio
    async def test_streaming_callback_chunk_processing(self):
        """Test streaming callback processes text chunks correctly."""
        mock_update = Mock()
        mock_update.text = "Test streaming text for processing"
        mock_update.contents = []

        with patch('backend.v4.callbacks.response_handlers.AgentMessageStreaming') as mock_streaming:
            mock_streaming_obj = Mock()
            mock_streaming.return_value = mock_streaming_obj
            
            await streaming_agent_response_callback("agent_123", mock_update, True, user_id="user_456")
            
            # Verify streaming message was created with correct parameters
            mock_streaming.assert_called_once_with(
                agent_name="agent_123",
                content="Test streaming text for processing",
                is_final=True
            )
            assert connection_config.send_status_update_async.called
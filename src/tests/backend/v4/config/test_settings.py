"""Unit tests for backend/v4/config/settings.py.

Comprehensive test cases covering all configuration classes with proper mocking.
"""

import asyncio
import json
import os
import sys
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

# Set up required environment variables before any imports
os.environ.update({
    'APPLICATIONINSIGHTS_CONNECTION_STRING': 'InstrumentationKey=test-key',
    'AZURE_AI_SUBSCRIPTION_ID': 'test-subscription',
    'AZURE_AI_RESOURCE_GROUP': 'test-rg',
    'AZURE_AI_PROJECT_NAME': 'test-project',
    'AZURE_AI_AGENT_ENDPOINT': 'https://test.agent.endpoint.com',
    'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
    'AZURE_OPENAI_API_KEY': 'test-key',
    'AZURE_OPENAI_API_VERSION': '2023-05-15'
})

# Only mock external problematic dependencies - do NOT mock internal common.* modules
sys.modules['agent_framework'] = Mock()
sys.modules['agent_framework.azure'] = Mock()
sys.modules['agent_framework_azure_ai'] = Mock()
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.projects'] = Mock()
sys.modules['azure.ai.projects.aio'] = Mock()
sys.modules['azure.core'] = Mock()
sys.modules['azure.core.exceptions'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['azure.keyvault'] = Mock()
sys.modules['azure.keyvault.secrets'] = Mock()
sys.modules['azure.keyvault.secrets.aio'] = Mock()

# Import the real v4.models classes first to avoid type annotation issues
from backend.v4.models.messages import MPlan, WebsocketMessageType
from backend.v4.models.models import MPlan as MPlanModel, MStep

# Mock v4.models for relative imports used in settings.py, using REAL classes
from types import ModuleType
mock_v4 = ModuleType('v4')
mock_v4_models = ModuleType('v4.models')
mock_v4_models_messages = ModuleType('v4.models.messages')
mock_v4_models_models = ModuleType('v4.models.models')

# Assign real classes to mock modules
mock_v4_models_messages.MPlan = MPlan
mock_v4_models_messages.WebsocketMessageType = WebsocketMessageType
mock_v4_models_models.MPlan = MPlanModel
mock_v4_models_models.MStep = MStep

sys.modules['v4'] = mock_v4
sys.modules['v4.models'] = mock_v4_models
sys.modules['v4.models.messages'] = mock_v4_models_messages
sys.modules['v4.models.models'] = mock_v4_models_models

# Mock common.config.app_config 
sys.modules['common'] = Mock()
sys.modules['common.config'] = Mock()
sys.modules['common.config.app_config'] = Mock()
sys.modules['common.models'] = Mock()
sys.modules['common.models.messages_af'] = Mock()

# Create comprehensive mock objects
mock_azure_openai_chat_client = Mock()
mock_chat_options = Mock()
mock_choice_update = Mock()
mock_chat_message_delta = Mock()
mock_user_message = Mock()
mock_assistant_message = Mock()
mock_system_message = Mock()
mock_get_log_analytics_workspace = Mock()
mock_get_applicationinsights = Mock()
mock_get_azure_openai_config = Mock()
mock_get_azure_ai_config = Mock()
mock_get_mcp_server_config = Mock()
mock_team_configuration = Mock()

# Mock config object with all required attributes
mock_config = Mock()
mock_config.AZURE_OPENAI_ENDPOINT = 'https://test.openai.azure.com/'
mock_config.REASONING_MODEL_NAME = 'o1-reasoning'
mock_config.AZURE_OPENAI_DEPLOYMENT_NAME = 'gpt-4'
mock_config.AZURE_COGNITIVE_SERVICES = 'https://cognitiveservices.azure.com/.default'
mock_config.get_azure_credentials.return_value = Mock()

# Set up external mocks
sys.modules['agent_framework'].azure.AzureOpenAIChatClient = mock_azure_openai_chat_client
sys.modules['agent_framework'].ChatOptions = mock_chat_options
sys.modules['common.config.app_config'].config = mock_config
sys.modules['common.models.messages_af'].TeamConfiguration = mock_team_configuration

# Now import from backend with proper path
from backend.v4.config.settings import (
    AzureConfig,
    MCPConfig,
    OrchestrationConfig,
    ConnectionConfig,
    TeamConfig
)


class TestAzureConfig(unittest.TestCase):
    """Test cases for AzureConfig class."""

    @patch('backend.v4.config.settings.config')
    def setUp(self, mock_config):
        """Set up test fixtures before each test method."""
        mock_config.return_value = Mock()

    def test_azure_config_creation(self):
        """Test creating AzureConfig instance."""
        # Import with environment variables set
        
        config = AzureConfig()
        
        # Test that object is created successfully
        self.assertIsNotNone(config)
        self.assertIsNotNone(config.endpoint)
        self.assertIsNotNone(config.credential)

    @patch('backend.v4.config.settings.ChatOptions')
    def test_create_execution_settings(self, mock_chat_options):
        """Test creating execution settings."""
        
        mock_settings = Mock()
        mock_chat_options.return_value = mock_settings
        
        config = AzureConfig()
        settings = config.create_execution_settings()
        
        self.assertEqual(settings, mock_settings)
        mock_chat_options.assert_called_once_with(
            max_output_tokens=4000,
            temperature=0.1
        )

    @patch('backend.v4.config.settings.config')
    def test_ad_token_provider(self, mock_config):
        """Test AD token provider."""
        # Mock the credential and token
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test-token-123"
        mock_credential.get_token.return_value = mock_token
        mock_config.get_azure_credentials.return_value = mock_credential
        mock_config.AZURE_COGNITIVE_SERVICES = "https://cognitiveservices.azure.com/.default"
        
        azure_config = AzureConfig()
        token = azure_config.ad_token_provider()
        
        self.assertEqual(token, "test-token-123")
        mock_credential.get_token.assert_called_once_with(mock_config.AZURE_COGNITIVE_SERVICES)

class TestAzureConfigAsync(IsolatedAsyncioTestCase):
    """Async test cases for AzureConfig class."""

    @patch('backend.v4.config.settings.AzureOpenAIChatClient')
    async def test_create_chat_completion_service_standard_model(self, mock_client_class):
        """Test creating chat completion service with standard model."""
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        config = AzureConfig()
        service = await config.create_chat_completion_service(use_reasoning_model=False)
        
        self.assertEqual(service, mock_client)
        mock_client_class.assert_called_once()

    @patch('backend.v4.config.settings.AzureOpenAIChatClient')
    async def test_create_chat_completion_service_reasoning_model(self, mock_client_class):
        """Test creating chat completion service with reasoning model."""
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        config = AzureConfig()
        service = await config.create_chat_completion_service(use_reasoning_model=True)
        
        self.assertEqual(service, mock_client)
        mock_client_class.assert_called_once()


class TestMCPConfig(unittest.TestCase):
    """Test cases for MCPConfig class."""

    def test_mcp_config_creation(self):
        """Test creating MCPConfig instance."""
        
        config = MCPConfig()
        
        # Test that object is created successfully
        self.assertIsNotNone(config)
        self.assertIsNotNone(config.url)
        self.assertIsNotNone(config.name)
        self.assertIsNotNone(config.description)

    def test_get_headers_with_token(self):
        """Test getting headers with token."""
        
        config = MCPConfig()
        token = "test-token"
        
        headers = config.get_headers(token)
        
        expected_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.assertEqual(headers, expected_headers)

    def test_get_headers_without_token(self):
        """Test getting headers without token."""
        
        config = MCPConfig()
        headers = config.get_headers("")
        
        self.assertEqual(headers, {})

    def test_get_headers_with_none_token(self):
        """Test getting headers with None token."""
        
        config = MCPConfig()
        headers = config.get_headers(None)
        
        self.assertEqual(headers, {})


class TestTeamConfig(unittest.TestCase):
    """Test cases for TeamConfig class."""

    def test_team_config_creation(self):
        """Test creating TeamConfig instance."""
        
        config = TeamConfig()
        
        # Test initialization
        self.assertIsInstance(config.teams, dict)
        self.assertEqual(len(config.teams), 0)

    def test_set_and_get_current_team(self):
        """Test setting and getting current team."""
        
        config = TeamConfig()
        user_id = "user-123"
        team_config_mock = Mock()
        
        config.set_current_team(user_id, team_config_mock)
        self.assertEqual(config.teams[user_id], team_config_mock)
        
        retrieved_config = config.get_current_team(user_id)
        self.assertEqual(retrieved_config, team_config_mock)

    def test_get_non_existent_team(self):
        """Test getting non-existent team configuration."""
        
        config = TeamConfig()
        non_existent = config.get_current_team("non-existent")
        
        self.assertIsNone(non_existent)

    def test_overwrite_existing_team(self):
        """Test overwriting existing team configuration."""
        
        config = TeamConfig()
        user_id = "user-123"
        team_config1 = Mock()
        team_config2 = Mock()
        
        config.set_current_team(user_id, team_config1)
        config.set_current_team(user_id, team_config2)
        
        self.assertEqual(config.get_current_team(user_id), team_config2)


class TestOrchestrationConfig(IsolatedAsyncioTestCase):
    """Test cases for OrchestrationConfig class."""

    def test_orchestration_config_creation(self):
        """Test creating OrchestrationConfig instance."""
        
        config = OrchestrationConfig()
        
        # Test initialization
        self.assertIsInstance(config.orchestrations, dict)
        self.assertIsInstance(config.plans, dict)
        self.assertIsInstance(config.approvals, dict)
        self.assertIsInstance(config.sockets, dict)
        self.assertIsInstance(config.clarifications, dict)
        self.assertEqual(config.max_rounds, 20)
        self.assertIsInstance(config._approval_events, dict)
        self.assertIsInstance(config._clarification_events, dict)
        self.assertEqual(config.default_timeout, 300.0)

    def test_get_current_orchestration(self):
        """Test getting current orchestration."""
        
        config = OrchestrationConfig()
        user_id = "user-123"
        orchestration = Mock()
        
        # Test getting non-existent orchestration
        result = config.get_current_orchestration(user_id)
        self.assertIsNone(result)
        
        # Test setting orchestration directly (since there's no setter method)
        config.orchestrations[user_id] = orchestration
        
        # Test getting existing orchestration
        result = config.get_current_orchestration(user_id)
        self.assertEqual(result, orchestration)

    def test_approval_workflow(self):
        """Test approval workflow."""
        
        config = OrchestrationConfig()
        plan_id = "test-plan"
        
        # Test set approval pending
        config.set_approval_pending(plan_id)
        self.assertIn(plan_id, config.approvals)
        self.assertIsNone(config.approvals[plan_id])
        
        # Test set approval result
        config.set_approval_result(plan_id, True)
        self.assertTrue(config.approvals[plan_id])
        
        # Test cleanup
        config.cleanup_approval(plan_id)
        self.assertNotIn(plan_id, config.approvals)

    def test_clarification_workflow(self):
        """Test clarification workflow."""
        
        config = OrchestrationConfig()
        request_id = "test-request"
        
        # Test set clarification pending
        config.set_clarification_pending(request_id)
        self.assertIn(request_id, config.clarifications)
        self.assertIsNone(config.clarifications[request_id])
        
        # Test set clarification result
        answer = "Test answer"
        config.set_clarification_result(request_id, answer)
        self.assertEqual(config.clarifications[request_id], answer)

    async def test_wait_for_approval_already_decided(self):
        """Test waiting for approval when already decided."""
        
        config = OrchestrationConfig()
        plan_id = "test-plan"
        
        # Set approval first
        config.set_approval_pending(plan_id)
        config.set_approval_result(plan_id, True)
        
        # Wait should return immediately
        result = await config.wait_for_approval(plan_id)
        self.assertTrue(result)

    async def test_wait_for_clarification_already_answered(self):
        """Test waiting for clarification when already answered."""
        
        config = OrchestrationConfig()
        request_id = "test-request"
        answer = "Test answer"
        
        # Set clarification first
        config.set_clarification_pending(request_id)
        config.set_clarification_result(request_id, answer)
        
        # Wait should return immediately
        result = await config.wait_for_clarification(request_id)
        self.assertEqual(result, answer)

    async def test_wait_for_approval_timeout(self):
        """Test waiting for approval with timeout."""
        
        config = OrchestrationConfig()
        plan_id = "test-plan"
        
        # Set approval pending but don't provide result
        config.set_approval_pending(plan_id)
        
        # Wait should timeout
        with self.assertRaises(asyncio.TimeoutError):
            await config.wait_for_approval(plan_id, timeout=0.1)
        
        # Approval should be cleaned up
        self.assertNotIn(plan_id, config.approvals)

    async def test_wait_for_clarification_timeout(self):
        """Test waiting for clarification with timeout."""
        
        config = OrchestrationConfig()
        request_id = "test-request"
        
        # Set clarification pending but don't provide result
        config.set_clarification_pending(request_id)
        
        # Wait should timeout
        with self.assertRaises(asyncio.TimeoutError):
            await config.wait_for_clarification(request_id, timeout=0.1)
        
        # Clarification should be cleaned up
        self.assertNotIn(request_id, config.clarifications)

    async def test_wait_for_approval_cancelled(self):
        """Test waiting for approval when cancelled."""
        
        config = OrchestrationConfig()
        plan_id = "test-plan"
        
        config.set_approval_pending(plan_id)
        
        async def cancel_task():
            await asyncio.sleep(0.05)
            task.cancel()
        
        task = asyncio.create_task(config.wait_for_approval(plan_id, timeout=1.0))
        cancel_task_handle = asyncio.create_task(cancel_task())
        
        with self.assertRaises(asyncio.CancelledError):
            await task
        
        await cancel_task_handle

    async def test_wait_for_clarification_cancelled(self):
        """Test waiting for clarification when cancelled."""
        
        config = OrchestrationConfig()
        request_id = "test-request"
        
        config.set_clarification_pending(request_id)
        
        async def cancel_task():
            await asyncio.sleep(0.05)
            task.cancel()
        
        task = asyncio.create_task(config.wait_for_clarification(request_id, timeout=1.0))
        cancel_task_handle = asyncio.create_task(cancel_task())
        
        with self.assertRaises(asyncio.CancelledError):
            await task
        
        await cancel_task_handle

    def test_cleanup_approval(self):
        """Test cleanup approval."""
        
        config = OrchestrationConfig()
        plan_id = "test-plan"
        
        # Set approval and event
        config.set_approval_pending(plan_id)
        self.assertIn(plan_id, config.approvals)
        self.assertIn(plan_id, config._approval_events)
        
        # Cleanup
        config.cleanup_approval(plan_id)
        self.assertNotIn(plan_id, config.approvals)
        self.assertNotIn(plan_id, config._approval_events)

    def test_cleanup_clarification(self):
        """Test cleanup clarification."""
        
        config = OrchestrationConfig()
        request_id = "test-request"
        
        # Set clarification and event
        config.set_clarification_pending(request_id)
        self.assertIn(request_id, config.clarifications)
        self.assertIn(request_id, config._clarification_events)
        
        # Cleanup
        config.cleanup_clarification(request_id)
        self.assertNotIn(request_id, config.clarifications)
        self.assertNotIn(request_id, config._clarification_events)


class TestConnectionConfig(IsolatedAsyncioTestCase):
    """Test cases for ConnectionConfig class."""

    def test_connection_config_creation(self):
        """Test creating ConnectionConfig instance."""
        
        config = ConnectionConfig()
        
        # Test initialization
        self.assertIsInstance(config.connections, dict)
        self.assertIsInstance(config.user_to_process, dict)

    def test_add_and_get_connection(self):
        """Test adding and getting connection."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        connection = Mock()
        user_id = "user-123"
        
        config.add_connection(process_id, connection, user_id)
        
        # Test that connection and user mapping are added
        self.assertEqual(config.connections[process_id], connection)
        self.assertEqual(config.user_to_process[user_id], process_id)
        
        # Test getting connection
        retrieved_connection = config.get_connection(process_id)
        self.assertEqual(retrieved_connection, connection)

    def test_get_non_existent_connection(self):
        """Test getting non-existent connection."""
        
        config = ConnectionConfig()
        process_id = "non-existent-process"
        
        retrieved_connection = config.get_connection(process_id)
        
        self.assertIsNone(retrieved_connection)

    def test_remove_connection(self):
        """Test removing connection."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        connection = Mock()
        user_id = "user-123"
        
        config.add_connection(process_id, connection, user_id)
        config.remove_connection(process_id)
        
        # Test that connection and user mapping are removed
        self.assertNotIn(process_id, config.connections)
        self.assertNotIn(user_id, config.user_to_process)

    async def test_close_connection(self):
        """Test closing connection."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        connection = AsyncMock()
        
        config.add_connection(process_id, connection)
        
        with patch('backend.v4.config.settings.logger'):
            await config.close_connection(process_id)
            
            connection.close.assert_called_once()
            self.assertNotIn(process_id, config.connections)

    async def test_close_non_existent_connection(self):
        """Test closing non-existent connection."""
        
        config = ConnectionConfig()
        process_id = "non-existent-process"
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            await config.close_connection(process_id)
            
            # Should log warning but not fail
            mock_logger.warning.assert_called()

    async def test_close_connection_with_exception(self):
        """Test closing connection with exception."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        connection = AsyncMock()
        connection.close.side_effect = Exception("Close error")
        
        config.add_connection(process_id, connection)
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            await config.close_connection(process_id)
            
            connection.close.assert_called_once()
            mock_logger.error.assert_called()
            # Connection should still be removed
            self.assertNotIn(process_id, config.connections)

    async def test_send_status_update_async_success(self):
        """Test sending status update successfully."""
        config = ConnectionConfig()
        user_id = "user-123"
        process_id = "process-456"
        message = "Test message"
        connection = AsyncMock()
        
        config.add_connection(process_id, connection, user_id)
        
        await config.send_status_update_async(message, user_id)
        
        connection.send_text.assert_called_once()
        sent_data = json.loads(connection.send_text.call_args[0][0])
        self.assertEqual(sent_data['type'], 'system_message')
        self.assertEqual(sent_data['data'], message)

    async def test_send_status_update_async_no_user_id(self):
        """Test sending status update with no user ID."""
        
        config = ConnectionConfig()
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            await config.send_status_update_async("message", "")
            
            mock_logger.warning.assert_called()

    async def test_send_status_update_async_dict_message(self):
        """Test sending status update with dict message."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        process_id = "process-456"
        message = {"key": "value"}
        connection = AsyncMock()
        
        config.add_connection(process_id, connection, user_id)
        
        await config.send_status_update_async(message, user_id)
        
        connection.send_text.assert_called_once()
        sent_data = json.loads(connection.send_text.call_args[0][0])
        self.assertEqual(sent_data['data'], message)

    async def test_send_status_update_async_with_to_dict_method(self):
        """Test sending status update with object having to_dict method."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        process_id = "process-456"
        connection = AsyncMock()
        
        # Create mock message with to_dict method
        message = Mock()
        message.to_dict.return_value = {"test": "data"}
        
        config.add_connection(process_id, connection, user_id)
        
        await config.send_status_update_async(message, user_id)
        
        connection.send_text.assert_called_once()
        sent_data = json.loads(connection.send_text.call_args[0][0])
        self.assertEqual(sent_data['data'], {"test": "data"})

    async def test_send_status_update_async_with_data_type_attributes(self):
        """Test sending status update with object having data and type attributes."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        process_id = "process-456"
        connection = AsyncMock()
        
        # Create mock message with data and type attributes
        message = Mock()
        message.data = "test data"
        message.type = "test_type"
        # Remove to_dict to avoid that path
        del message.to_dict
        
        config.add_connection(process_id, connection, user_id)
        
        await config.send_status_update_async(message, user_id)
        
        connection.send_text.assert_called_once()
        sent_data = json.loads(connection.send_text.call_args[0][0])
        self.assertEqual(sent_data['data'], "test data")

    async def test_send_status_update_async_message_processing_error(self):
        """Test sending status update when message processing fails."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        process_id = "process-456"
        connection = AsyncMock()
        
        # Create mock message that raises exception on to_dict
        message = Mock()
        message.to_dict.side_effect = Exception("Processing error")
        
        config.add_connection(process_id, connection, user_id)
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            await config.send_status_update_async(message, user_id)
            
            mock_logger.error.assert_called()
            connection.send_text.assert_called_once()
            # Should fall back to string representation
            sent_data = json.loads(connection.send_text.call_args[0][0])
            self.assertIsInstance(sent_data['data'], str)

    async def test_send_status_update_async_connection_send_error(self):
        """Test sending status update when connection send fails."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        process_id = "process-456"
        connection = AsyncMock()
        connection.send_text.side_effect = Exception("Send error")
        
        config.add_connection(process_id, connection, user_id)
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            await config.send_status_update_async("test", user_id)
            
            mock_logger.error.assert_called()
            # Connection should be removed after error
            self.assertNotIn(process_id, config.connections)

    def test_add_connection_with_existing_user(self):
        """Test adding connection when user already has a different connection."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        old_process_id = "old-process"
        new_process_id = "new-process"
        old_connection = AsyncMock()
        new_connection = AsyncMock()
        
        # Add first connection
        config.add_connection(old_process_id, old_connection, user_id)
        self.assertEqual(config.user_to_process[user_id], old_process_id)
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            # Add second connection for same user
            config.add_connection(new_process_id, new_connection, user_id)
            
            # New connection should be active and user should be mapped to new process
            self.assertEqual(config.connections[new_process_id], new_connection)
            self.assertEqual(config.user_to_process[user_id], new_process_id)
            # Logger should be called for the old connection handling
            self.assertTrue(mock_logger.info.called or mock_logger.error.called)

    def test_add_connection_old_connection_close_error(self):
        """Test adding connection when closing old connection fails."""
        
        config = ConnectionConfig()
        user_id = "user-123"
        old_process_id = "old-process"
        new_process_id = "new-process"
        old_connection = AsyncMock()
        old_connection.close.side_effect = Exception("Close error")
        new_connection = AsyncMock()
        
        # Add first connection
        config.add_connection(old_process_id, old_connection, user_id)
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            # Add second connection for same user
            config.add_connection(new_process_id, new_connection, user_id)
            
            # Error should be logged
            mock_logger.error.assert_called()
            self.assertEqual(config.connections[new_process_id], new_connection)

    def test_add_connection_existing_process_close_error(self):
        """Test adding connection when closing existing process connection fails."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        old_connection = AsyncMock()
        old_connection.close.side_effect = Exception("Close error")
        new_connection = AsyncMock()
        
        # Add first connection
        config.connections[process_id] = old_connection
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            # Add new connection for same process
            config.add_connection(process_id, new_connection)
            
            # Error should be logged
            mock_logger.error.assert_called()
            self.assertEqual(config.connections[process_id], new_connection)

    def test_send_status_update_sync_with_exception(self):
        """Test sync send status update with exception."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        message = "Test message"
        connection = AsyncMock()
        
        config.add_connection(process_id, connection)
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_create_task.side_effect = Exception("Task creation error")
            
            with patch('backend.v4.config.settings.logger') as mock_logger:
                config.send_status_update(message, process_id)
                
                mock_logger.error.assert_called()

    def test_send_status_update_sync(self):
        """Test sync send status update."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        message = "Test message"
        connection = AsyncMock()
        
        config.add_connection(process_id, connection)
        
        with patch('asyncio.create_task') as mock_create_task:
            config.send_status_update(message, process_id)
            
            mock_create_task.assert_called_once()

    def test_send_status_update_sync_no_connection(self):
        """Test sync send status update with no connection."""
        
        config = ConnectionConfig()
        process_id = "test-process"
        message = "Test message"
        
        with patch('backend.v4.config.settings.logger') as mock_logger:
            config.send_status_update(message, process_id)
            
            mock_logger.warning.assert_called()


class TestGlobalInstances(unittest.TestCase):
    """Test cases for global configuration instances."""

    def test_global_instances_exist(self):
        """Test that all global config instances exist and are of correct types."""
        from backend.v4.config.settings import (
            azure_config,
            connection_config,
            mcp_config,
            orchestration_config,
            team_config,
        )
        
        # Test that all instances exist
        self.assertIsNotNone(azure_config)
        self.assertIsNotNone(mcp_config)
        self.assertIsNotNone(orchestration_config)
        self.assertIsNotNone(connection_config)
        self.assertIsNotNone(team_config)
        
        # Test correct types
        from backend.v4.config.settings import (
            AzureConfig,
            ConnectionConfig,
            MCPConfig,
            OrchestrationConfig,
            TeamConfig,
        )
        
        self.assertIsInstance(azure_config, AzureConfig)
        self.assertIsInstance(mcp_config, MCPConfig)
        self.assertIsInstance(orchestration_config, OrchestrationConfig)
        self.assertIsInstance(connection_config, ConnectionConfig)
        self.assertIsInstance(team_config, TeamConfig)


if __name__ == '__main__':
    unittest.main()

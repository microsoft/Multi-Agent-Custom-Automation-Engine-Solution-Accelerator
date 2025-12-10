"""Unit tests for event_utils module."""

import logging
import sys
import os
from unittest.mock import Mock, patch, MagicMock
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
os.environ.setdefault('COSMOSDB_ENDPOINT', 'https://test.documents.azure.com:443/')
os.environ.setdefault('COSMOSDB_DATABASE', 'test_database')
os.environ.setdefault('COSMOSDB_CONTAINER', 'test_container')
os.environ.setdefault('AZURE_CLIENT_ID', 'test_client_id')
os.environ.setdefault('AZURE_TENANT_ID', 'test_tenant_id')

from common.utils.event_utils import track_event_if_configured


class TestTrackEventIfConfigured:
    """Test track_event_if_configured function."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_valid_configuration(self, mock_config, mock_track_event):
        """Test track_event_if_configured with valid Application Insights configuration."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "InstrumentationKey=test-key;IngestionEndpoint=https://test.com/"
        event_name = "test_event"
        event_data = {"key1": "value1", "key2": "value2"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_called_once_with(event_name, event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_with_no_configuration(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured when Application Insights is not configured."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_not_called()
        mock_logging.warning.assert_called_once_with(
            f"Skipping track_event for {event_name} as Application Insights is not configured"
        )
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_with_empty_configuration(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured with empty connection string."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = ""
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_not_called()
        mock_logging.warning.assert_called_once_with(
            f"Skipping track_event for {event_name} as Application Insights is not configured"
        )
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_handles_attribute_error(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured handles AttributeError (ProxyLogger error)."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        mock_track_event.side_effect = AttributeError("'ProxyLogger' object has no attribute 'resource'")
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_called_once_with(event_name, event_data)
        mock_logging.warning.assert_called_once_with(
            "ProxyLogger error in track_event: 'ProxyLogger' object has no attribute 'resource'"
        )
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_handles_generic_exception(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured handles generic exceptions."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        mock_track_event.side_effect = RuntimeError("Unexpected error occurred")
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_called_once_with(event_name, event_data)
        mock_logging.warning.assert_called_once_with(
            "Error in track_event: Unexpected error occurred"
        )
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_complex_event_data(self, mock_config, mock_track_event):
        """Test track_event_if_configured with complex event data structures."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        event_name = "complex_event"
        event_data = {
            "string_value": "test",
            "number_value": 42,
            "boolean_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"nested_key": "nested_value"},
            "null_value": None
        }
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_called_once_with(event_name, event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_empty_event_data(self, mock_config, mock_track_event):
        """Test track_event_if_configured with empty event data."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        event_name = "empty_data_event"
        event_data = {}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_called_once_with(event_name, event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_special_characters_in_name(self, mock_config, mock_track_event):
        """Test track_event_if_configured with special characters in event name."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        event_name = "test-event_with.special@characters123"
        event_data = {"test": "data"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        mock_track_event.assert_called_once_with(event_name, event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_multiple_calls_with_mixed_scenarios(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured with multiple calls having different scenarios."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # First call - successful
        track_event_if_configured("event1", {"data": "test1"})
        
        # Second call - with AttributeError
        mock_track_event.side_effect = AttributeError("ProxyLogger error")
        track_event_if_configured("event2", {"data": "test2"})
        
        # Third call - reset and successful again
        mock_track_event.side_effect = None
        track_event_if_configured("event3", {"data": "test3"})
        
        # Verify
        assert mock_track_event.call_count == 3
        mock_logging.warning.assert_called_once_with("ProxyLogger error in track_event: ProxyLogger error")


class TestEventUtilsIntegration:
    """Test event_utils integration scenarios."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    @patch('common.utils.event_utils.track_event')
    def test_track_event_with_real_config_module(self, mock_track_event):
        """Test track_event_if_configured with real config module (mocked at track_event level)."""
        # Note: config is already loaded from the real module due to our imports
        # We just need to ensure track_event is mocked to avoid actual Azure calls
        
        event_name = "integration_test_event"
        event_data = {"integration": "test", "timestamp": "2025-12-08"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Since we have APPLICATIONINSIGHTS_CONNECTION_STRING set in environment,
        # track_event should be called
        mock_track_event.assert_called_once_with(event_name, event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_preserves_original_event_data(self, mock_config, mock_track_event):
        """Test that track_event_if_configured preserves original event data."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        original_event_data = {"mutable": ["list"], "dict": {"key": "value"}}
        event_data_copy = original_event_data.copy()
        
        # Execute
        track_event_if_configured("test_event", original_event_data)
        
        # Verify original data is unchanged
        assert original_event_data == event_data_copy
        mock_track_event.assert_called_once_with("test_event", original_event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_logging_behavior_with_different_log_levels(self, mock_logging, mock_config, mock_track_event):
        """Test that warnings are logged at the correct level."""
        # Setup - no configuration
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        
        # Execute
        track_event_if_configured("test_event", {"data": "test"})
        
        # Verify warning level is used
        mock_logging.warning.assert_called_once()
        # Verify other log levels are not called
        assert not hasattr(mock_logging, 'info') or not mock_logging.info.called
        assert not hasattr(mock_logging, 'error') or not mock_logging.error.called


class TestEventUtilsErrorScenarios:
    """Test error scenarios and edge cases for event_utils."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_with_various_attribute_errors(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured with various AttributeError scenarios."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Test different AttributeError messages
        attribute_errors = [
            "'ProxyLogger' object has no attribute 'resource'",
            "'Logger' object has no attribute 'some_method'",
            "module 'azure' has no attribute 'monitor'"
        ]
        
        for error_msg in attribute_errors:
            mock_track_event.side_effect = AttributeError(error_msg)
            track_event_if_configured("test_event", {"data": "test"})
            mock_logging.warning.assert_called_with(f"ProxyLogger error in track_event: {error_msg}")
            mock_logging.reset_mock()
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_with_various_exceptions(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured with various exception types."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Test different exception types
        exceptions = [
            ValueError("Invalid value"),
            TypeError("Type mismatch"),
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            KeyError("Missing key")
        ]
        
        for exception in exceptions:
            mock_track_event.side_effect = exception
            track_event_if_configured("test_event", {"data": "test"})
            mock_logging.warning.assert_called_with(f"Error in track_event: {exception}")
            mock_logging.reset_mock()
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    @patch('common.utils.event_utils.logging')
    def test_track_event_with_whitespace_connection_string(self, mock_logging, mock_config, mock_track_event):
        """Test track_event_if_configured with whitespace-only connection string."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "   "  # Whitespace only
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify - whitespace should be treated as truthy, so track_event should be called
        mock_track_event.assert_called_once_with(event_name, event_data)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_none_event_name(self, mock_config, mock_track_event):
        """Test track_event_if_configured with None event name."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Execute
        track_event_if_configured(None, {"data": "test"})
        
        # Verify - the function should pass None through to track_event
        mock_track_event.assert_called_once_with(None, {"data": "test"})
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_none_event_data(self, mock_config, mock_track_event):
        """Test track_event_if_configured with None event data."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Execute
        track_event_if_configured("test_event", None)
        
        # Verify - the function should pass None through to track_event
        mock_track_event.assert_called_once_with("test_event", None)


class TestEventUtilsParameterValidation:
    """Test parameter validation and type handling for event_utils."""
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_string_types(self, mock_config, mock_track_event):
        """Test track_event_if_configured with various string types."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Test with different string types
        string_types = [
            "",  # Empty string
            "simple_string",  # Simple string
            "string with spaces",  # String with spaces
            "string_with_unicode_café",  # Unicode string
            "very_long_string_" + "x" * 1000  # Long string
        ]
        
        for event_name in string_types:
            track_event_if_configured(event_name, {"type": "string_test"})
            mock_track_event.assert_called_with(event_name, {"type": "string_test"})
        
        assert mock_track_event.call_count == len(string_types)
    
    @patch('common.utils.event_utils.track_event')
    @patch('common.utils.event_utils.config')
    def test_track_event_with_different_data_types(self, mock_config, mock_track_event):
        """Test track_event_if_configured with different event data types."""
        # Setup
        mock_config.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Test with different data types
        data_types = [
            {"string": "value"},
            {"integer": 42},
            {"float": 3.14},
            {"boolean": True},
            {"list": [1, 2, 3]},
            {"nested_dict": {"inner": {"deep": "value"}}},
            {"mixed": {"str": "text", "num": 123, "bool": False}}
        ]
        
        for i, event_data in enumerate(data_types):
            track_event_if_configured(f"test_event_{i}", event_data)
            mock_track_event.assert_called_with(f"test_event_{i}", event_data)
        
        assert mock_track_event.call_count == len(data_types)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
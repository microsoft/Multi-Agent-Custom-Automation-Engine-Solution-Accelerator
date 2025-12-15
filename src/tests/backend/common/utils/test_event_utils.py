"""Unit tests for event_utils module."""

import logging
import sys
import os
import types
from unittest.mock import Mock, patch, MagicMock
import pytest
from pathlib import Path

# REMOVED: azure.monitor.events.extension and config sys.modules pollution
# This pollution was causing isinstance() failures across test files
# Each test should use @patch decorators for its specific mocking needs

# Create mock config object for testing
mock_config_obj = Mock()
mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None

# Import the module AFTER setting up mocks
import common.utils.event_utils
from common.utils.event_utils import track_event_if_configured


class TestTrackEventIfConfigured:
    """Test track_event_if_configured function."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Reset module-level mocks
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        # Replace track_event in the module with a fresh Mock
        common.utils.event_utils.track_event = Mock()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    def test_track_event_with_valid_configuration(self):
        """Test track_event_if_configured with valid Application Insights configuration."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "InstrumentationKey=test-key;IngestionEndpoint=https://test.com/"
        event_name = "test_event"
        event_data = {"key1": "value1", "key2": "value2"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
    
    def test_track_event_with_no_configuration(self):
        """Test track_event_if_configured when Application Insights is not configured."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            # Execute
            track_event_if_configured(event_name, event_data)
            
            # Verify
            common.utils.event_utils.track_event.assert_not_called()
            mock_warning.assert_called_once_with(
                f"Skipping track_event for {event_name} as Application Insights is not configured"
            )
    
    def test_track_event_with_empty_configuration(self):
        """Test track_event_if_configured with empty connection string."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = ""
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            # Execute
            track_event_if_configured(event_name, event_data)
            
            # Verify
            common.utils.event_utils.track_event.assert_not_called()
            mock_warning.assert_called_once_with(
                f"Skipping track_event for {event_name} as Application Insights is not configured"
            )
    
    def test_track_event_handles_attribute_error(self):
        """Test track_event_if_configured handles AttributeError (ProxyLogger error)."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        common.utils.event_utils.track_event.side_effect = AttributeError("'ProxyLogger' object has no attribute 'resource'")
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            # Execute
            track_event_if_configured(event_name, event_data)
            
            # Verify
            common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
            mock_warning.assert_called_once_with(
                "ProxyLogger error in track_event: 'ProxyLogger' object has no attribute 'resource'"
            )
    
    def test_track_event_handles_generic_exception(self):
        """Test track_event_if_configured handles generic exceptions."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        common.utils.event_utils.track_event.side_effect = RuntimeError("Unexpected error occurred")
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            # Execute
            track_event_if_configured(event_name, event_data)
            
            # Verify
            common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
            mock_warning.assert_called_once_with(
                "Error in track_event: Unexpected error occurred"
            )
    
    def test_track_event_with_complex_event_data(self):
        """Test track_event_if_configured with complex event data structures."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
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
        common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
    
    def test_track_event_with_empty_event_data(self):
        """Test track_event_if_configured with empty event data."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        event_name = "empty_data_event"
        event_data = {}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
    
    def test_track_event_with_special_characters_in_name(self):
        """Test track_event_if_configured with special characters in event name."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        event_name = "test-event_with.special@characters123"
        event_data = {"test": "data"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify
        common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
    
    def test_track_event_multiple_calls_with_mixed_scenarios(self):
        """Test track_event_if_configured with multiple calls having different scenarios."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            # First call - successful
            track_event_if_configured("event1", {"data": "test1"})
            
            # Second call - with AttributeError
            common.utils.event_utils.track_event.side_effect = AttributeError("ProxyLogger error")
            track_event_if_configured("event2", {"data": "test2"})
            
            # Third call - reset and successful again
            common.utils.event_utils.track_event.side_effect = None
            track_event_if_configured("event3", {"data": "test3"})
            
            # Verify
            assert common.utils.event_utils.track_event.call_count == 3
            mock_warning.assert_called_once_with("ProxyLogger error in track_event: ProxyLogger error")


class TestEventUtilsIntegration:
    """Test event_utils integration scenarios."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Reset module-level mocks
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        common.utils.event_utils.track_event = Mock()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    def test_track_event_with_real_config_module(self):
        """Test track_event_if_configured with real config module (mocked at track_event level)."""
        # Setup config to have a connection string
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "InstrumentationKey=test-key;"
        
        event_name = "integration_test_event"
        event_data = {"integration": "test", "timestamp": "2025-12-08"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify track_event was called
        common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
    
    def test_track_event_preserves_original_event_data(self):
        """Test that track_event_if_configured preserves original event data."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        original_event_data = {"mutable": ["list"], "dict": {"key": "value"}}
        event_data_copy = original_event_data.copy()
        
        # Execute
        track_event_if_configured("test_event", original_event_data)
        
        # Verify original data is unchanged
        assert original_event_data == event_data_copy
        common.utils.event_utils.track_event.assert_called_once_with("test_event", original_event_data)
    
    def test_logging_behavior_with_different_log_levels(self):
        """Test that warnings are logged at the correct level."""
        # Setup - no configuration
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            # Execute
            track_event_if_configured("test_event", {"data": "test"})
            
            # Verify warning level is used
            mock_warning.assert_called_once()


class TestEventUtilsErrorScenarios:
    """Test error scenarios and edge cases for event_utils."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Reset module-level mocks
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        common.utils.event_utils.track_event = Mock()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear any cached logging handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    def test_track_event_with_various_attribute_errors(self):
        """Test track_event_if_configured with various AttributeError scenarios."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Test different AttributeError messages
        attribute_errors = [
            "'ProxyLogger' object has no attribute 'resource'",
            "'Logger' object has no attribute 'some_method'",
            "module 'azure' has no attribute 'monitor'"
        ]
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            for error_msg in attribute_errors:
                common.utils.event_utils.track_event.side_effect = AttributeError(error_msg)
                track_event_if_configured("test_event", {"data": "test"})
                mock_warning.assert_called_with(f"ProxyLogger error in track_event: {error_msg}")
                mock_warning.reset_mock()
                common.utils.event_utils.track_event.side_effect = None
    
    def test_track_event_with_various_exceptions(self):
        """Test track_event_if_configured with various exception types."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Test different exception types
        exceptions = [
            ValueError("Invalid value"),
            TypeError("Type mismatch"),
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            KeyError("Missing key")
        ]
        
        with patch('backend.common.utils.event_utils.logging.warning') as mock_warning:
            for exception in exceptions:
                common.utils.event_utils.track_event.side_effect = exception
                track_event_if_configured("test_event", {"data": "test"})
                mock_warning.assert_called_with(f"Error in track_event: {exception}")
                mock_warning.reset_mock()
                common.utils.event_utils.track_event.side_effect = None
    
    def test_track_event_with_whitespace_connection_string(self):
        """Test track_event_if_configured with whitespace-only connection string."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "   "  # Whitespace only
        event_name = "test_event"
        event_data = {"key1": "value1"}
        
        # Execute
        track_event_if_configured(event_name, event_data)
        
        # Verify - whitespace should be treated as truthy, so track_event should be called
        common.utils.event_utils.track_event.assert_called_once_with(event_name, event_data)
    
    def test_track_event_with_none_event_name(self):
        """Test track_event_if_configured with None event name."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Execute
        track_event_if_configured(None, {"data": "test"})
        
        # Verify - the function should pass None through to track_event
        common.utils.event_utils.track_event.assert_called_once_with(None, {"data": "test"})
    
    def test_track_event_with_none_event_data(self):
        """Test track_event_if_configured with None event data."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
        # Execute
        track_event_if_configured("test_event", None)
        
        # Verify - the function should pass None through to track_event
        common.utils.event_utils.track_event.assert_called_once_with("test_event", None)


class TestEventUtilsParameterValidation:
    """Test parameter validation and type handling for event_utils."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset module-level mocks
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = None
        common.utils.event_utils.track_event = Mock()
    
    def test_track_event_with_string_types(self):
        """Test track_event_if_configured with various string types."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
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
            common.utils.event_utils.track_event.assert_called_with(event_name, {"type": "string_test"})
        
        assert common.utils.event_utils.track_event.call_count == len(string_types)
    
    def test_track_event_with_different_data_types(self):
        """Test track_event_if_configured with different event data types."""
        # Setup
        mock_config_obj.APPLICATIONINSIGHTS_CONNECTION_STRING = "valid_connection_string"
        
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
            common.utils.event_utils.track_event.assert_called_with(f"test_event_{i}", event_data)
        
        assert common.utils.event_utils.track_event.call_count == len(data_types)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
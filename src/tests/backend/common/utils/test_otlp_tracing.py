"""Unit tests for otlp_tracing module."""

import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
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

from common.utils.otlp_tracing import configure_oltp_tracing


class TestConfigureOltpTracing:
    """Test configure_oltp_tracing function."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset any global state that might affect tests
        pass
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clean up any global state changes
        pass
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_default_parameters(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing with default parameters."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        # Execute
        result = configure_oltp_tracing()
        
        # Verify Resource creation
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        
        # Verify TracerProvider creation
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        
        # Verify OTLPSpanExporter creation
        mock_exporter.assert_called_once_with()
        
        # Verify BatchSpanProcessor creation
        mock_processor.assert_called_once_with(mock_exporter_instance)
        
        # Verify span processor is added to tracer provider
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        
        # Verify tracer provider is set globally
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
        
        # Verify return value
        assert result is mock_tracer_provider_instance
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_with_endpoint_parameter(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing with endpoint parameter (currently unused)."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        # Execute with endpoint parameter
        endpoint = "https://test-otlp-endpoint.com"
        result = configure_oltp_tracing(endpoint=endpoint)
        
        # Verify the same behavior as default case (endpoint parameter is currently unused)
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
        
        # Verify return value
        assert result is mock_tracer_provider_instance
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_with_none_endpoint(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing with explicitly None endpoint."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        # Execute with None endpoint
        result = configure_oltp_tracing(endpoint=None)
        
        # Verify the same behavior as default case
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
        
        # Verify return value
        assert result is mock_tracer_provider_instance
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_multiple_calls(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test multiple calls to configure_oltp_tracing."""
        # Setup mocks for first call
        mock_resource_instance1 = Mock()
        mock_exporter_instance1 = Mock()
        mock_processor_instance1 = Mock()
        mock_tracer_provider_instance1 = Mock()
        
        # Setup mocks for second call
        mock_resource_instance2 = Mock()
        mock_exporter_instance2 = Mock()
        mock_processor_instance2 = Mock()
        mock_tracer_provider_instance2 = Mock()
        
        # Configure side effects for multiple calls
        mock_resource.side_effect = [mock_resource_instance1, mock_resource_instance2]
        mock_exporter.side_effect = [mock_exporter_instance1, mock_exporter_instance2]
        mock_processor.side_effect = [mock_processor_instance1, mock_processor_instance2]
        mock_tracer_provider_class.side_effect = [mock_tracer_provider_instance1, mock_tracer_provider_instance2]
        
        # Execute first call
        result1 = configure_oltp_tracing()
        
        # Execute second call
        result2 = configure_oltp_tracing(endpoint="https://different-endpoint.com")
        
        # Verify both calls were made
        assert mock_resource.call_count == 2
        assert mock_exporter.call_count == 2
        assert mock_processor.call_count == 2
        assert mock_tracer_provider_class.call_count == 2
        assert mock_trace.set_tracer_provider.call_count == 2
        
        # Verify return values
        assert result1 is mock_tracer_provider_instance1
        assert result2 is mock_tracer_provider_instance2


class TestConfigureOltpTracingErrorHandling:
    """Test error handling scenarios for configure_oltp_tracing."""
    
    def setup_method(self):
        """Setup for each test method."""
        pass
    
    def teardown_method(self):
        """Cleanup after each test method."""
        pass
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_resource_creation_error(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing when Resource creation fails."""
        # Setup
        mock_resource.side_effect = Exception("Resource creation failed")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Resource creation failed"):
            configure_oltp_tracing()
        
        # Verify that subsequent operations were not called
        mock_tracer_provider_class.assert_not_called()
        mock_exporter.assert_not_called()
        mock_processor.assert_not_called()
        mock_trace.set_tracer_provider.assert_not_called()
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_tracer_provider_creation_error(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing when TracerProvider creation fails."""
        # Setup
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        mock_tracer_provider_class.side_effect = Exception("TracerProvider creation failed")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="TracerProvider creation failed"):
            configure_oltp_tracing()
        
        # Verify Resource was created but subsequent operations were not called
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_exporter.assert_not_called()
        mock_processor.assert_not_called()
        mock_trace.set_tracer_provider.assert_not_called()
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_exporter_creation_error(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing when OTLPSpanExporter creation fails."""
        # Setup
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter.side_effect = Exception("Exporter creation failed")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Exporter creation failed"):
            configure_oltp_tracing()
        
        # Verify creation up to exporter was called
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        
        # Verify subsequent operations were not called
        mock_processor.assert_not_called()
        mock_tracer_provider_instance.add_span_processor.assert_not_called()
        mock_trace.set_tracer_provider.assert_not_called()
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_processor_creation_error(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing when BatchSpanProcessor creation fails."""
        # Setup
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor.side_effect = Exception("Processor creation failed")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Processor creation failed"):
            configure_oltp_tracing()
        
        # Verify creation up to processor was called
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        
        # Verify subsequent operations were not called
        mock_tracer_provider_instance.add_span_processor.assert_not_called()
        mock_trace.set_tracer_provider.assert_not_called()
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_add_span_processor_error(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing when add_span_processor fails."""
        # Setup
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_instance.add_span_processor.side_effect = Exception("Add processor failed")
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Add processor failed"):
            configure_oltp_tracing()
        
        # Verify all creation steps were called
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        
        # Verify set_tracer_provider was not called
        mock_trace.set_tracer_provider.assert_not_called()
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_set_tracer_provider_error(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing when set_tracer_provider fails."""
        # Setup
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_trace.set_tracer_provider.side_effect = Exception("Set tracer provider failed")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Set tracer provider failed"):
            configure_oltp_tracing()
        
        # Verify all steps up to set_tracer_provider were called
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)


class TestConfigureOltpTracingIntegration:
    """Test integration scenarios for configure_oltp_tracing."""
    
    def setup_method(self):
        """Setup for each test method."""
        pass
    
    def teardown_method(self):
        """Cleanup after each test method."""
        pass
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_service_name_configuration(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test that service name is correctly configured."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        # Execute
        result = configure_oltp_tracing()
        
        # Verify service name is set correctly
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        
        # Verify the resource is used in TracerProvider
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        
        # Verify return value
        assert result is mock_tracer_provider_instance
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_call_sequence(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test that configure_oltp_tracing calls functions in the correct sequence."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        # Execute
        result = configure_oltp_tracing()
        
        # Verify call sequence using call order
        expected_calls = [
            call({"service.name": "macwe"}),  # Resource creation
        ]
        mock_resource.assert_has_calls(expected_calls)
        
        # Verify TracerProvider was created with resource
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        
        # Verify exporter and processor creation order
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        
        # Verify processor is added to tracer provider
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        
        # Verify global tracer provider is set
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)


class TestConfigureOltpTracingParameterHandling:
    """Test parameter handling for configure_oltp_tracing."""
    
    def setup_method(self):
        """Setup for each test method."""
        pass
    
    def teardown_method(self):
        """Cleanup after each test method."""
        pass
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_with_empty_string_endpoint(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test configure_oltp_tracing with empty string endpoint."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        # Execute with empty string endpoint
        result = configure_oltp_tracing(endpoint="")
        
        # Verify same behavior as default (endpoint parameter is unused in current implementation)
        mock_resource.assert_called_once_with({"service.name": "macwe"})
        mock_tracer_provider_class.assert_called_once_with(resource=mock_resource_instance)
        mock_exporter.assert_called_once_with()
        mock_processor.assert_called_once_with(mock_exporter_instance)
        mock_tracer_provider_instance.add_span_processor.assert_called_once_with(mock_processor_instance)
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider_instance)
        
        assert result is mock_tracer_provider_instance
    
    @patch('common.utils.otlp_tracing.trace')
    @patch('common.utils.otlp_tracing.TracerProvider')
    @patch('common.utils.otlp_tracing.BatchSpanProcessor')
    @patch('common.utils.otlp_tracing.OTLPSpanExporter')
    @patch('common.utils.otlp_tracing.Resource')
    def test_configure_oltp_tracing_function_signature(
        self, mock_resource, mock_exporter, mock_processor, mock_tracer_provider_class, mock_trace
    ):
        """Test that configure_oltp_tracing accepts the expected parameters."""
        # Setup mocks
        mock_resource_instance = Mock()
        mock_resource.return_value = mock_resource_instance
        
        mock_tracer_provider_instance = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider_instance
        
        mock_exporter_instance = Mock()
        mock_exporter.return_value = mock_exporter_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        # Test various ways to call the function
        
        # No parameters
        result1 = configure_oltp_tracing()
        assert result1 is mock_tracer_provider_instance
        
        # Positional parameter
        result2 = configure_oltp_tracing("https://endpoint.com")
        assert result2 is mock_tracer_provider_instance
        
        # Keyword parameter
        result3 = configure_oltp_tracing(endpoint="https://endpoint.com")
        assert result3 is mock_tracer_provider_instance
        
        # Verify all calls succeeded and returned tracer provider
        assert mock_tracer_provider_class.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
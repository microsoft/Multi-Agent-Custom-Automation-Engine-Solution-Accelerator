import os
from src.backend.common.utils.otlp_tracing import (
    configure_oltp_tracing,
)  # Import directly since it's in backend

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@patch("src.backend.common.utils.otlp_tracing.TracerProvider")
@patch("src.backend.common.utils.otlp_tracing.OTLPSpanExporter")
@patch("src.backend.common.utils.otlp_tracing.Resource")
def test_configure_oltp_tracing(
    mock_resource,
    mock_otlp_exporter,
    mock_tracer_provider,
):
    # Mock the Resource
    mock_resource_instance = MagicMock()
    mock_resource.return_value = mock_resource_instance

    # Mock TracerProvider
    mock_tracer_provider_instance = MagicMock()
    mock_tracer_provider.return_value = mock_tracer_provider_instance

    # Mock OTLPSpanExporter
    mock_otlp_exporter_instance = MagicMock()
    mock_otlp_exporter.return_value = mock_otlp_exporter_instance

    # Call the function
    endpoint = "mock-endpoint"
    tracer_provider = configure_oltp_tracing(endpoint=endpoint)

    # Assertions
    mock_tracer_provider.assert_called_once_with(resource=mock_resource_instance)
    mock_otlp_exporter.assert_called_once_with()
    mock_tracer_provider_instance.add_span_processor.assert_called_once()
    assert tracer_provider == mock_tracer_provider_instance

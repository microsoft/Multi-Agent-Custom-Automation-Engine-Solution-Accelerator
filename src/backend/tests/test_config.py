# tests/test_config.py
from unittest.mock import patch
import os

# Mock environment variables globally
MOCK_ENV_VARS = {
    "COSMOSDB_ENDPOINT": "https://mock-cosmosdb.documents.azure.com:443/",
    "COSMOSDB_DATABASE": "mock_database",
    "COSMOSDB_CONTAINER": "mock_container",
    "AZURE_OPENAI_DEPLOYMENT_NAME": "mock-deployment",
    "AZURE_OPENAI_API_VERSION": "2024-05-01-preview",
    "AZURE_OPENAI_ENDPOINT": "https://mock-openai-endpoint.azure.com/",
    "AZURE_OPENAI_API_KEY": "mock-api-key",
    "AZURE_TENANT_ID": "mock-tenant-id",
    "AZURE_CLIENT_ID": "mock-client-id",
    "AZURE_CLIENT_SECRET": "mock-client-secret",
}

with patch.dict(os.environ, MOCK_ENV_VARS):
    from src.backend.config import (
        Config,
        GetRequiredConfig,
        GetOptionalConfig,
        GetBoolConfig,
    )


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_get_required_config():
    """Test GetRequiredConfig."""
    assert GetRequiredConfig("COSMOSDB_ENDPOINT") == MOCK_ENV_VARS["COSMOSDB_ENDPOINT"]


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_get_optional_config():
    """Test GetOptionalConfig."""
    assert GetOptionalConfig("NON_EXISTENT_VAR", "default_value") == "default_value"
    assert (
        GetOptionalConfig("COSMOSDB_DATABASE", "default_db")
        == MOCK_ENV_VARS["COSMOSDB_DATABASE"]
    )


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_get_bool_config():
    """Test GetBoolConfig."""
    with patch.dict("os.environ", {"FEATURE_ENABLED": "true"}):
        assert GetBoolConfig("FEATURE_ENABLED") is True
    with patch.dict("os.environ", {"FEATURE_ENABLED": "false"}):
        assert GetBoolConfig("FEATURE_ENABLED") is False
    with patch.dict("os.environ", {"FEATURE_ENABLED": "1"}):
        assert GetBoolConfig("FEATURE_ENABLED") is True
    with patch.dict("os.environ", {"FEATURE_ENABLED": "0"}):
        assert GetBoolConfig("FEATURE_ENABLED") is False

# src/backend/tests/test_config.py
import os
import sys
from unittest.mock import patch

# Make repo root importable so `src.backend...` works
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Mock environment variables so app_config can construct safely at import time
MOCK_ENV_VARS = {
    # Cosmos
    "COSMOSDB_ENDPOINT": "https://mock-cosmosdb.documents.azure.com:443/",
    "COSMOSDB_DATABASE": "mock_database",
    "COSMOSDB_CONTAINER": "mock_container",
    # Azure OpenAI
    "AZURE_OPENAI_DEPLOYMENT_NAME": "mock-deployment",
    "AZURE_OPENAI_API_VERSION": "2024-11-20",
    "AZURE_OPENAI_ENDPOINT": "https://mock-openai-endpoint.azure.com/",
    # Optional auth (kept for completeness)
    "AZURE_TENANT_ID": "mock-tenant-id",
    "AZURE_CLIENT_ID": "mock-client-id",
    "AZURE_CLIENT_SECRET": "mock-client-secret",
    # Azure AI Project (required by current AppConfig)
    "AZURE_AI_SUBSCRIPTION_ID": "00000000-0000-0000-0000-000000000000",
    "AZURE_AI_RESOURCE_GROUP": "rg-test",
    "AZURE_AI_PROJECT_NAME": "proj-test",
    "AZURE_AI_AGENT_ENDPOINT": "https://agents.example.com/",
    # Misc
    "USER_LOCAL_BROWSER_LANGUAGE": "en-US",
}

# Import the current config objects/functions under the mocked env
with patch.dict(os.environ, MOCK_ENV_VARS, clear=False):
    # New codebase: config lives in app_config/config_kernel
    from src.backend.common.config.app_config import config as app_config

# Provide thin wrappers so the old test names still work
def GetRequiredConfig(name: str, default=None):
    return app_config._get_required(name, default)


def GetOptionalConfig(name: str, default: str = ""):
    return app_config._get_optional(name, default)


def GetBoolConfig(name: str) -> bool:
    return app_config._get_bool(name)


# ---- Tests (unchanged semantics) ----


@patch.dict(os.environ, MOCK_ENV_VARS, clear=False)
def test_get_required_config():
    assert GetRequiredConfig("COSMOSDB_ENDPOINT") == MOCK_ENV_VARS["COSMOSDB_ENDPOINT"]


@patch.dict(os.environ, MOCK_ENV_VARS, clear=False)
def test_get_optional_config():
    assert GetOptionalConfig("NON_EXISTENT_VAR", "default_value") == "default_value"
    assert (
        GetOptionalConfig("COSMOSDB_DATABASE", "default_db")
        == MOCK_ENV_VARS["COSMOSDB_DATABASE"]
    )


@patch.dict(os.environ, MOCK_ENV_VARS, clear=False)
def test_get_bool_config():
    with patch.dict("os.environ", {"FEATURE_ENABLED": "true"}):
        assert GetBoolConfig("FEATURE_ENABLED") is True
    with patch.dict("os.environ", {"FEATURE_ENABLED": "false"}):
        assert GetBoolConfig("FEATURE_ENABLED") is False
    with patch.dict("os.environ", {"FEATURE_ENABLED": "1"}):
        assert GetBoolConfig("FEATURE_ENABLED") is True
    with patch.dict("os.environ", {"FEATURE_ENABLED": "0"}):
        assert GetBoolConfig("FEATURE_ENABLED") is False

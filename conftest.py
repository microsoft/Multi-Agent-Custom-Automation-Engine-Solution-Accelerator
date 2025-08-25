"""
Test configuration for agent tests.
"""

import sys
from pathlib import Path

import pytest

# Add the agents path
agents_path = Path(__file__).parent.parent.parent / "backend" / "v3" / "magentic_agents"
sys.path.insert(0, str(agents_path))

@pytest.fixture
def agent_env_vars():
    """Common environment variables for agent testing."""
    return {
        "BING_CONNECTION_NAME": "test_bing_connection",
        "MCP_SERVER_ENDPOINT": "http://test-mcp-server",
        "MCP_SERVER_NAME": "test_mcp_server", 
        "MCP_SERVER_DESCRIPTION": "Test MCP server",
        "TENANT_ID": "test_tenant_id",
        "CLIENT_ID": "test_client_id",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test_key",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "test_deployment"
    }
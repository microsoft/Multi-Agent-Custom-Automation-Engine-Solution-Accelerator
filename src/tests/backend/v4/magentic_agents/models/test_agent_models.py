"""
Unit tests for v4 agent models.

Tests cover:
- MCPConfig class initialization and from_env method
- SearchConfig class initialization and from_env method  
- Error handling for missing environment variables
- Dataclass functionality and validation
"""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path
from dataclasses import FrozenInstanceError

# Add backend path to sys.path for proper imports
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the real models for coverage
from v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig


class TestMCPConfig:
    """Test MCPConfig dataclass."""

    def test_mcp_config_default_initialization(self):
        """Test MCPConfig with default values."""
        config = MCPConfig()
        
        assert config.url == ""
        assert config.name == "MCP"
        assert config.description == ""
        assert config.tenant_id == ""
        assert config.client_id == ""

    def test_mcp_config_custom_initialization(self):
        """Test MCPConfig with custom values."""
        config = MCPConfig(
            url="http://test.com",
            name="TestMCP",
            description="Test Description",
            tenant_id="test-tenant",
            client_id="test-client"
        )
        
        assert config.url == "http://test.com"
        assert config.name == "TestMCP"
        assert config.description == "Test Description"
        assert config.tenant_id == "test-tenant"
        assert config.client_id == "test-client"

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_mcp_config_from_env_success(self, mock_config):
        """Test MCPConfig.from_env with all required environment variables."""
        # Mock config values
        mock_config.MCP_SERVER_ENDPOINT = "http://mcp.test.com"
        mock_config.MCP_SERVER_NAME = "TestServer"
        mock_config.MCP_SERVER_DESCRIPTION = "Test Server Description"
        mock_config.AZURE_TENANT_ID = "test-tenant-123"
        mock_config.AZURE_CLIENT_ID = "test-client-456"
        
        config = MCPConfig.from_env()
        
        assert config.url == "http://mcp.test.com"
        assert config.name == "TestServer"
        assert config.description == "Test Server Description"
        assert config.tenant_id == "test-tenant-123"
        assert config.client_id == "test-client-456"

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_mcp_config_from_env_missing_url(self, mock_config):
        """Test MCPConfig.from_env with missing URL."""
        mock_config.MCP_SERVER_ENDPOINT = ""  # Missing
        mock_config.MCP_SERVER_NAME = "TestServer"
        mock_config.MCP_SERVER_DESCRIPTION = "Test Description"
        mock_config.AZURE_TENANT_ID = "test-tenant"
        mock_config.AZURE_CLIENT_ID = "test-client"
        
        with pytest.raises(ValueError, match="MCPConfig Missing required environment variables"):
            MCPConfig.from_env()

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_mcp_config_from_env_missing_name(self, mock_config):
        """Test MCPConfig.from_env with missing name."""
        mock_config.MCP_SERVER_ENDPOINT = "http://test.com"
        mock_config.MCP_SERVER_NAME = ""  # Missing
        mock_config.MCP_SERVER_DESCRIPTION = "Test Description"
        mock_config.AZURE_TENANT_ID = "test-tenant"
        mock_config.AZURE_CLIENT_ID = "test-client"
        
        with pytest.raises(ValueError, match="MCPConfig Missing required environment variables"):
            MCPConfig.from_env()

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_mcp_config_from_env_missing_description(self, mock_config):
        """Test MCPConfig.from_env with missing description."""
        mock_config.MCP_SERVER_ENDPOINT = "http://test.com"
        mock_config.MCP_SERVER_NAME = "TestServer"
        mock_config.MCP_SERVER_DESCRIPTION = ""  # Missing
        mock_config.AZURE_TENANT_ID = "test-tenant"
        mock_config.AZURE_CLIENT_ID = "test-client"
        
        with pytest.raises(ValueError, match="MCPConfig Missing required environment variables"):
            MCPConfig.from_env()

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_mcp_config_from_env_missing_tenant_id(self, mock_config):
        """Test MCPConfig.from_env with missing tenant ID."""
        mock_config.MCP_SERVER_ENDPOINT = "http://test.com"
        mock_config.MCP_SERVER_NAME = "TestServer"
        mock_config.MCP_SERVER_DESCRIPTION = "Test Description"
        mock_config.AZURE_TENANT_ID = ""  # Missing
        mock_config.AZURE_CLIENT_ID = "test-client"
        
        with pytest.raises(ValueError, match="MCPConfig Missing required environment variables"):
            MCPConfig.from_env()

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_mcp_config_from_env_missing_client_id(self, mock_config):
        """Test MCPConfig.from_env with missing client ID."""
        mock_config.MCP_SERVER_ENDPOINT = "http://test.com"
        mock_config.MCP_SERVER_NAME = "TestServer"
        mock_config.MCP_SERVER_DESCRIPTION = "Test Description"
        mock_config.AZURE_TENANT_ID = "test-tenant"
        mock_config.AZURE_CLIENT_ID = ""  # Missing
        
        with pytest.raises(ValueError, match="MCPConfig Missing required environment variables"):
            MCPConfig.from_env()

    def test_mcp_config_dataclass_slots(self):
        """Test that MCPConfig uses slots for efficiency."""
        config = MCPConfig()
        
        # Should not be able to add arbitrary attributes due to slots
        with pytest.raises(AttributeError):
            config.new_attribute = "test"

    def test_mcp_config_equality(self):
        """Test MCPConfig equality comparison."""
        config1 = MCPConfig(url="test", name="test")
        config2 = MCPConfig(url="test", name="test")
        config3 = MCPConfig(url="different", name="test")
        
        assert config1 == config2
        assert config1 != config3

    def test_mcp_config_repr(self):
        """Test MCPConfig string representation."""
        config = MCPConfig(url="test", name="TestMCP")
        repr_str = repr(config)
        
        assert "MCPConfig" in repr_str
        assert "test" in repr_str
        assert "TestMCP" in repr_str


class TestSearchConfig:
    """Test SearchConfig dataclass."""

    def test_search_config_default_initialization(self):
        """Test SearchConfig with default values."""
        config = SearchConfig()
        
        assert config.connection_name is None
        assert config.endpoint is None
        assert config.index_name is None

    def test_search_config_custom_initialization(self):
        """Test SearchConfig with custom values."""
        config = SearchConfig(
            connection_name="test-connection",
            endpoint="https://search.test.com",
            index_name="test-index"
        )
        
        assert config.connection_name == "test-connection"
        assert config.endpoint == "https://search.test.com"
        assert config.index_name == "test-index"

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_search_config_from_env_success(self, mock_config):
        """Test SearchConfig.from_env with all required environment variables."""
        mock_config.AZURE_AI_SEARCH_CONNECTION_NAME = "test-search-connection"
        mock_config.AZURE_AI_SEARCH_ENDPOINT = "https://search.endpoint.com"
        
        config = SearchConfig.from_env("test-index")
        
        assert config.connection_name == "test-search-connection"
        assert config.endpoint == "https://search.endpoint.com"
        assert config.index_name == "test-index"

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_search_config_from_env_missing_connection_name(self, mock_config):
        """Test SearchConfig.from_env with missing connection name."""
        mock_config.AZURE_AI_SEARCH_CONNECTION_NAME = ""  # Missing
        mock_config.AZURE_AI_SEARCH_ENDPOINT = "https://search.endpoint.com"
        
        with pytest.raises(ValueError, match="SearchConfig Missing required Azure Search environment variables"):
            SearchConfig.from_env("test-index")

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_search_config_from_env_missing_endpoint(self, mock_config):
        """Test SearchConfig.from_env with missing endpoint."""
        mock_config.AZURE_AI_SEARCH_CONNECTION_NAME = "test-connection"
        mock_config.AZURE_AI_SEARCH_ENDPOINT = ""  # Missing
        
        with pytest.raises(ValueError, match="SearchConfig Missing required Azure Search environment variables"):
            SearchConfig.from_env("test-index")

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_search_config_from_env_empty_index_name(self, mock_config):
        """Test SearchConfig.from_env with empty index name."""
        mock_config.AZURE_AI_SEARCH_CONNECTION_NAME = "test-connection"
        mock_config.AZURE_AI_SEARCH_ENDPOINT = "https://search.endpoint.com"
        
        with pytest.raises(ValueError, match="SearchConfig Missing required Azure Search environment variables"):
            SearchConfig.from_env("")  # Empty index name

    def test_search_config_dataclass_slots(self):
        """Test that SearchConfig uses slots for efficiency."""
        config = SearchConfig()
        
        # Should not be able to add arbitrary attributes due to slots
        with pytest.raises(AttributeError):
            config.new_attribute = "test"

    def test_search_config_equality(self):
        """Test SearchConfig equality comparison."""
        config1 = SearchConfig(connection_name="test", endpoint="test")
        config2 = SearchConfig(connection_name="test", endpoint="test")
        config3 = SearchConfig(connection_name="different", endpoint="test")
        
        assert config1 == config2
        assert config1 != config3

    def test_search_config_repr(self):
        """Test SearchConfig string representation."""
        config = SearchConfig(connection_name="test-conn", index_name="test-index")
        repr_str = repr(config)
        
        assert "SearchConfig" in repr_str
        assert "test-conn" in repr_str
        assert "test-index" in repr_str


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_none_values(self):
        """Test configs with None values."""
        mcp_config = MCPConfig(url=None, name=None)
        search_config = SearchConfig(connection_name=None, endpoint=None)
        
        # Should handle None values gracefully
        assert mcp_config.url is None
        assert search_config.connection_name is None

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_config_from_env_with_whitespace(self, mock_config):
        """Test config from_env with whitespace values."""
        mock_config.MCP_SERVER_ENDPOINT = "  "  # Just whitespace
        mock_config.MCP_SERVER_NAME = "TestServer"
        mock_config.MCP_SERVER_DESCRIPTION = "Test"
        mock_config.AZURE_TENANT_ID = "tenant"
        mock_config.AZURE_CLIENT_ID = "client"
        
        # The current implementation doesn't strip whitespace, so this should pass
        # Let's test that whitespace is preserved as is
        config = MCPConfig.from_env()
        assert config.url == "  "  # Whitespace is preserved

    @patch('v4.magentic_agents.models.agent_models.config')
    def test_search_config_from_env_special_characters(self, mock_config):
        """Test SearchConfig.from_env with special characters in index name."""
        mock_config.AZURE_AI_SEARCH_CONNECTION_NAME = "test-connection"
        mock_config.AZURE_AI_SEARCH_ENDPOINT = "https://search.endpoint.com"
        
        config = SearchConfig.from_env("test-index_123")
        
        assert config.index_name == "test-index_123"

    def test_config_immutability(self):
        """Test that dataclass fields can be modified (not frozen)."""
        mcp_config = MCPConfig()
        search_config = SearchConfig()
        
        # Should be able to modify fields (not frozen)
        mcp_config.url = "new-url"
        search_config.endpoint = "new-endpoint"
        
        assert mcp_config.url == "new-url"
        assert search_config.endpoint == "new-endpoint"
"""Unit tests for backend.v4.magentic_agents.models.agent_models module."""
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest


# Mock the common module completely
mock_common = MagicMock()
mock_config = MagicMock()
mock_common.config.app_config.config = mock_config
sys.modules['common'] = mock_common
sys.modules['common.config'] = mock_common.config
sys.modules['common.config.app_config'] = mock_common.config.app_config

# Import the module under test
from backend.v4.magentic_agents.models.agent_models import MCPConfig, SearchConfig


class TestMCPConfig:
    """Test cases for MCPConfig dataclass."""

    def test_init_with_default_values(self):
        """Test MCPConfig initialization with default values."""
        mcp_config = MCPConfig()
        
        assert mcp_config.url == ""
        assert mcp_config.name == "MCP"
        assert mcp_config.description == ""
        assert mcp_config.tenant_id == ""
        assert mcp_config.client_id == ""

    def test_init_with_custom_values(self):
        """Test MCPConfig initialization with custom values."""
        mcp_config = MCPConfig(
            url="https://custom-mcp.example.com",
            name="CustomMCP",
            description="Custom MCP Server",
            tenant_id="custom-tenant-123",
            client_id="custom-client-456"
        )
        
        assert mcp_config.url == "https://custom-mcp.example.com"
        assert mcp_config.name == "CustomMCP"
        assert mcp_config.description == "Custom MCP Server"
        assert mcp_config.tenant_id == "custom-tenant-123"
        assert mcp_config.client_id == "custom-client-456"

    def test_init_with_partial_values(self):
        """Test MCPConfig initialization with partial custom values."""
        mcp_config = MCPConfig(
            url="https://partial-mcp.example.com",
            description="Partial MCP Server"
        )
        
        assert mcp_config.url == "https://partial-mcp.example.com"
        assert mcp_config.name == "MCP"  # Default value
        assert mcp_config.description == "Partial MCP Server"
        assert mcp_config.tenant_id == ""  # Default value
        assert mcp_config.client_id == ""  # Default value

    def test_init_with_empty_strings(self):
        """Test MCPConfig initialization with explicit empty strings."""
        mcp_config = MCPConfig(
            url="",
            name="",
            description="",
            tenant_id="",
            client_id=""
        )
        
        assert mcp_config.url == ""
        assert mcp_config.name == ""
        assert mcp_config.description == ""
        assert mcp_config.tenant_id == ""
        assert mcp_config.client_id == ""

    def test_init_with_none_values(self):
        """Test MCPConfig initialization with None values (should use defaults)."""
        # Note: Since dataclass fields have defaults, None values would be accepted
        # but the dataclass will use the provided values
        mcp_config = MCPConfig(
            url=None,
            name=None,
            description=None,
            tenant_id=None,
            client_id=None
        )
        
        assert mcp_config.url is None
        assert mcp_config.name is None
        assert mcp_config.description is None
        assert mcp_config.tenant_id is None
        assert mcp_config.client_id is None

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_success(self, mock_config_patch):
        """Test MCPConfig.from_env with all required environment variables."""
        # Set up mock config values
        mock_config_patch.MCP_SERVER_ENDPOINT = "https://env-mcp.example.com"
        mock_config_patch.MCP_SERVER_NAME = "EnvMCP"
        mock_config_patch.MCP_SERVER_DESCRIPTION = "Environment MCP Server"
        mock_config_patch.AZURE_TENANT_ID = "env-tenant-789"
        mock_config_patch.AZURE_CLIENT_ID = "env-client-012"
        
        mcp_config = MCPConfig.from_env()
        
        assert mcp_config.url == "https://env-mcp.example.com"
        assert mcp_config.name == "EnvMCP"
        assert mcp_config.description == "Environment MCP Server"
        assert mcp_config.tenant_id == "env-tenant-789"
        assert mcp_config.client_id == "env-client-012"

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_url(self, mock_config_patch):
        """Test MCPConfig.from_env with missing MCP_SERVER_ENDPOINT."""
        mock_config_patch.MCP_SERVER_ENDPOINT = None
        mock_config_patch.MCP_SERVER_NAME = "EnvMCP"
        mock_config_patch.MCP_SERVER_DESCRIPTION = "Environment MCP Server"
        mock_config_patch.AZURE_TENANT_ID = "env-tenant-789"
        mock_config_patch.AZURE_CLIENT_ID = "env-client-012"
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_name(self, mock_config_patch):
        """Test MCPConfig.from_env with missing MCP_SERVER_NAME."""
        mock_config_patch.MCP_SERVER_ENDPOINT = "https://env-mcp.example.com"
        mock_config_patch.MCP_SERVER_NAME = ""
        mock_config_patch.MCP_SERVER_DESCRIPTION = "Environment MCP Server"
        mock_config_patch.AZURE_TENANT_ID = "env-tenant-789"
        mock_config_patch.AZURE_CLIENT_ID = "env-client-012"
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_description(self, mock_config_patch):
        """Test MCPConfig.from_env with missing MCP_SERVER_DESCRIPTION."""
        mock_config_patch.MCP_SERVER_ENDPOINT = "https://env-mcp.example.com"
        mock_config_patch.MCP_SERVER_NAME = "EnvMCP"
        mock_config_patch.MCP_SERVER_DESCRIPTION = None
        mock_config_patch.AZURE_TENANT_ID = "env-tenant-789"
        mock_config_patch.AZURE_CLIENT_ID = "env-client-012"
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_tenant_id(self, mock_config_patch):
        """Test MCPConfig.from_env with missing AZURE_TENANT_ID."""
        mock_config_patch.MCP_SERVER_ENDPOINT = "https://env-mcp.example.com"
        mock_config_patch.MCP_SERVER_NAME = "EnvMCP"
        mock_config_patch.MCP_SERVER_DESCRIPTION = "Environment MCP Server"
        mock_config_patch.AZURE_TENANT_ID = ""
        mock_config_patch.AZURE_CLIENT_ID = "env-client-012"
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_client_id(self, mock_config_patch):
        """Test MCPConfig.from_env with missing AZURE_CLIENT_ID."""
        mock_config_patch.MCP_SERVER_ENDPOINT = "https://env-mcp.example.com"
        mock_config_patch.MCP_SERVER_NAME = "EnvMCP"
        mock_config_patch.MCP_SERVER_DESCRIPTION = "Environment MCP Server"
        mock_config_patch.AZURE_TENANT_ID = "env-tenant-789"
        mock_config_patch.AZURE_CLIENT_ID = None
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_all_missing(self, mock_config_patch):
        """Test MCPConfig.from_env with all environment variables missing."""
        mock_config_patch.MCP_SERVER_ENDPOINT = None
        mock_config_patch.MCP_SERVER_NAME = None
        mock_config_patch.MCP_SERVER_DESCRIPTION = None
        mock_config_patch.AZURE_TENANT_ID = None
        mock_config_patch.AZURE_CLIENT_ID = None
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_empty_strings(self, mock_config_patch):
        """Test MCPConfig.from_env with empty string environment variables."""
        mock_config_patch.MCP_SERVER_ENDPOINT = ""
        mock_config_patch.MCP_SERVER_NAME = ""
        mock_config_patch.MCP_SERVER_DESCRIPTION = ""
        mock_config_patch.AZURE_TENANT_ID = ""
        mock_config_patch.AZURE_CLIENT_ID = ""
        
        with pytest.raises(ValueError) as exc_info:
            MCPConfig.from_env()
        
        assert "MCPConfig Missing required environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_with_special_characters(self, mock_config_patch):
        """Test MCPConfig.from_env with special characters in values."""
        mock_config_patch.MCP_SERVER_ENDPOINT = "https://mcp-üñíçødé.example.com/path?query=value&param=123"
        mock_config_patch.MCP_SERVER_NAME = "MCP Server (üñíçødé) #1"
        mock_config_patch.MCP_SERVER_DESCRIPTION = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        mock_config_patch.AZURE_TENANT_ID = "tenant-with-dashes-and_underscores_123"
        mock_config_patch.AZURE_CLIENT_ID = "client.with.dots.and-dashes-456"
        
        mcp_config = MCPConfig.from_env()
        
        assert mcp_config.url == "https://mcp-üñíçødé.example.com/path?query=value&param=123"
        assert mcp_config.name == "MCP Server (üñíçødé) #1"
        assert mcp_config.description == "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        assert mcp_config.tenant_id == "tenant-with-dashes-and_underscores_123"
        assert mcp_config.client_id == "client.with.dots.and-dashes-456"

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_with_long_values(self, mock_config_patch):
        """Test MCPConfig.from_env with very long environment variable values."""
        long_url = "https://" + "a" * 1000 + ".example.com"
        long_name = "MCP" + "N" * 1000
        long_description = "Description " + "D" * 2000
        long_tenant_id = "tenant-" + "t" * 500
        long_client_id = "client-" + "c" * 500
        
        mock_config_patch.MCP_SERVER_ENDPOINT = long_url
        mock_config_patch.MCP_SERVER_NAME = long_name
        mock_config_patch.MCP_SERVER_DESCRIPTION = long_description
        mock_config_patch.AZURE_TENANT_ID = long_tenant_id
        mock_config_patch.AZURE_CLIENT_ID = long_client_id
        
        mcp_config = MCPConfig.from_env()
        
        assert mcp_config.url == long_url
        assert mcp_config.name == long_name
        assert mcp_config.description == long_description
        assert mcp_config.tenant_id == long_tenant_id
        assert mcp_config.client_id == long_client_id

    def test_dataclass_attributes(self):
        """Test that MCPConfig is properly configured as a dataclass."""
        mcp_config = MCPConfig()
        
        # Test that it has the expected dataclass attributes
        assert hasattr(mcp_config, '__dataclass_fields__')
        
        # Test field names
        expected_fields = {'url', 'name', 'description', 'tenant_id', 'client_id'}
        actual_fields = set(mcp_config.__dataclass_fields__.keys())
        assert expected_fields == actual_fields

    def test_equality_and_representation(self):
        """Test equality and string representation of MCPConfig instances."""
        config1 = MCPConfig(
            url="https://test.com",
            name="Test",
            description="Test Config",
            tenant_id="tenant1",
            client_id="client1"
        )
        
        config2 = MCPConfig(
            url="https://test.com",
            name="Test",
            description="Test Config",
            tenant_id="tenant1",
            client_id="client1"
        )
        
        config3 = MCPConfig(
            url="https://different.com",
            name="Test",
            description="Test Config",
            tenant_id="tenant1",
            client_id="client1"
        )
        
        # Test equality
        assert config1 == config2
        assert config1 != config3
        
        # Test representation
        repr_str = repr(config1)
        assert "MCPConfig" in repr_str
        assert "https://test.com" in repr_str


class TestSearchConfig:
    """Test cases for SearchConfig dataclass."""

    def test_init_with_default_values(self):
        """Test SearchConfig initialization with default values."""
        search_config = SearchConfig()
        
        assert search_config.connection_name is None
        assert search_config.endpoint is None
        assert search_config.index_name is None

    def test_init_with_custom_values(self):
        """Test SearchConfig initialization with custom values."""
        search_config = SearchConfig(
            connection_name="CustomConnection",
            endpoint="https://custom-search.example.com",
            index_name="custom-index"
        )
        
        assert search_config.connection_name == "CustomConnection"
        assert search_config.endpoint == "https://custom-search.example.com"
        assert search_config.index_name == "custom-index"

    def test_init_with_partial_values(self):
        """Test SearchConfig initialization with partial custom values."""
        search_config = SearchConfig(
            endpoint="https://partial-search.example.com"
        )
        
        assert search_config.connection_name is None
        assert search_config.endpoint == "https://partial-search.example.com"
        assert search_config.index_name is None

    def test_init_with_explicit_none(self):
        """Test SearchConfig initialization with explicit None values."""
        search_config = SearchConfig(
            connection_name=None,
            endpoint=None,
            index_name=None
        )
        
        assert search_config.connection_name is None
        assert search_config.endpoint is None
        assert search_config.index_name is None

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_success(self, mock_config_patch):
        """Test SearchConfig.from_env with all required environment variables."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = "EnvConnection"
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = "https://env-search.example.com"
        
        search_config = SearchConfig.from_env(index_name="env-index")
        
        assert search_config.connection_name == "EnvConnection"
        assert search_config.endpoint == "https://env-search.example.com"
        assert search_config.index_name == "env-index"

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_connection_name(self, mock_config_patch):
        """Test SearchConfig.from_env with missing AZURE_AI_SEARCH_CONNECTION_NAME."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = None
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = "https://env-search.example.com"
        
        with pytest.raises(ValueError) as exc_info:
            SearchConfig.from_env(index_name="test-index")
        
        assert "SearchConfig Missing required Azure Search environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_endpoint(self, mock_config_patch):
        """Test SearchConfig.from_env with missing AZURE_AI_SEARCH_ENDPOINT."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = "EnvConnection"
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = ""
        
        with pytest.raises(ValueError) as exc_info:
            SearchConfig.from_env(index_name="test-index")
        
        assert "SearchConfig Missing required Azure Search environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_missing_index_name(self, mock_config_patch):
        """Test SearchConfig.from_env with missing index_name parameter."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = "EnvConnection"
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = "https://env-search.example.com"
        
        with pytest.raises(ValueError) as exc_info:
            SearchConfig.from_env(index_name=None)
        
        assert "SearchConfig Missing required Azure Search environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_empty_index_name(self, mock_config_patch):
        """Test SearchConfig.from_env with empty index_name parameter."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = "EnvConnection"
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = "https://env-search.example.com"
        
        with pytest.raises(ValueError) as exc_info:
            SearchConfig.from_env(index_name="")
        
        assert "SearchConfig Missing required Azure Search environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_all_missing(self, mock_config_patch):
        """Test SearchConfig.from_env with all environment variables missing."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = None
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = None
        
        with pytest.raises(ValueError) as exc_info:
            SearchConfig.from_env(index_name=None)
        
        assert "SearchConfig Missing required Azure Search environment variables" in str(exc_info.value)

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_with_special_characters(self, mock_config_patch):
        """Test SearchConfig.from_env with special characters in values."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = "Connection (üñíçødé) #1"
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = "https://search-üñíçødé.example.com/path?query=value"
        
        search_config = SearchConfig.from_env(index_name="index-üñíçødé-123")
        
        assert search_config.connection_name == "Connection (üñíçødé) #1"
        assert search_config.endpoint == "https://search-üñíçødé.example.com/path?query=value"
        assert search_config.index_name == "index-üñíçødé-123"

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_with_long_values(self, mock_config_patch):
        """Test SearchConfig.from_env with very long values."""
        long_connection_name = "Connection" + "C" * 1000
        long_endpoint = "https://" + "e" * 1000 + ".example.com"
        long_index_name = "index" + "i" * 1000
        
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = long_connection_name
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = long_endpoint
        
        search_config = SearchConfig.from_env(index_name=long_index_name)
        
        assert search_config.connection_name == long_connection_name
        assert search_config.endpoint == long_endpoint
        assert search_config.index_name == long_index_name

    def test_dataclass_attributes(self):
        """Test that SearchConfig is properly configured as a dataclass."""
        search_config = SearchConfig()
        
        # Test that it has the expected dataclass attributes
        assert hasattr(search_config, '__dataclass_fields__')
        
        # Test field names
        expected_fields = {'connection_name', 'endpoint', 'index_name'}
        actual_fields = set(search_config.__dataclass_fields__.keys())
        assert expected_fields == actual_fields

    def test_equality_and_representation(self):
        """Test equality and string representation of SearchConfig instances."""
        config1 = SearchConfig(
            connection_name="TestConnection",
            endpoint="https://test.com",
            index_name="test-index"
        )
        
        config2 = SearchConfig(
            connection_name="TestConnection",
            endpoint="https://test.com",
            index_name="test-index"
        )
        
        config3 = SearchConfig(
            connection_name="DifferentConnection",
            endpoint="https://test.com",
            index_name="test-index"
        )
        
        # Test equality
        assert config1 == config2
        assert config1 != config3
        
        # Test representation
        repr_str = repr(config1)
        assert "SearchConfig" in repr_str
        assert "TestConnection" in repr_str

    @patch('backend.v4.magentic_agents.models.agent_models.config')
    def test_from_env_index_name_override(self, mock_config_patch):
        """Test that SearchConfig.from_env properly uses the provided index_name."""
        mock_config_patch.AZURE_AI_SEARCH_CONNECTION_NAME = "EnvConnection"
        mock_config_patch.AZURE_AI_SEARCH_ENDPOINT = "https://env-search.example.com"
        
        # Test with different index names
        search_config1 = SearchConfig.from_env(index_name="custom-index-1")
        search_config2 = SearchConfig.from_env(index_name="custom-index-2")
        
        assert search_config1.index_name == "custom-index-1"
        assert search_config2.index_name == "custom-index-2"
        
        # Both should have the same connection_name and endpoint from env
        assert search_config1.connection_name == search_config2.connection_name
        assert search_config1.endpoint == search_config2.endpoint

    def test_none_type_annotation(self):
        """Test that SearchConfig properly handles None type annotations."""
        # Test that fields can accept None values
        search_config = SearchConfig(
            connection_name=None,
            endpoint=None, 
            index_name=None
        )
        
        assert search_config.connection_name is None
        assert search_config.endpoint is None
        assert search_config.index_name is None
        
        # Test that we can also set string values
        search_config.connection_name = "test"
        search_config.endpoint = "https://test.com"
        search_config.index_name = "test-index"
        
        assert search_config.connection_name == "test"
        assert search_config.endpoint == "https://test.com"
        assert search_config.index_name == "test-index"
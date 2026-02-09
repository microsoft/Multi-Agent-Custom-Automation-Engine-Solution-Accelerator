"""
Comprehensive unit tests for MCPService.

This module contains extensive test coverage for:
- MCPService class initialization and configuration
- Factory method for creating services from app config
- Health check operations
- Tool invocation operations
- Error handling and edge cases
"""

import pytest
import os
import sys
import asyncio
import importlib.util
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, Optional
from aiohttp import ClientTimeout, ClientError

# Add the src directory to sys.path for proper import
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
if src_path not in sys.path:
    sys.path.insert(0, os.path.abspath(src_path))

# Mock Azure modules before importing the MCPService
azure_ai_module = MagicMock()
azure_ai_projects_module = MagicMock()
azure_ai_projects_aio_module = MagicMock()

# Create mock AIProjectClient
mock_ai_project_client = MagicMock()
azure_ai_projects_aio_module.AIProjectClient = mock_ai_project_client

# Set up the module hierarchy
azure_ai_module.projects = azure_ai_projects_module
azure_ai_projects_module.aio = azure_ai_projects_aio_module

# Inject the mocked modules
sys.modules['azure'] = MagicMock()
sys.modules['azure.ai'] = azure_ai_module
sys.modules['azure.ai.projects'] = azure_ai_projects_module
sys.modules['azure.ai.projects.aio'] = azure_ai_projects_aio_module

# Mock other problematic modules and imports
sys.modules['common.models.messages_af'] = MagicMock()
sys.modules['v4'] = MagicMock()
sys.modules['v4.common'] = MagicMock()
sys.modules['v4.common.services'] = MagicMock()
sys.modules['v4.common.services.team_service'] = MagicMock()

# Mock the services module to avoid circular import
mock_services_module = MagicMock()
mock_services_module.MCPService = MagicMock()
mock_services_module.BaseAPIService = MagicMock()
mock_services_module.AgentsService = MagicMock()
mock_services_module.FoundryService = MagicMock()
sys.modules['backend.v4.common.services'] = mock_services_module

# Mock the config module
mock_config_module = MagicMock()
mock_config = MagicMock()

# Mock config attributes for MCPService tests
mock_config.MCP_SERVER_ENDPOINT = 'https://test.mcp.endpoint.com'
mock_config.MCP_SERVER_ENDPOINT_WITH_AUTH = 'https://auth.mcp.endpoint.com'
mock_config.MISSING_MCP_ENDPOINT = None

mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

# First, load BaseAPIService separately to avoid circular imports
base_api_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'base_api_service.py')
base_api_service_path = os.path.abspath(base_api_service_path)
base_spec = importlib.util.spec_from_file_location("base_api_service_module", base_api_service_path)
base_api_service_module = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base_api_service_module)

# Add BaseAPIService to the services mock module
mock_services_module.BaseAPIService = base_api_service_module.BaseAPIService

# Now import the real MCPService using direct file import but register for coverage
import importlib.util
# Now import the real MCPService using direct file import with proper mocking
import importlib.util

# First, load BaseAPIService to make it available for MCPService
base_api_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'base_api_service.py')
base_api_service_path = os.path.abspath(base_api_service_path)

# Mock the relative import for BaseAPIService during MCPService loading
with patch.dict('sys.modules', {
    'backend.v4.common.services.base_api_service': base_api_service_module,
}):
    mcp_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'mcp_service.py')
    mcp_service_path = os.path.abspath(mcp_service_path)
    spec = importlib.util.spec_from_file_location("backend.v4.common.services.mcp_service", mcp_service_path)
    mcp_service_module = importlib.util.module_from_spec(spec)
    
    # Set the proper module name for coverage tracking (matching --cov=backend pattern)
    mcp_service_module.__name__ = "backend.v4.common.services.mcp_service"
    mcp_service_module.__file__ = mcp_service_path
    
    # Add to sys.modules BEFORE execution for coverage tracking (both variations)
    sys.modules['backend.v4.common.services.mcp_service'] = mcp_service_module
    sys.modules['src.backend.v4.common.services.mcp_service'] = mcp_service_module
    
    spec.loader.exec_module(mcp_service_module)

MCPService = mcp_service_module.MCPService


class TestMCPService:
    """Test cases for MCPService class."""

    def test_init_with_required_parameters_only(self):
        """Test MCPService initialization with only required parameters."""
        service = MCPService("https://mcp.example.com")
        
        assert service.base_url == "https://mcp.example.com"
        assert service.default_headers == {"Content-Type": "application/json"}

    def test_init_with_token_authentication(self):
        """Test MCPService initialization with token authentication."""
        token = "test-bearer-token"
        service = MCPService("https://mcp.example.com", token=token)
        
        assert service.base_url == "https://mcp.example.com"
        assert service.default_headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-bearer-token"
        }

    def test_init_with_no_token(self):
        """Test MCPService initialization without token."""
        service = MCPService("https://mcp.example.com", token=None)
        
        assert service.base_url == "https://mcp.example.com"
        assert service.default_headers == {"Content-Type": "application/json"}

    def test_init_with_empty_token(self):
        """Test MCPService initialization with empty token."""
        service = MCPService("https://mcp.example.com", token="")
        
        assert service.base_url == "https://mcp.example.com"
        assert service.default_headers == {"Content-Type": "application/json"}

    def test_init_with_additional_kwargs(self):
        """Test MCPService initialization with additional keyword arguments."""
        timeout_seconds = 60
        service = MCPService(
            "https://mcp.example.com",
            token="test-token",
            timeout_seconds=timeout_seconds
        )
        
        assert service.base_url == "https://mcp.example.com"
        assert service.default_headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token"
        }
        assert service.timeout.total == timeout_seconds

    def test_init_with_trailing_slash_removal(self):
        """Test that trailing slashes are removed from base URL."""
        service = MCPService("https://mcp.example.com/", token="test-token")
        
        assert service.base_url == "https://mcp.example.com"

    def test_from_app_config_with_valid_endpoint(self):
        """Test from_app_config with a valid MCP endpoint."""
        with patch.object(mcp_service_module, 'config', mock_config):
            service = MCPService.from_app_config()
            
            assert service is not None
            assert service.base_url == 'https://test.mcp.endpoint.com'
            assert service.default_headers == {"Content-Type": "application/json"}

    def test_from_app_config_with_valid_endpoint_and_kwargs(self):
        """Test from_app_config with valid endpoint and additional kwargs."""
        with patch.object(mcp_service_module, 'config', mock_config):
            service = MCPService.from_app_config(timeout_seconds=45)
            
            assert service is not None
            assert service.base_url == 'https://test.mcp.endpoint.com'
            assert service.default_headers == {"Content-Type": "application/json"}
            assert service.timeout.total == 45

    def test_from_app_config_with_missing_endpoint_returns_none(self):
        """Test from_app_config returns None when endpoint is missing."""
        with patch.object(mcp_service_module, 'config', mock_config):
            mock_config.MCP_SERVER_ENDPOINT = None
            service = MCPService.from_app_config()
            
            assert service is None

    def test_from_app_config_with_empty_endpoint_returns_none(self):
        """Test from_app_config returns None when endpoint is empty string."""
        with patch.object(mcp_service_module, 'config', mock_config):
            mock_config.MCP_SERVER_ENDPOINT = ""
            service = MCPService.from_app_config()
            
            assert service is None

    @pytest.mark.asyncio
    async def test_health_success(self):
        """Test successful health check."""
        service = MCPService("https://mcp.example.com", token="test-token")
        
        expected_response = {"status": "healthy", "version": "1.0.0"}
        
        with patch.object(service, 'get_json', return_value=expected_response) as mock_get_json:
            result = await service.health()
            
            mock_get_json.assert_called_once_with("health")
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_health_with_detailed_status(self):
        """Test health check returning detailed status information."""
        service = MCPService("https://mcp.example.com")
        
        expected_response = {
            "status": "healthy",
            "version": "1.2.0",
            "uptime": "5 days",
            "services": {
                "database": "connected",
                "cache": "connected"
            }
        }
        
        with patch.object(service, 'get_json', return_value=expected_response) as mock_get_json:
            result = await service.health()
            
            mock_get_json.assert_called_once_with("health")
            assert result == expected_response
            assert result["services"]["database"] == "connected"

    @pytest.mark.asyncio
    async def test_health_failure(self):
        """Test health check when service is unhealthy."""
        service = MCPService("https://mcp.example.com")
        
        error_response = {"status": "unhealthy", "error": "Database connection failed"}
        
        with patch.object(service, 'get_json', return_value=error_response) as mock_get_json:
            result = await service.health()
            
            mock_get_json.assert_called_once_with("health")
            assert result == error_response
            assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_with_http_error(self):
        """Test health check when HTTP error occurs."""
        service = MCPService("https://mcp.example.com")
        
        with patch.object(service, 'get_json', side_effect=ClientError("Connection failed")):
            with pytest.raises(ClientError, match="Connection failed"):
                await service.health()

    @pytest.mark.asyncio
    async def test_invoke_tool_success(self):
        """Test successful tool invocation."""
        service = MCPService("https://mcp.example.com", token="test-token")
        
        tool_name = "test_tool"
        payload = {"param1": "value1", "param2": 42}
        expected_response = {"result": "success", "output": "Tool executed successfully"}
        
        with patch.object(service, 'post_json', return_value=expected_response) as mock_post_json:
            result = await service.invoke_tool(tool_name, payload)
            
            mock_post_json.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_invoke_tool_with_complex_payload(self):
        """Test tool invocation with complex nested payload."""
        service = MCPService("https://mcp.example.com")
        
        tool_name = "complex_tool"
        payload = {
            "config": {
                "settings": {"debug": True, "timeout": 30},
                "data": [1, 2, 3, {"nested": "value"}]
            },
            "metadata": {"version": "2.0", "user": "test_user"}
        }
        expected_response = {
            "result": "completed",
            "data": {"processed": True, "items": 3},
            "metadata": {"execution_time": 1.23}
        }
        
        with patch.object(service, 'post_json', return_value=expected_response) as mock_post_json:
            result = await service.invoke_tool(tool_name, payload)
            
            mock_post_json.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == expected_response
            assert result["data"]["processed"] is True

    @pytest.mark.asyncio
    async def test_invoke_tool_with_empty_payload(self):
        """Test tool invocation with empty payload."""
        service = MCPService("https://mcp.example.com")
        
        tool_name = "simple_tool"
        payload = {}
        expected_response = {"result": "no_op", "message": "No parameters provided"}
        
        with patch.object(service, 'post_json', return_value=expected_response) as mock_post_json:
            result = await service.invoke_tool(tool_name, payload)
            
            mock_post_json.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_invoke_tool_with_special_characters_in_name(self):
        """Test tool invocation with special characters in tool name."""
        service = MCPService("https://mcp.example.com")
        
        tool_name = "tool-with-dashes_and_underscores"
        payload = {"test": True}
        expected_response = {"result": "success"}
        
        with patch.object(service, 'post_json', return_value=expected_response) as mock_post_json:
            result = await service.invoke_tool(tool_name, payload)
            
            mock_post_json.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_invoke_tool_with_tool_error(self):
        """Test tool invocation when tool returns an error."""
        service = MCPService("https://mcp.example.com")
        
        tool_name = "failing_tool"
        payload = {"cause_error": True}
        error_response = {
            "error": "Tool execution failed",
            "code": "TOOL_ERROR",
            "details": "Invalid parameter: cause_error"
        }
        
        with patch.object(service, 'post_json', return_value=error_response) as mock_post_json:
            result = await service.invoke_tool(tool_name, payload)
            
            mock_post_json.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == error_response
            assert result["error"] == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_invoke_tool_with_http_error(self):
        """Test tool invocation when HTTP error occurs."""
        service = MCPService("https://mcp.example.com")
        
        tool_name = "test_tool"
        payload = {"param": "value"}
        
        with patch.object(service, 'post_json', side_effect=ClientError("Network error")):
            with pytest.raises(ClientError, match="Network error"):
                await service.invoke_tool(tool_name, payload)

    @pytest.mark.asyncio
    async def test_invoke_tool_with_timeout_error(self):
        """Test tool invocation when timeout occurs."""
        service = MCPService("https://mcp.example.com")
        
        tool_name = "slow_tool"
        payload = {"wait_time": 1000}
        
        with patch.object(service, 'post_json', side_effect=asyncio.TimeoutError("Request timed out")):
            with pytest.raises(asyncio.TimeoutError, match="Request timed out"):
                await service.invoke_tool(tool_name, payload)

    @pytest.mark.asyncio
    async def test_inheritance_from_base_api_service(self):
        """Test that MCPService properly inherits from BaseAPIService."""
        service = MCPService("https://mcp.example.com", token="test-token")
        
        # Test inherited properties
        assert hasattr(service, 'base_url')
        assert hasattr(service, 'default_headers')
        assert hasattr(service, 'timeout')
        
        # Test inherited methods
        assert hasattr(service, 'get_json')
        assert hasattr(service, 'post_json')
        assert hasattr(service, '_ensure_session')

    def test_service_configuration_integration(self):
        """Test service configuration with various scenarios."""
        # Test with different base URLs and tokens
        configs = [
            ("https://localhost:8080", "local-token"),
            ("https://prod.mcp.com", "prod-token"),
            ("http://dev.mcp.internal:3000", None),
        ]
        
        for base_url, token in configs:
            service = MCPService(base_url, token=token)
            assert service.base_url == base_url.rstrip('/')
            
            if token:
                assert service.default_headers["Authorization"] == f"Bearer {token}"
            else:
                assert "Authorization" not in service.default_headers

    @pytest.mark.asyncio
    async def test_multiple_tool_invocations(self):
        """Test multiple sequential tool invocations."""
        service = MCPService("https://mcp.example.com")
        
        tools_and_payloads = [
            ("tool1", {"param": "value1"}, {"result": "result1"}),
            ("tool2", {"param": "value2"}, {"result": "result2"}),
            ("tool3", {"param": "value3"}, {"result": "result3"}),
        ]
        
        with patch.object(service, 'post_json') as mock_post_json:
            for tool_name, payload, expected_result in tools_and_payloads:
                mock_post_json.return_value = expected_result
                result = await service.invoke_tool(tool_name, payload)
                assert result == expected_result
        
        # Verify all calls were made
        assert mock_post_json.call_count == 3
        for i, (tool_name, payload, _) in enumerate(tools_and_payloads):
            args, kwargs = mock_post_json.call_args_list[i]
            assert args[0] == f"tools/{tool_name}"
            assert kwargs["json"] == payload

    def test_from_app_config_error_handling(self):
        """Test from_app_config error handling scenarios."""
        # Test when config object itself is None
        with patch.object(mcp_service_module, 'config', None):
            with pytest.raises(AttributeError):
                MCPService.from_app_config()
        
        # Test when config has no MCP_SERVER_ENDPOINT attribute
        mock_config_no_attr = MagicMock()
        del mock_config_no_attr.MCP_SERVER_ENDPOINT
        with patch.object(mcp_service_module, 'config', mock_config_no_attr):
            with pytest.raises(AttributeError):
                MCPService.from_app_config()

    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Test MCPService as a context manager (inherited from BaseAPIService)."""
        service = MCPService("https://mcp.example.com", token="test-token")
        
        # Mock the session operations
        with patch.object(service, '_ensure_session') as mock_ensure_session, \
             patch.object(service, 'close') as mock_close:
            
            async with service:
                # Verify context manager entry
                assert service is not None
            
            # Verify cleanup on exit
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_scenario(self):
        """Test a complete integration scenario."""
        # Create service from config
        with patch.object(mcp_service_module, 'config', mock_config):
            # Ensure the mock config has the correct endpoint
            mock_config.MCP_SERVER_ENDPOINT = 'https://test.mcp.endpoint.com'
            service = MCPService.from_app_config(timeout_seconds=30)
        
        assert service is not None
        assert service.base_url == 'https://test.mcp.endpoint.com'
        
        # Mock responses for health and tool invocation
        health_response = {"status": "healthy", "version": "1.0"}
        tool_response = {"result": "success", "data": {"processed": True}}
        
        with patch.object(service, 'get_json', return_value=health_response) as mock_get, \
             patch.object(service, 'post_json', return_value=tool_response) as mock_post:
            
            # Check health
            health_result = await service.health()
            assert health_result == health_response
            
            # Invoke tool
            tool_result = await service.invoke_tool("process_data", {"input": "test"})
            assert tool_result == tool_response
            
            # Verify calls
            mock_get.assert_called_once_with("health")
            mock_post.assert_called_once_with("tools/process_data", json={"input": "test"})
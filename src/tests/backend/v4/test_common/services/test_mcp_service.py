"""
Unit tests for v4 MCPService with actual module import for coverage.

This module tests the MCPService by importing the actual module
with proper dependency mocking to enable coverage reporting.

Tests cover:
- Service initialization with base URL and optional token
- Authorization header configuration
- Factory method from_app_config
- Health endpoint
- Tool invocation
- Error handling
- Edge cases and boundary conditions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import aiohttp
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend path to sys.path for proper imports  
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the real service modules for coverage
from v4.common.services.mcp_service import MCPService


class TestMCPServiceInit:
    """Test cases for MCPService initialization."""

    def test_init_with_base_url_only(self):
        """Test MCPService initialization with only base_url."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com")
            assert service.base_url == "https://mcp.example.com"
            assert service.default_headers["Content-Type"] == "application/json"
            assert "Authorization" not in service.default_headers

    def test_init_with_token(self):
        """Test MCPService initialization with token."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com", token="test-token")
            assert service.base_url == "https://mcp.example.com"
            assert service.default_headers["Content-Type"] == "application/json"
            assert service.default_headers["Authorization"] == "Bearer test-token"

    def test_init_without_token(self):
        """Test MCPService initialization without token."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com", token=None)
            assert service.base_url == "https://mcp.example.com"
            assert "Authorization" not in service.default_headers

    def test_init_with_empty_token(self):
        """Test MCPService initialization with empty token."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com", token="")
            assert "Authorization" not in service.default_headers

    def test_init_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com/")
            assert service.base_url == "https://mcp.example.com"

    def test_init_with_path_in_url(self):
        """Test initialization with path in URL."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com/api/v1")
            assert service.base_url == "https://mcp.example.com/api/v1"

    def test_init_empty_base_url_raises_error(self):
        """Test that empty base_url raises ValueError."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            with pytest.raises(ValueError):
                MCPService("")

    def test_init_token_bearer_format(self):
        """Test that token is properly formatted as Bearer token."""
        with patch('v4.common.services.mcp_service.config') as mock_config:
            service = MCPService("https://mcp.example.com", token="mytoken")
            assert service.default_headers["Authorization"] == "Bearer mytoken"


class TestMCPServiceFromAppConfig:
    """Test cases for MCPService.from_app_config class method."""

    @patch('v4.common.services.mcp_service.config')
    def test_from_app_config_with_endpoint(self, mock_config):
        """Test from_app_config when MCP_SERVER_ENDPOINT is set."""
        mock_config.MCP_SERVER_ENDPOINT = "https://configured.mcp.example.com"
        
        service = MCPService.from_app_config()
        assert service.base_url == "https://configured.mcp.example.com"
        # Note: from_app_config sets token=None, so no Authorization header
        assert "Authorization" not in service.default_headers

    @patch('v4.common.services.mcp_service.config')
    def test_from_app_config_without_endpoint(self, mock_config):
        """Test from_app_config when MCP_SERVER_ENDPOINT is None."""
        mock_config.MCP_SERVER_ENDPOINT = None
        
        result = MCPService.from_app_config()
        assert result is None

    @patch('v4.common.services.mcp_service.config')
    def test_from_app_config_with_empty_endpoint(self, mock_config):
        """Test from_app_config when MCP_SERVER_ENDPOINT is empty string."""
        mock_config.MCP_SERVER_ENDPOINT = ""
        
        result = MCPService.from_app_config()
        assert result is None

    @patch('v4.common.services.mcp_service.config')
    def test_from_app_config_without_token(self, mock_config):
        """Test from_app_config when token is not configured."""
        mock_config.MCP_SERVER_ENDPOINT = "https://configured.mcp.example.com"
        mock_config.MCP_SERVER_TOKEN = None
        
        service = MCPService.from_app_config()
        assert service.base_url == "https://configured.mcp.example.com"
        assert "Authorization" not in service.default_headers


@pytest.mark.asyncio
class TestMCPServiceHealth:
    """Test cases for MCPService health methods."""

    async def test_health_success(self):
        """Test successful health check."""
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            with patch.object(service, 'get_json', return_value={"status": "healthy"}) as mock_get:
                result = await service.health()
                assert result == {"status": "healthy"}
                mock_get.assert_called_once_with("health")

    async def test_health_with_detailed_response(self):
        """Test health check with detailed response."""
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            detailed_response = {
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 3600
            }
            
            with patch.object(service, 'get_json', return_value=detailed_response) as mock_get:
                result = await service.health()
                assert result == detailed_response
                mock_get.assert_called_once_with("health")

    async def test_health_http_error(self):
        """Test health check with HTTP error response."""
        import aiohttp
        
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            with patch.object(service, 'get_json') as mock_get:
                mock_get.side_effect = aiohttp.ClientResponseError(
                    request_info=None, history=(), status=500
                )
                
                with pytest.raises(aiohttp.ClientResponseError):
                    await service.health()


@pytest.mark.asyncio
class TestMCPServiceInvokeTool:
    """Test cases for MCPService invoke_tool method."""

    async def test_invoke_tool_success(self):
        """Test successful tool invocation."""
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            payload = {"param": "value"}
            expected_response = {"result": "success"}
            
            with patch.object(service, 'post_json', return_value=expected_response) as mock_post:
                result = await service.invoke_tool("test_tool", payload)
                assert result == expected_response
                mock_post.assert_called_once_with("tools/test_tool", json=payload)

    async def test_invoke_tool_with_complex_payload(self):
        """Test tool invocation with complex payload."""
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            complex_payload = {
                "action": "execute",
                "params": {
                    "nested": {"value": 42}
                },
                "list_data": [1, 2, 3]
            }
            expected_response = {"result": "processed", "data": {"items": 3}}
            
            with patch.object(service, 'post_json', return_value=expected_response) as mock_post:
                result = await service.invoke_tool("complex_tool", complex_payload)
                assert result == expected_response
                mock_post.assert_called_once_with("tools/complex_tool", json=complex_payload)

    async def test_invoke_tool_http_error(self):
        """Test tool invocation with HTTP error."""
        import aiohttp
        
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            with patch.object(service, 'post_json') as mock_post:
                mock_post.side_effect = aiohttp.ClientResponseError(
                    request_info=None, history=(), status=400
                )
                
                with pytest.raises(aiohttp.ClientResponseError):
                    await service.invoke_tool("test_tool", {"param": "value"})

    async def test_invoke_tool_url_construction(self):
        """Test correct URL construction for tool invocation."""
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            with patch.object(service, 'post_json', return_value={}) as mock_post:
                await service.invoke_tool("my-custom-tool", {"data": "test"})
                mock_post.assert_called_once_with("tools/my-custom-tool", json={"data": "test"})

    async def test_invoke_tool_empty_payload(self):
        """Test tool invocation with empty payload."""
        with patch('v4.common.services.mcp_service.config'):
            service = MCPService("https://mcp.example.com")
            
            with patch.object(service, 'post_json', return_value={"status": "ok"}) as mock_post:
                result = await service.invoke_tool("simple_tool", {})
                assert result == {"status": "ok"}
                mock_post.assert_called_once_with("tools/simple_tool", json={})

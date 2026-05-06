# Copyright (c) Microsoft. All rights reserved.
"""Tests for services/mcp_service.py."""

import os
import sys

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from aiohttp import ClientError

# Add src/backend to sys.path
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Mock Azure modules
sys.modules.setdefault('azure', MagicMock())
sys.modules.setdefault('azure.ai', MagicMock())
sys.modules.setdefault('azure.ai.projects', MagicMock())
sys.modules.setdefault('azure.ai.projects.aio', MagicMock())

mock_config = MagicMock()
mock_config.MCP_SERVER_ENDPOINT = 'https://test.mcp.endpoint.com'

mock_config_module = MagicMock()
mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

from backend.services.mcp_service import MCPService
import backend.services.mcp_service as mcp_service_module


class TestMCPService:
    """Test cases for MCPService class."""

    def test_init_with_required_parameters_only(self):
        service = MCPService("https://mcp.example.com")
        assert service.base_url == "https://mcp.example.com"
        assert service.default_headers == {"Content-Type": "application/json"}

    def test_init_with_token_authentication(self):
        service = MCPService("https://mcp.example.com", token="test-bearer-token")
        assert service.default_headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-bearer-token"
        }

    def test_init_with_no_token(self):
        service = MCPService("https://mcp.example.com", token=None)
        assert service.default_headers == {"Content-Type": "application/json"}

    def test_init_with_empty_token(self):
        service = MCPService("https://mcp.example.com", token="")
        assert service.default_headers == {"Content-Type": "application/json"}

    def test_init_with_additional_kwargs(self):
        service = MCPService(
            "https://mcp.example.com",
            token="test-token",
            timeout_seconds=60
        )
        assert service.default_headers["Authorization"] == "Bearer test-token"
        assert service.timeout.total == 60

    def test_init_with_trailing_slash_removal(self):
        service = MCPService("https://mcp.example.com/", token="test-token")
        assert service.base_url == "https://mcp.example.com"

    def test_from_app_config_with_valid_endpoint(self):
        with patch.object(mcp_service_module, 'config', mock_config):
            mock_config.MCP_SERVER_ENDPOINT = 'https://test.mcp.endpoint.com'
            service = MCPService.from_app_config()
            assert service is not None
            assert service.base_url == 'https://test.mcp.endpoint.com'
            assert service.default_headers == {"Content-Type": "application/json"}

    def test_from_app_config_with_valid_endpoint_and_kwargs(self):
        with patch.object(mcp_service_module, 'config', mock_config):
            mock_config.MCP_SERVER_ENDPOINT = 'https://test.mcp.endpoint.com'
            service = MCPService.from_app_config(timeout_seconds=45)
            assert service is not None
            assert service.base_url == 'https://test.mcp.endpoint.com'
            assert service.timeout.total == 45

    def test_from_app_config_with_missing_endpoint_returns_none(self):
        with patch.object(mcp_service_module, 'config', mock_config):
            mock_config.MCP_SERVER_ENDPOINT = None
            service = MCPService.from_app_config()
            assert service is None

    def test_from_app_config_with_empty_endpoint_returns_none(self):
        with patch.object(mcp_service_module, 'config', mock_config):
            mock_config.MCP_SERVER_ENDPOINT = ""
            service = MCPService.from_app_config()
            assert service is None

    @pytest.mark.asyncio
    async def test_health_success(self):
        service = MCPService("https://mcp.example.com", token="test-token")
        expected = {"status": "healthy", "version": "1.0.0"}
        with patch.object(service, 'get_json', return_value=expected) as mock_get:
            result = await service.health()
            mock_get.assert_called_once_with("health")
            assert result == expected

    @pytest.mark.asyncio
    async def test_health_with_detailed_status(self):
        service = MCPService("https://mcp.example.com")
        expected = {
            "status": "healthy",
            "version": "1.2.0",
            "services": {"database": "connected"}
        }
        with patch.object(service, 'get_json', return_value=expected) as mock_get:
            result = await service.health()
            mock_get.assert_called_once_with("health")
            assert result["services"]["database"] == "connected"

    @pytest.mark.asyncio
    async def test_health_failure(self):
        service = MCPService("https://mcp.example.com")
        error_resp = {"status": "unhealthy", "error": "Database connection failed"}
        with patch.object(service, 'get_json', return_value=error_resp):
            result = await service.health()
            assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_with_http_error(self):
        service = MCPService("https://mcp.example.com")
        with patch.object(service, 'get_json', side_effect=ClientError("Connection failed")):
            with pytest.raises(ClientError, match="Connection failed"):
                await service.health()

    @pytest.mark.asyncio
    async def test_invoke_tool_success(self):
        service = MCPService("https://mcp.example.com", token="test-token")
        tool_name = "test_tool"
        payload = {"param1": "value1", "param2": 42}
        expected = {"result": "success", "output": "Tool executed successfully"}
        with patch.object(service, 'post_json', return_value=expected) as mock_post:
            result = await service.invoke_tool(tool_name, payload)
            mock_post.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == expected

    @pytest.mark.asyncio
    async def test_invoke_tool_with_complex_payload(self):
        service = MCPService("https://mcp.example.com")
        tool_name = "complex_tool"
        payload = {
            "config": {"settings": {"debug": True}},
            "metadata": {"version": "2.0"}
        }
        expected = {"result": "completed", "data": {"processed": True}}
        with patch.object(service, 'post_json', return_value=expected) as mock_post:
            result = await service.invoke_tool(tool_name, payload)
            mock_post.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result["data"]["processed"] is True

    @pytest.mark.asyncio
    async def test_invoke_tool_with_empty_payload(self):
        service = MCPService("https://mcp.example.com")
        payload = {}
        expected = {"result": "no_op"}
        with patch.object(service, 'post_json', return_value=expected) as mock_post:
            result = await service.invoke_tool("simple_tool", payload)
            mock_post.assert_called_once_with("tools/simple_tool", json=payload)
            assert result == expected

    @pytest.mark.asyncio
    async def test_invoke_tool_with_special_characters_in_name(self):
        service = MCPService("https://mcp.example.com")
        tool_name = "tool-with-dashes_and_underscores"
        payload = {"test": True}
        expected = {"result": "success"}
        with patch.object(service, 'post_json', return_value=expected) as mock_post:
            result = await service.invoke_tool(tool_name, payload)
            mock_post.assert_called_once_with(f"tools/{tool_name}", json=payload)
            assert result == expected

    @pytest.mark.asyncio
    async def test_invoke_tool_with_tool_error(self):
        service = MCPService("https://mcp.example.com")
        error_response = {"error": "Tool execution failed", "code": "TOOL_ERROR"}
        with patch.object(service, 'post_json', return_value=error_response):
            result = await service.invoke_tool("failing_tool", {"cause_error": True})
            assert result["error"] == "Tool execution failed"

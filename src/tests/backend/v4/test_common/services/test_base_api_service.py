"""
Unit tests for v4 BaseAPIService patterns and functionality.

This module tests the BaseAPIService by importing the actual module
with proper dependency mocking to enable coverage reporting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import aiohttp
from typing import Any, Dict
import sys
from pathlib import Path

# Add backend path to sys.path for proper imports  
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the real service module now that dependencies are mocked
from v4.common.services.base_api_service import BaseAPIService

# Mock config class for testing
class MockConfig:
    """Mock configuration class for testing"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestBaseAPIServiceInit:
    """Test cases for BaseAPIService initialization."""

    def test_init_with_base_url(self):
        """Test successful initialization with base URL."""
        service = BaseAPIService("https://api.example.com")
        
        assert service.base_url == "https://api.example.com"
        assert service.default_headers == {}
        assert service._session is None
        assert service._session_external is False

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        service = BaseAPIService("https://api.example.com/")
        
        assert service.base_url == "https://api.example.com"

    def test_init_with_custom_headers(self):
        """Test initialization with custom default headers."""
        headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        service = BaseAPIService("https://api.example.com", default_headers=headers)
        
        assert service.base_url == "https://api.example.com"
        assert service.default_headers == headers

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        service = BaseAPIService("https://api.example.com", timeout_seconds=60)
        
        assert service.base_url == "https://api.example.com"
        assert service.timeout.total == 60

    def test_init_with_external_session(self):
        """Test initialization with external session."""
        session = AsyncMock()
        service = BaseAPIService("https://api.example.com", session=session)
        
        assert service.base_url == "https://api.example.com"
        assert service._session is session
        assert service._session_external is True

    def test_init_empty_base_url_raises_error(self):
        """Test that empty base URL raises ValueError."""
        with pytest.raises(ValueError, match="base_url is required"):
            BaseAPIService("")


class TestFromConfig:
    """Test cases for BaseAPIService.from_config method."""

    @patch('v4.common.services.base_api_service.config')
    def test_from_config_success(self, mock_config):
        """Test successful service creation from config."""
        mock_config.endpoint_url = "https://api.example.com"
        
        service = BaseAPIService.from_config('endpoint_url')
        
        assert isinstance(service, BaseAPIService)
        assert service.base_url == "https://api.example.com"

    @patch('v4.common.services.base_api_service.config')
    def test_from_config_with_default(self, mock_config):
        """Test service creation with default value when config attribute is None."""
        mock_config.missing_url = None
        default_url = "https://default-api.example.com"
        
        service = BaseAPIService.from_config(
            'missing_url', 
            default=default_url
        )
        
        assert isinstance(service, BaseAPIService)
        assert service.base_url == default_url

    @patch('v4.common.services.base_api_service.config')
    def test_from_config_attribute_is_none(self, mock_config):
        """Test service creation when config attribute exists but is None."""
        mock_config.endpoint_url = None
        default_url = "https://default-api.example.com"
        
        service = BaseAPIService.from_config(
            'endpoint_url', 
            default=default_url
        )
        
        assert isinstance(service, BaseAPIService)
        assert service.base_url == default_url

    @patch('v4.common.services.base_api_service.config')
    def test_from_config_attribute_is_empty_string(self, mock_config):
        """Test service creation when config attribute is empty string."""
        mock_config.endpoint_url = ""
        default_url = "https://default-api.example.com"
        
        service = BaseAPIService.from_config(
            'endpoint_url', 
            default=default_url
        )
        
        assert isinstance(service, BaseAPIService)
        assert service.base_url == default_url

    @patch('v4.common.services.base_api_service.config')
    def test_from_config_no_attribute_no_default_raises_error(self, mock_config):
        """Test that missing attribute with no default raises ValueError."""
        # Simulate missing attribute by having getattr return None
        mock_config.missing_url = None
        with pytest.raises(ValueError, match="not configured"):
            BaseAPIService.from_config('missing_url')

    @patch('v4.common.services.base_api_service.config')
    def test_from_config_with_kwargs(self, mock_config):
        """Test service creation with additional kwargs."""
        mock_config.endpoint_url = "https://api.example.com"
        headers = {"Authorization": "Bearer token"}
        
        service = BaseAPIService.from_config(
            'endpoint_url', 
            default_headers=headers,
            timeout_seconds=60
        )
        
        assert isinstance(service, BaseAPIService)
        assert service.base_url == "https://api.example.com"
        assert service.default_headers == headers
        assert service.timeout.total == 60


class TestSessionManagement:
    """Test cases for session management functionality."""

    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self):
        """Test that _ensure_session creates a new session when none exists."""
        service = BaseAPIService("https://api.example.com")
        
        assert service._session is None
        
        session = await service._ensure_session()
        
        assert session is not None
        assert service._session is session
        assert isinstance(session, aiohttp.ClientSession)
        
        # Clean up
        await session.close()

    @pytest.mark.asyncio
    async def test_ensure_session_reuses_existing(self):
        """Test that _ensure_session reuses existing session."""
        service = BaseAPIService("https://api.example.com")
        existing_session = await service._ensure_session()
        
        session = await service._ensure_session()
        
        assert session is existing_session
        
        # Clean up
        await session.close()

    @pytest.mark.asyncio
    async def test_ensure_session_recreates_closed_session(self):
        """Test that _ensure_session recreates closed session."""
        service = BaseAPIService("https://api.example.com")
        
        old_session = await service._ensure_session()
        await old_session.close()  # Close the session
        
        session = await service._ensure_session()
        
        assert session is not old_session
        assert service._session is session
        assert not session.closed
        
        # Clean up
        await session.close()

    @pytest.mark.asyncio
    async def test_internal_session_closed(self):
        """Test that internal session gets closed properly."""
        service = BaseAPIService("https://api.example.com")
        
        session = await service._ensure_session()
        await service.close()
        
        assert session.closed is True

    @pytest.mark.asyncio
    async def test_close_when_no_session(self):
        """Test close() when no session exists."""
        service = BaseAPIService("https://api.example.com")
        
        # Should not raise exception
        await service.close()
        assert service._session is None

    @pytest.mark.asyncio 
    async def test_close_already_closed_session(self):
        """Test close() when session is already closed."""
        service = BaseAPIService("https://api.example.com")
        
        session = await service._ensure_session()
        await session.close()
        
        # Should not raise exception
        await service.close()


class TestHttpRequests:
    """Test cases for HTTP request methods with proper mocking."""

    @pytest.mark.asyncio
    async def test_get_json_success(self):
        """Test successful JSON GET request."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response
            
            result = await service.get_json("users")
            
            assert result == {"result": "success"}
            mock_request.assert_called_once_with("GET", "users", headers=None, params=None)
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_json_success(self):
        """Test successful JSON POST request."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response
            
            data = {"name": "John"}
            result = await service.post_json("users", json=data)
            
            assert result == {"result": "success"}
            mock_request.assert_called_once_with("POST", "users", headers=None, params=None, json=data)
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_json_with_params(self):
        """Test GET request with parameters."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response
            
            params = {"page": 1, "limit": 10}
            result = await service.get_json("users", params=params)
            
            assert result == {"result": "success"}
            mock_request.assert_called_once_with("GET", "users", headers=None, params=params)

    @pytest.mark.asyncio
    async def test_post_json_with_params_and_body(self):
        """Test POST request with both params and JSON body."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response
            
            params = {"version": "v1"}
            data = {"name": "John"}
            result = await service.post_json("users", json=data, params=params)
            
            assert result == {"result": "success"}
            mock_request.assert_called_once_with("POST", "users", headers=None, params=params, json=data)

    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """Test request with custom headers."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response
            
            headers = {"Content-Type": "application/json"}
            result = await service.get_json("users", headers=headers)
            
            assert result == {"result": "success"}
            mock_request.assert_called_once_with("GET", "users", headers=headers, params=None)

    @pytest.mark.asyncio
    async def test_request_error_handling(self):
        """Test that HTTP errors are properly raised."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            # Create a properly configured mock response that raises on raise_for_status
            error = aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=404
            )
            mock_response = Mock()  # Use Mock, not AsyncMock for non-async methods
            mock_response.raise_for_status.side_effect = error
            mock_request.return_value = mock_response
            
            with pytest.raises(aiohttp.ClientResponseError):
                await service.get_json("not-found")


class TestRequestInternals:
    """Test cases for internal request method functionality."""

    @pytest.mark.asyncio
    async def test_url_construction(self):
        """Test URL construction from base URL and path."""
        service = BaseAPIService("https://api.example.com")
        
        assert service._url("") == "https://api.example.com"
        assert service._url("users") == "https://api.example.com/users"
        assert service._url("/users") == "https://api.example.com/users"
        assert service._url("users/123") == "https://api.example.com/users/123"

    @pytest.mark.asyncio
    async def test_header_merging(self):
        """Test that headers are properly merged."""
        default_headers = {"Authorization": "Bearer token"}
        service = BaseAPIService("https://api.example.com", default_headers=default_headers)
        
        with patch.object(service, '_ensure_session') as mock_ensure_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_session.request.return_value = mock_response
            mock_ensure_session.return_value = mock_session
            
            request_headers = {"Content-Type": "application/json"}
            await service._request("GET", "users", headers=request_headers)
            
            # Check that session.request was called with merged headers
            call_args = mock_session.request.call_args
            merged_headers = call_args[1]["headers"]
            assert merged_headers["Authorization"] == "Bearer token"
            assert merged_headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_header_override(self):
        """Test that request headers override default headers."""
        default_headers = {"Content-Type": "application/xml"}
        service = BaseAPIService("https://api.example.com", default_headers=default_headers)
        
        with patch.object(service, '_ensure_session') as mock_ensure_session:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_session.request.return_value = mock_response
            mock_ensure_session.return_value = mock_session
            
            request_headers = {"Content-Type": "application/json"}
            await service._request("POST", "users", headers=request_headers)
            
            # Check that request headers override default headers
            call_args = mock_session.request.call_args
            merged_headers = call_args[1]["headers"]
            assert merged_headers["Content-Type"] == "application/json"


class TestEdgeCases:
    """Test cases for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_json_response(self):
        """Test handling of empty JSON response."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {}
            mock_request.return_value = mock_response
            
            result = await service.get_json("empty")
            assert result == {}

    @pytest.mark.asyncio
    async def test_json_array_response(self):
        """Test handling of JSON array response."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = [{'id': 1}, {'id': 2}]
            mock_request.return_value = mock_response
            
            result = await service.get_json("array")
            assert result == [{'id': 1}, {'id': 2}]


class TestIntegrationScenarios:
    """Test cases for integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_request_lifecycle(self):
        """Test complete request lifecycle with all features."""
        headers = {"Authorization": "Bearer token"}
        service = BaseAPIService(
            "https://api.example.com/",
            default_headers=headers,
            timeout_seconds=60
        )
        
        with patch.object(service, '_request') as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response
            
            params = {"include": "profile"}
            data = {"name": "John Doe", "email": "john@example.com"}
            
            result = await service.post_json("users", json=data, params=params)
            
            assert result == {"result": "success"}
            mock_request.assert_called_once_with("POST", "users", headers=None, params=params, json=data)

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test service as async context manager."""
        service = BaseAPIService("https://api.example.com")
        
        async with service:
            # Session should be created
            assert service._session is not None
        
        # Session should be closed after exiting context
        assert service._session.closed
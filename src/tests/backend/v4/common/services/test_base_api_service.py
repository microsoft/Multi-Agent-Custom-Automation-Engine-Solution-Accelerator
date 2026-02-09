"""
Comprehensive unit tests for BaseAPIService.

This module contains extensive test coverage for:
- BaseAPIService class initialization and configuration
- Factory method for creating services from config
- Session management and HTTP request operations
- Error handling and context manager functionality
"""

import pytest
import os
import sys
import importlib.util
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from typing import Dict, Optional, Union
import aiohttp
from aiohttp import ClientTimeout, ClientSession

# Add the src directory to sys.path for proper import
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
if src_path not in sys.path:
    sys.path.insert(0, os.path.abspath(src_path))

# Mock Azure modules before importing the BaseAPIService
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

# Mock other problematic modules  
sys.modules['common.models.messages_af'] = MagicMock()

# Mock the config module
mock_config_module = MagicMock()
mock_config = MagicMock()

# Mock config attributes for BaseAPIService tests
mock_config.AZURE_AI_AGENT_ENDPOINT = 'https://test.agent.endpoint.com'
mock_config.TEST_ENDPOINT = 'https://test.example.com'
mock_config.MISSING_ENDPOINT = None

mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

# Now import the real BaseAPIService using direct file import but register for coverage
import importlib.util
base_api_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'base_api_service.py')
base_api_service_path = os.path.abspath(base_api_service_path)
spec = importlib.util.spec_from_file_location("backend.v4.common.services.base_api_service", base_api_service_path)
base_api_service_module = importlib.util.module_from_spec(spec)

# Set the proper module name for coverage tracking (matching --cov=backend pattern)
base_api_service_module.__name__ = "backend.v4.common.services.base_api_service"
base_api_service_module.__file__ = base_api_service_path

# Add to sys.modules BEFORE execution for coverage tracking (both variations)
sys.modules['backend.v4.common.services.base_api_service'] = base_api_service_module
sys.modules['src.backend.v4.common.services.base_api_service'] = base_api_service_module

spec.loader.exec_module(base_api_service_module)
BaseAPIService = base_api_service_module.BaseAPIService


class TestBaseAPIService:
    """Test cases for BaseAPIService class."""

    def test_init_with_required_parameters(self):
        """Test BaseAPIService initialization with required parameters."""
        service = BaseAPIService("https://api.example.com")
        
        assert service.base_url == "https://api.example.com"
        assert service.default_headers == {}
        assert isinstance(service.timeout, ClientTimeout)
        assert service.timeout.total == 30
        assert service._session is None
        assert service._session_external is False

    def test_init_with_trailing_slash_removal(self):
        """Test that trailing slashes are removed from base_url."""
        service = BaseAPIService("https://api.example.com/")
        assert service.base_url == "https://api.example.com"

    def test_init_with_empty_base_url_raises_error(self):
        """Test that empty base_url raises ValueError."""
        with pytest.raises(ValueError, match="base_url is required"):
            BaseAPIService("")

    def test_init_with_optional_parameters(self):
        """Test BaseAPIService initialization with optional parameters."""
        headers = {"Authorization": "Bearer token"}
        session = Mock(spec=ClientSession)
        
        service = BaseAPIService(
            "https://api.example.com",
            default_headers=headers,
            timeout_seconds=60,
            session=session
        )
        
        assert service.base_url == "https://api.example.com"
        assert service.default_headers == headers
        assert service.timeout.total == 60
        assert service._session == session
        assert service._session_external is True

    def test_from_config_with_valid_endpoint(self):
        """Test from_config with a valid endpoint attribute."""
        with patch.object(base_api_service_module, 'config', mock_config):
            service = BaseAPIService.from_config('AZURE_AI_AGENT_ENDPOINT')
            
            assert service.base_url == 'https://test.agent.endpoint.com'
            assert service.default_headers == {}

    def test_from_config_with_valid_endpoint_and_kwargs(self):
        """Test from_config with valid endpoint and additional kwargs."""
        headers = {"Content-Type": "application/json"}
        with patch.object(base_api_service_module, 'config', mock_config):
            service = BaseAPIService.from_config(
                'TEST_ENDPOINT', 
                default_headers=headers,
                timeout_seconds=45
            )
            
            assert service.base_url == 'https://test.example.com'
            assert service.default_headers == headers
            assert service.timeout.total == 45

    def test_from_config_with_missing_endpoint_and_default(self):
        """Test from_config with missing endpoint but provided default.""" 
        with patch.object(base_api_service_module, 'config', mock_config):
            mock_config.NONEXISTENT_ENDPOINT = None
            service = BaseAPIService.from_config(
                'NONEXISTENT_ENDPOINT',
                default='https://default.example.com'
            )
            assert service.base_url == 'https://default.example.com'

    def test_from_config_with_missing_endpoint_no_default_raises_error(self):
        """Test from_config raises error when endpoint missing and no default."""
        with patch.object(base_api_service_module, 'config', mock_config):
            mock_config.NONEXISTENT_ENDPOINT = None
            with pytest.raises(ValueError, match="Endpoint 'NONEXISTENT_ENDPOINT' not configured"):
                BaseAPIService.from_config('NONEXISTENT_ENDPOINT')

    def test_from_config_with_none_endpoint_and_default(self):
        """Test from_config with None endpoint value but provided default."""
        with patch.object(base_api_service_module, 'config', mock_config):
            service = BaseAPIService.from_config(
                'MISSING_ENDPOINT',
                default='https://fallback.example.com'
            )
            
            assert service.base_url == 'https://fallback.example.com'

    @pytest.mark.asyncio
    async def test_ensure_session_creates_new_session(self):
        """Test _ensure_session creates a new session when none exists."""
        service = BaseAPIService("https://api.example.com")
        
        session = await service._ensure_session()
        
        assert isinstance(session, ClientSession)
        assert service._session == session

    @pytest.mark.asyncio
    async def test_ensure_session_reuses_existing_session(self):
        """Test _ensure_session reuses existing open session."""
        service = BaseAPIService("https://api.example.com")
        
        # Create first session
        session1 = await service._ensure_session()
        # Get session again
        session2 = await service._ensure_session()
        
        assert session1 == session2

    @pytest.mark.asyncio
    async def test_ensure_session_creates_new_when_closed(self):
        """Test _ensure_session creates new session when existing is closed."""
        service = BaseAPIService("https://api.example.com")
        
        # Mock a closed session
        closed_session = Mock(spec=ClientSession)
        closed_session.closed = True
        service._session = closed_session
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_new_session = Mock(spec=ClientSession)
            mock_session_class.return_value = mock_new_session
            
            session = await service._ensure_session()
            
            assert session == mock_new_session
            mock_session_class.assert_called_once_with(timeout=service.timeout)

    def test_url_with_empty_path(self):
        """Test _url with empty path returns base URL."""
        service = BaseAPIService("https://api.example.com")
        
        assert service._url("") == "https://api.example.com"
        assert service._url(None) == "https://api.example.com"

    def test_url_with_simple_path(self):
        """Test _url with simple path."""
        service = BaseAPIService("https://api.example.com")
        
        assert service._url("users") == "https://api.example.com/users"

    def test_url_with_leading_slash_path(self):
        """Test _url with path that has leading slash."""
        service = BaseAPIService("https://api.example.com")
        
        assert service._url("/users") == "https://api.example.com/users"

    def test_url_with_complex_path(self):
        """Test _url with complex path."""
        service = BaseAPIService("https://api.example.com")
        
        assert service._url("users/123/profile") == "https://api.example.com/users/123/profile"

    @pytest.mark.asyncio
    async def test_request_method(self):
        """Test _request method with various parameters."""
        service = BaseAPIService("https://api.example.com", default_headers={"Auth": "token"})
        
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_session = Mock(spec=ClientSession)
        mock_session.request = AsyncMock(return_value=mock_response)
        
        with patch.object(service, '_ensure_session', return_value=mock_session):
            response = await service._request(
                "POST",
                "users",
                headers={"Content-Type": "application/json"},
                params={"page": 1},
                json={"name": "test"}
            )
            
            assert response == mock_response
            mock_session.request.assert_called_once_with(
                "POST",
                "https://api.example.com/users",
                headers={"Auth": "token", "Content-Type": "application/json"},
                params={"page": 1},
                json={"name": "test"}
            )

    @pytest.mark.asyncio
    async def test_request_merges_headers(self):
        """Test _request merges default headers with provided headers."""
        service = BaseAPIService(
            "https://api.example.com", 
            default_headers={"Authorization": "Bearer token", "User-Agent": "TestAgent"}
        )
        
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_session = Mock(spec=ClientSession)
        mock_session.request = AsyncMock(return_value=mock_response)
        
        with patch.object(service, '_ensure_session', return_value=mock_session):
            await service._request(
                "GET",
                "data",
                headers={"Content-Type": "application/json", "User-Agent": "OverrideAgent"}
            )
            
            mock_session.request.assert_called_once()
            call_args = mock_session.request.call_args
            headers = call_args[1]['headers']
            
            assert headers["Authorization"] == "Bearer token"
            assert headers["Content-Type"] == "application/json"
            assert headers["User-Agent"] == "OverrideAgent"  # Should be overridden

    @pytest.mark.asyncio
    async def test_get_json_success(self):
        """Test get_json method with successful response."""
        service = BaseAPIService("https://api.example.com")
        
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"data": "test"})
        
        with patch.object(service, '_request', return_value=mock_response):
            result = await service.get_json("users", headers={"Accept": "application/json"}, params={"id": 123})
            
            assert result == {"data": "test"}
            mock_response.raise_for_status.assert_called_once()
            mock_response.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_json_with_http_error(self):
        """Test get_json method raises error on HTTP error."""
        service = BaseAPIService("https://api.example.com")
        
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientError("404 Not Found"))
        
        with patch.object(service, '_request', return_value=mock_response):
            with pytest.raises(aiohttp.ClientError, match="404 Not Found"):
                await service.get_json("nonexistent")

    @pytest.mark.asyncio
    async def test_post_json_success(self):
        """Test post_json method with successful response."""
        service = BaseAPIService("https://api.example.com")
        
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"created": True, "id": 456})
        
        with patch.object(service, '_request', return_value=mock_response):
            result = await service.post_json(
                "users",
                headers={"Content-Type": "application/json"},
                params={"validate": True},
                json={"name": "John", "email": "john@example.com"}
            )
            
            assert result == {"created": True, "id": 456}
            mock_response.raise_for_status.assert_called_once()
            mock_response.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_json_with_http_error(self):
        """Test post_json method raises error on HTTP error."""
        service = BaseAPIService("https://api.example.com")
        
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientError("400 Bad Request"))
        
        with patch.object(service, '_request', return_value=mock_response):
            with pytest.raises(aiohttp.ClientError, match="400 Bad Request"):
                await service.post_json("users", json={"invalid": "data"})

    @pytest.mark.asyncio
    async def test_close_with_internal_session(self):
        """Test close method with internal session."""
        service = BaseAPIService("https://api.example.com")
        
        mock_session = Mock(spec=ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        service._session = mock_session
        service._session_external = False
        
        await service.close()
        
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_external_session(self):
        """Test close method with external session (should not close)."""
        mock_session = Mock(spec=ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        
        service = BaseAPIService("https://api.example.com", session=mock_session)
        
        await service.close()
        
        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_with_already_closed_session(self):
        """Test close method with already closed session."""
        service = BaseAPIService("https://api.example.com")
        
        mock_session = Mock(spec=ClientSession)
        mock_session.closed = True
        mock_session.close = AsyncMock()
        service._session = mock_session
        service._session_external = False
        
        await service.close()
        
        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_with_no_session(self):
        """Test close method with no session."""
        service = BaseAPIService("https://api.example.com")
        
        # Should not raise any exception
        await service.close()

    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        """Test async context manager __aenter__ method."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_ensure_session') as mock_ensure:
            mock_session = Mock(spec=ClientSession)
            mock_ensure.return_value = mock_session
            
            result = await service.__aenter__()
            
            assert result == service
            mock_ensure.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit(self):
        """Test async context manager __aexit__ method."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, 'close') as mock_close:
            await service.__aexit__(None, None, None)
            
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_full_usage(self):
        """Test full async context manager usage."""
        service = BaseAPIService("https://api.example.com")
        
        with patch.object(service, '_ensure_session') as mock_ensure, \
             patch.object(service, 'close') as mock_close:
            
            mock_session = Mock(spec=ClientSession)
            mock_ensure.return_value = mock_session
            
            async with service as svc:
                assert svc == service
                
            mock_ensure.assert_called_once()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_integration_workflow(self):
        """Test integration workflow with multiple method calls."""
        service = BaseAPIService(
            "https://api.example.com",
            default_headers={"Authorization": "Bearer test-token"}
        )
        
        # Mock session and responses
        mock_session = Mock(spec=ClientSession)
        
        # Mock GET response
        mock_get_response = Mock(spec=aiohttp.ClientResponse)
        mock_get_response.raise_for_status = Mock()
        mock_get_response.json = AsyncMock(return_value={"users": [{"id": 1, "name": "Alice"}]})
        
        # Mock POST response
        mock_post_response = Mock(spec=aiohttp.ClientResponse)
        mock_post_response.raise_for_status = Mock()
        mock_post_response.json = AsyncMock(return_value={"id": 2, "name": "Bob", "created": True})
        
        mock_session.request = AsyncMock(side_effect=[mock_get_response, mock_post_response])
        
        with patch.object(service, '_ensure_session', return_value=mock_session):
            # Test GET request
            users = await service.get_json("users", params={"active": True})
            assert users == {"users": [{"id": 1, "name": "Alice"}]}
            
            # Test POST request
            new_user = await service.post_json(
                "users",
                json={"name": "Bob", "email": "bob@example.com"}
            )
            assert new_user == {"id": 2, "name": "Bob", "created": True}
            
            # Verify session.request was called twice with correct parameters
            assert mock_session.request.call_count == 2
            
            # Verify first call (GET)
            first_call = mock_session.request.call_args_list[0]
            assert first_call[0] == ("GET", "https://api.example.com/users")
            assert first_call[1]["params"] == {"active": True}
            assert first_call[1]["headers"]["Authorization"] == "Bearer test-token"
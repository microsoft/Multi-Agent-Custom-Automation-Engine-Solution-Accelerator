# Copyright (c) Microsoft. All rights reserved.
"""Tests for services/base_api_service.py."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
from aiohttp import ClientSession, ClientTimeout

# Add src/backend to sys.path so flat imports inside base_api_service resolve
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Mock Azure and common modules before importing the target
sys.modules.setdefault('azure', MagicMock())
sys.modules.setdefault('azure.ai', MagicMock())
sys.modules.setdefault('azure.ai.projects', MagicMock())
sys.modules.setdefault('azure.ai.projects.aio', MagicMock())

mock_config = MagicMock()
mock_config.AZURE_AI_AGENT_ENDPOINT = 'https://test.agent.endpoint.com'
mock_config.TEST_ENDPOINT = 'https://test.example.com'
mock_config.MISSING_ENDPOINT = None

mock_config_module = MagicMock()
mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

import backend.services.base_api_service as base_api_service_module
from backend.services.base_api_service import BaseAPIService


class TestBaseAPIService:
    """Test cases for BaseAPIService class."""

    def test_init_with_required_parameters(self):
        service = BaseAPIService("https://api.example.com")
        assert service.base_url == "https://api.example.com"
        assert service.default_headers == {}
        assert isinstance(service.timeout, ClientTimeout)
        assert service.timeout.total == 30
        assert service._session is None
        assert service._session_external is False

    def test_init_with_trailing_slash_removal(self):
        service = BaseAPIService("https://api.example.com/")
        assert service.base_url == "https://api.example.com"

    def test_init_with_empty_base_url_raises_error(self):
        with pytest.raises(ValueError, match="base_url is required"):
            BaseAPIService("")

    def test_init_with_optional_parameters(self):
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
        with patch.object(base_api_service_module, 'config', mock_config):
            service = BaseAPIService.from_config('AZURE_AI_AGENT_ENDPOINT')
            assert service.base_url == 'https://test.agent.endpoint.com'
            assert service.default_headers == {}

    def test_from_config_with_valid_endpoint_and_kwargs(self):
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
        with patch.object(base_api_service_module, 'config', mock_config):
            mock_config.NONEXISTENT_ENDPOINT = None
            service = BaseAPIService.from_config(
                'NONEXISTENT_ENDPOINT',
                default='https://default.example.com'
            )
            assert service.base_url == 'https://default.example.com'

    def test_from_config_with_missing_endpoint_no_default_raises_error(self):
        with patch.object(base_api_service_module, 'config', mock_config):
            mock_config.NONEXISTENT_ENDPOINT = None
            with pytest.raises(ValueError, match="Endpoint 'NONEXISTENT_ENDPOINT' not configured"):
                BaseAPIService.from_config('NONEXISTENT_ENDPOINT')

    def test_from_config_with_none_endpoint_and_default(self):
        with patch.object(base_api_service_module, 'config', mock_config):
            service = BaseAPIService.from_config(
                'MISSING_ENDPOINT',
                default='https://fallback.example.com'
            )
            assert service.base_url == 'https://fallback.example.com'

    @pytest.mark.asyncio
    async def test_ensure_session_creates_new_session(self):
        service = BaseAPIService("https://api.example.com")
        session = await service._ensure_session()
        assert isinstance(session, ClientSession)
        assert service._session == session
        await service.close()

    @pytest.mark.asyncio
    async def test_ensure_session_reuses_existing_session(self):
        service = BaseAPIService("https://api.example.com")
        session1 = await service._ensure_session()
        session2 = await service._ensure_session()
        assert session1 == session2
        await service.close()

    @pytest.mark.asyncio
    async def test_ensure_session_creates_new_when_closed(self):
        service = BaseAPIService("https://api.example.com")
        closed_session = Mock(spec=ClientSession)
        closed_session.closed = True
        service._session = closed_session

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_new_session = Mock(spec=ClientSession)
            mock_session_class.return_value = mock_new_session
            session = await service._ensure_session()
            assert session == mock_new_session

    def test_url_with_empty_path(self):
        service = BaseAPIService("https://api.example.com")
        assert service._url("") == "https://api.example.com"
        assert service._url(None) == "https://api.example.com"

    def test_url_with_simple_path(self):
        service = BaseAPIService("https://api.example.com")
        assert service._url("users") == "https://api.example.com/users"

    def test_url_with_leading_slash_path(self):
        service = BaseAPIService("https://api.example.com")
        assert service._url("/users") == "https://api.example.com/users"

    def test_url_with_complex_path(self):
        service = BaseAPIService("https://api.example.com")
        assert service._url("users/123/profile") == "https://api.example.com/users/123/profile"

    @pytest.mark.asyncio
    async def test_request_method(self):
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
            call_args = mock_session.request.call_args
            headers = call_args[1]['headers']
            assert headers["Authorization"] == "Bearer token"
            assert headers["Content-Type"] == "application/json"
            assert headers["User-Agent"] == "OverrideAgent"

    @pytest.mark.asyncio
    async def test_get_json_success(self):
        service = BaseAPIService("https://api.example.com")
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"data": "test"})

        with patch.object(service, '_request', return_value=mock_response):
            result = await service.get_json("users", headers={"Accept": "application/json"}, params={"id": 123})
            assert result == {"data": "test"}
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_json_with_http_error(self):
        service = BaseAPIService("https://api.example.com")
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientError("404 Not Found"))

        with patch.object(service, '_request', return_value=mock_response):
            with pytest.raises(aiohttp.ClientError, match="404 Not Found"):
                await service.get_json("nonexistent")

    @pytest.mark.asyncio
    async def test_post_json_success(self):
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

    @pytest.mark.asyncio
    async def test_post_json_with_http_error(self):
        service = BaseAPIService("https://api.example.com")
        mock_response = Mock(spec=aiohttp.ClientResponse)
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientError("400 Bad Request"))

        with patch.object(service, '_request', return_value=mock_response):
            with pytest.raises(aiohttp.ClientError, match="400 Bad Request"):
                await service.post_json("users", json={"invalid": "data"})

    @pytest.mark.asyncio
    async def test_close_with_internal_session(self):
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
        mock_session = Mock(spec=ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        service = BaseAPIService("https://api.example.com", session=mock_session)

        await service.close()
        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_with_already_closed_session(self):
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
        service = BaseAPIService("https://api.example.com")
        await service.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        service = BaseAPIService("https://api.example.com")
        with patch.object(service, '_ensure_session') as mock_ensure:
            mock_session = Mock(spec=ClientSession)
            mock_ensure.return_value = mock_session
            result = await service.__aenter__()
            assert result == service
            mock_ensure.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit(self):
        service = BaseAPIService("https://api.example.com")
        with patch.object(service, 'close') as mock_close:
            await service.__aexit__(None, None, None)
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_full_usage(self):
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
        service = BaseAPIService(
            "https://api.example.com",
            default_headers={"Authorization": "Bearer test-token"}
        )
        mock_session = Mock(spec=ClientSession)

        mock_get_response = Mock(spec=aiohttp.ClientResponse)
        mock_get_response.raise_for_status = Mock()
        mock_get_response.json = AsyncMock(return_value={"users": [{"id": 1, "name": "Alice"}]})

        mock_post_response = Mock(spec=aiohttp.ClientResponse)
        mock_post_response.raise_for_status = Mock()
        mock_post_response.json = AsyncMock(return_value={"id": 2, "name": "Bob", "created": True})

        mock_session.request = AsyncMock(side_effect=[mock_get_response, mock_post_response])

        with patch.object(service, '_ensure_session', return_value=mock_session):
            users = await service.get_json("users", params={"active": True})
            assert users == {"users": [{"id": 1, "name": "Alice"}]}

            new_user = await service.post_json(
                "users",
                json={"name": "Bob", "email": "bob@example.com"}
            )
            assert new_user == {"id": 2, "name": "Bob", "created": True}

            assert mock_session.request.call_count == 2
            first_call = mock_session.request.call_args_list[0]
            assert first_call[0] == ("GET", "https://api.example.com/users")
            assert first_call[1]["headers"]["Authorization"] == "Bearer test-token"

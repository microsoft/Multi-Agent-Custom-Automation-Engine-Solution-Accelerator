# Copyright (c) Microsoft. All rights reserved.
"""Tests for services/foundry_service.py."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src/backend to sys.path
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Mock Azure modules before importing
sys.modules.setdefault('azure', MagicMock())
sys.modules.setdefault('azure.ai', MagicMock())
sys.modules.setdefault('azure.ai.projects', MagicMock())
sys.modules.setdefault('azure.ai.projects.aio', MagicMock())

mock_config = MagicMock()
mock_config.AZURE_AI_SUBSCRIPTION_ID = "test-subscription-id"
mock_config.AZURE_AI_RESOURCE_GROUP = "test-resource-group"
mock_config.AZURE_AI_PROJECT_NAME = "test-project-name"
mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.ai.azure.com"
mock_config.AZURE_OPENAI_ENDPOINT = "https://test-openai.openai.azure.com/"
mock_config.AZURE_MANAGEMENT_SCOPE = "https://management.azure.com/.default"

def _mock_get_ai_project_client():
    client = MagicMock()
    client.connections = MagicMock()
    client.connections.list = AsyncMock()
    client.connections.get = AsyncMock()
    return client

def _mock_get_azure_credentials():
    cred = MagicMock()
    token = MagicMock()
    token.token = "mock-access-token"
    cred.get_token.return_value = token
    return cred

mock_config.get_ai_project_client = _mock_get_ai_project_client
mock_config.get_azure_credentials = _mock_get_azure_credentials

mock_config_module = MagicMock()
mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

import backend.services.foundry_service as foundry_service_module
from backend.services.foundry_service import FoundryService


class MockConnection:
    def __init__(self, data):
        self.data = data

    def as_dict(self):
        return self.data


class TestFoundryServiceInitialization:
    def test_initialization_with_client(self):
        mock_client = MagicMock()
        service = FoundryService(client=mock_client)
        assert service._client == mock_client
        assert hasattr(service, 'logger')

    def test_initialization_without_client(self):
        service = FoundryService()
        assert service._client is None
        assert hasattr(service, 'logger')

    def test_initialization_with_none_client(self):
        service = FoundryService(client=None)
        assert service._client is None


class TestFoundryServiceClientManagement:
    @pytest.mark.asyncio
    async def test_get_client_lazy_loading(self):
        with patch.object(foundry_service_module, 'config', mock_config):
            service = FoundryService()
            assert service._client is None
            client = await service.get_client()
            assert client is not None
            assert service._client == client

    @pytest.mark.asyncio
    async def test_get_client_returns_existing_client(self):
        mock_client = MagicMock()
        service = FoundryService(client=mock_client)
        client = await service.get_client()
        assert client == mock_client

    @pytest.mark.asyncio
    async def test_get_client_caches_result(self):
        with patch.object(foundry_service_module, 'config', mock_config):
            service = FoundryService()
            client1 = await service.get_client()
            client2 = await service.get_client()
            assert client1 == client2
            assert service._client == client1


class TestFoundryServiceConnections:
    @pytest.mark.asyncio
    async def test_list_connections_success(self):
        mock_client = MagicMock()
        mock_connections = [
            MockConnection({"name": "conn1", "type": "AzureOpenAI"}),
            MockConnection({"name": "conn2", "type": "AzureAI"}),
        ]
        mock_client.connections.list = AsyncMock(return_value=mock_connections)
        service = FoundryService(client=mock_client)
        connections = await service.list_connections()
        assert len(connections) == 2
        assert connections[0]["name"] == "conn1"
        mock_client.connections.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_connections_empty(self):
        mock_client = MagicMock()
        mock_client.connections.list = AsyncMock(return_value=[])
        service = FoundryService(client=mock_client)
        connections = await service.list_connections()
        assert connections == []

    @pytest.mark.asyncio
    async def test_get_connection_success(self):
        mock_client = MagicMock()
        mock_connection = MockConnection({"name": "test_conn", "type": "AzureOpenAI"})
        mock_client.connections.get = AsyncMock(return_value=mock_connection)
        service = FoundryService(client=mock_client)
        connection = await service.get_connection("test_conn")
        assert connection["name"] == "test_conn"
        mock_client.connections.get.assert_called_once_with(name="test_conn")

    @pytest.mark.asyncio
    async def test_list_connections_handles_dict_objects(self):
        mock_client = MagicMock()
        mock_connection = {"name": "dict_conn", "type": "Dictionary"}
        mock_client.connections.list = AsyncMock(return_value=[mock_connection])
        service = FoundryService(client=mock_client)
        connections = await service.list_connections()
        assert len(connections) == 1
        assert connections[0]["name"] == "dict_conn"

    @pytest.mark.asyncio
    async def test_get_connection_handles_dict_object(self):
        mock_client = MagicMock()
        mock_connection = {"name": "dict_conn", "type": "Dictionary"}
        mock_client.connections.get = AsyncMock(return_value=mock_connection)
        service = FoundryService(client=mock_client)
        connection = await service.get_connection("dict_conn")
        assert connection["name"] == "dict_conn"

    @pytest.mark.asyncio
    async def test_list_connections_with_lazy_client(self):
        service = FoundryService()
        mock_client = MagicMock()
        mock_connections = [MockConnection({"name": "lazy_conn", "type": "Azure"})]
        mock_client.connections.list = AsyncMock(return_value=mock_connections)

        async def mock_get_client():
            if service._client is None:
                service._client = mock_client
            return service._client

        service.get_client = mock_get_client
        connections = await service.list_connections()
        assert len(connections) == 1
        assert connections[0]["name"] == "lazy_conn"


class TestFoundryServiceModelDeployments:
    @pytest.mark.asyncio
    async def test_list_model_deployments_success(self):
        with patch.object(foundry_service_module, 'config', mock_config):
            with patch('aiohttp.ClientSession') as mock_session_cls:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={
                    "value": [
                        {
                            "name": "deployment1",
                            "properties": {
                                "model": {"name": "gpt-4", "version": "0613"},
                                "provisioningState": "Succeeded",
                                "scoringUri": "https://test.openai.azure.com/v1/chat/completions"
                            }
                        }
                    ]
                })
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                service = FoundryService()
                deployments = await service.list_model_deployments()
                assert len(deployments) == 1
                assert deployments[0]["name"] == "deployment1"
                assert deployments[0]["status"] == "Succeeded"

    @pytest.mark.asyncio
    async def test_list_model_deployments_empty_response(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": []}
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch.object(foundry_service_module, 'config', mock_config):
                service = FoundryService()
                deployments = await service.list_model_deployments()
                assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_malformed_response(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"error": "some error"}
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch.object(foundry_service_module, 'config', mock_config):
                service = FoundryService()
                deployments = await service.list_model_deployments()
                assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_http_error(self):
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.side_effect = Exception("HTTP Error")

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch.object(foundry_service_module, 'config', mock_config):
                service = FoundryService()
                deployments = await service.list_model_deployments()
                assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_multiple_deployments(self):
        with patch.object(foundry_service_module, 'config', mock_config):
            with patch('aiohttp.ClientSession') as mock_session_cls:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={
                    "value": [
                        {
                            "name": "deployment1",
                            "properties": {
                                "model": {"name": "gpt-4", "version": "0613"},
                                "provisioningState": "Succeeded",
                            }
                        },
                        {
                            "name": "deployment2",
                            "properties": {
                                "model": {"name": "gpt-35-turbo", "version": "0301"},
                                "provisioningState": "Running",
                            }
                        }
                    ]
                })
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                service = FoundryService()
                deployments = await service.list_model_deployments()
                assert len(deployments) == 2
                assert deployments[0]["name"] == "deployment1"
                assert deployments[1]["name"] == "deployment2"
                assert deployments[0]["status"] == "Succeeded"
                assert deployments[1]["status"] == "Running"

    @pytest.mark.asyncio
    async def test_list_model_deployments_invalid_endpoint(self):
        with patch.object(foundry_service_module, 'config', mock_config):
            mock_config.AZURE_OPENAI_ENDPOINT = "https://invalid-endpoint.com/"
            service = FoundryService()
            deployments = await service.list_model_deployments()
            assert deployments == []


class TestFoundryServiceErrorHandling:
    @pytest.mark.asyncio
    async def test_list_connections_client_error(self):
        mock_client = MagicMock()
        mock_client.connections.list.side_effect = Exception("Client error")
        service = FoundryService(client=mock_client)
        with pytest.raises(Exception):
            await service.list_connections()

    @pytest.mark.asyncio
    async def test_get_connection_client_error(self):
        mock_client = MagicMock()
        mock_client.connections.get.side_effect = Exception("Connection not found")
        service = FoundryService(client=mock_client)
        with pytest.raises(Exception):
            await service.get_connection("nonexistent")

    @pytest.mark.asyncio
    async def test_list_model_deployments_credential_error(self):
        with patch.object(foundry_service_module, 'config', mock_config):
            mock_config.get_azure_credentials.side_effect = Exception("Credential error")
            service = FoundryService()
            deployments = await service.list_model_deployments()
            assert deployments == []

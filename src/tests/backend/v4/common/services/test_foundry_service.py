"""
Comprehensive unit tests for FoundryService.

This module contains extensive test coverage for:
- FoundryService class initialization
- Client management and lazy loading
- Connection listing and retrieval
- Model deployment operations
- Error handling and edge cases
"""

import pytest
import os
import re
import logging
import aiohttp
import sys
import importlib.util
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from typing import Any, Dict, List

# Add backend directory to sys.path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_dir)

# Mock Azure modules before importing the FoundryService
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

# Mock the config module
mock_config_module = MagicMock()
mock_config = MagicMock()
mock_config.AZURE_AI_SUBSCRIPTION_ID = "test-subscription-id"
mock_config.AZURE_AI_RESOURCE_GROUP = "test-resource-group"
mock_config.AZURE_AI_PROJECT_NAME = "test-project-name"
mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.ai.azure.com"
mock_config.AZURE_OPENAI_ENDPOINT = "https://test-openai.openai.azure.com/"
mock_config.AZURE_MANAGEMENT_SCOPE = "https://management.azure.com/.default"

def mock_get_ai_project_client():
    """Mock function to return AIProjectClient."""
    client = MagicMock()
    client.connections = MagicMock()
    client.connections.list = AsyncMock()
    client.connections.get = AsyncMock()
    return client

def mock_get_azure_credentials():
    """Mock function to return Azure credentials."""
    mock_credential = MagicMock()
    mock_token = MagicMock()
    mock_token.token = "mock-access-token"
    mock_credential.get_token.return_value = mock_token
    return mock_credential

mock_config.get_ai_project_client = mock_get_ai_project_client
mock_config.get_azure_credentials = mock_get_azure_credentials

mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

# Now import the real FoundryService
from backend.v4.common.services.foundry_service import FoundryService

# Also import the module for patching
import backend.v4.common.services.foundry_service as foundry_service_module


# Test fixtures and mock classes
class MockConnection:
    """Mock connection object with as_dict method."""
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    def as_dict(self):
        return self.data


class TestFoundryServiceInitialization:
    """Test cases for FoundryService initialization."""

    def test_initialization_with_client(self):
        """Test FoundryService initialization with provided client."""
        mock_client = MagicMock()
        service = FoundryService(client=mock_client)
        
        assert service._client == mock_client
        assert hasattr(service, 'logger')

    def test_initialization_without_client(self):
        """Test FoundryService initialization without client (lazy loading)."""
        service = FoundryService()
        assert service._client is None
        assert hasattr(service, 'logger')

    def test_initialization_with_none_client(self):
        """Test FoundryService initialization with None client explicitly."""
        service = FoundryService(client=None)
        
        assert service._client is None
        assert hasattr(service, 'logger')


class TestFoundryServiceClientManagement:
    """Test cases for FoundryService client management."""

    @pytest.mark.asyncio
    async def test_get_client_lazy_loading(self):
        """Test lazy loading of client when not provided during initialization."""
        with patch.object(foundry_service_module, 'config', mock_config):
            service = FoundryService()
            assert service._client is None
            
            client = await service.get_client()
            assert client is not None
            assert service._client == client

    @pytest.mark.asyncio
    async def test_get_client_returns_existing_client(self):
        """Test that get_client returns existing client if already initialized."""
        mock_client = MagicMock()
        service = FoundryService(client=mock_client)
        
        client = await service.get_client()
        assert client == mock_client

    @pytest.mark.asyncio
    async def test_get_client_caches_result(self):
        """Test that get_client caches the result for subsequent calls."""
        with patch.object(foundry_service_module, 'config', mock_config):
            service = FoundryService()
            assert service._client is None
            
            client1 = await service.get_client()
            client2 = await service.get_client()
            
            assert client1 is not None
            assert client1 == client2
            assert service._client == client1


class TestFoundryServiceConnections:
    """Test cases for FoundryService connection operations."""

    @pytest.mark.asyncio
    async def test_list_connections_success(self):
        """Test successful listing of connections."""
        mock_client = MagicMock()
        mock_connections = [
            MockConnection({"name": "conn1", "type": "AzureOpenAI"}),
            MockConnection({"name": "conn2", "type": "AzureAI"})
        ]
        mock_client.connections.list = AsyncMock(return_value=mock_connections)
        
        service = FoundryService(client=mock_client)
        connections = await service.list_connections()
        
        assert len(connections) == 2
        assert connections[0]["name"] == "conn1"
        assert connections[1]["name"] == "conn2"
        mock_client.connections.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_connections_empty(self):
        """Test listing connections when no connections exist."""
        mock_client = MagicMock()
        mock_client.connections.list = AsyncMock(return_value=[])
        
        service = FoundryService(client=mock_client)
        connections = await service.list_connections()
        
        assert connections == []
        mock_client.connections.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_success(self):
        """Test successful retrieval of a specific connection."""
        mock_client = MagicMock()
        mock_connection = MockConnection({"name": "test_conn", "type": "AzureOpenAI"})
        mock_client.connections.get = AsyncMock(return_value=mock_connection)
        
        service = FoundryService(client=mock_client)
        connection = await service.get_connection("test_conn")
        
        assert connection["name"] == "test_conn"
        assert connection["type"] == "AzureOpenAI"
        mock_client.connections.get.assert_called_once_with(name="test_conn")

    @pytest.mark.asyncio
    async def test_list_connections_handles_dict_objects(self):
        """Test that list_connections handles objects that don't have as_dict method."""
        mock_client = MagicMock()
        mock_connection = {"name": "dict_conn", "type": "Dictionary"}
        mock_client.connections.list = AsyncMock(return_value=[mock_connection])
        
        service = FoundryService(client=mock_client)
        connections = await service.list_connections()
        
        assert len(connections) == 1
        assert connections[0]["name"] == "dict_conn"

    @pytest.mark.asyncio
    async def test_get_connection_handles_dict_object(self):
        """Test that get_connection handles objects that don't have as_dict method."""
        mock_client = MagicMock()
        mock_connection = {"name": "dict_conn", "type": "Dictionary"}
        mock_client.connections.get = AsyncMock(return_value=mock_connection)
        
        service = FoundryService(client=mock_client)
        connection = await service.get_connection("dict_conn")
        
        assert connection["name"] == "dict_conn"
        assert connection["type"] == "Dictionary"

    @pytest.mark.asyncio
    async def test_list_connections_with_lazy_client(self):
        """Test list_connections works with lazy-loaded client."""
        service = FoundryService()  # No client provided
        
        # Mock the connections
        service._client = None
        mock_client = MagicMock()
        mock_connections = [MockConnection({"name": "lazy_conn", "type": "Azure"})]
        mock_client.connections.list = AsyncMock(return_value=mock_connections)
        
        # Replace the get_client method to return our mock
        async def mock_get_client():
            if service._client is None:
                service._client = mock_client
            return service._client
        
        service.get_client = mock_get_client
        
        connections = await service.list_connections()
        
        assert len(connections) == 1
        assert connections[0]["name"] == "lazy_conn"


class TestFoundryServiceModelDeployments:
    """Test cases for model deployment operations."""

    @pytest.mark.asyncio
    async def test_list_model_deployments_success(self):
        """Test successful listing of model deployments."""
        with patch.object(foundry_service_module, 'config', mock_config):
            with patch('aiohttp.ClientSession') as mock_session_cls:
                # Create mock response
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
                
                # Create mock session
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
                assert deployments[0]["model"]["name"] == "gpt-4"
                assert deployments[0]["status"] == "Succeeded"

    @pytest.mark.asyncio
    async def test_list_model_deployments_empty_response(self):
        """Test handling of empty deployment list."""        
        mock_response = AsyncMock()
        mock_response.json.return_value = {"value": []}
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            service = FoundryService()
            deployments = await service.list_model_deployments()
            
            assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_malformed_response(self):
        """Test handling of malformed response data."""        
        mock_response = AsyncMock()
        mock_response.json.return_value = {"error": "some error"}  # Missing 'value' key
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            service = FoundryService()
            deployments = await service.list_model_deployments()
            
            assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_http_error(self):
        """Test handling of HTTP errors during deployment listing."""        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.get.side_effect = Exception("HTTP Error")
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            service = FoundryService()
            deployments = await service.list_model_deployments()
            
            assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_multiple_deployments(self):
        """Test handling of multiple deployments."""
        with patch.object(foundry_service_module, 'config', mock_config):
            with patch('aiohttp.ClientSession') as mock_session_cls:
                # Create mock response
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
                        },
                        {
                            "name": "deployment2",
                            "properties": {
                                "model": {"name": "gpt-35-turbo", "version": "0301"},
                                "provisioningState": "Running"
                            }
                        }
                    ]
                })
                
                # Create mock session  
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
        """Test list_model_deployments with invalid endpoint configuration."""
        with patch.object(foundry_service_module, 'config', mock_config):
            # Mock an invalid endpoint
            mock_config.AZURE_OPENAI_ENDPOINT = "https://invalid-endpoint.com/"
            
            service = FoundryService()
            deployments = await service.list_model_deployments()
            assert deployments == []


class TestFoundryServiceErrorHandling:
    """Test cases for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_list_connections_client_error(self):
        """Test handling of client errors during connection listing."""
        mock_client = MagicMock()
        mock_client.connections.list.side_effect = Exception("Client error")
        
        service = FoundryService(client=mock_client)
        
        with pytest.raises(Exception):
            await service.list_connections()

    @pytest.mark.asyncio
    async def test_get_connection_client_error(self):
        """Test handling of client errors during connection retrieval."""
        mock_client = MagicMock()
        mock_client.connections.get.side_effect = Exception("Connection not found")
        
        service = FoundryService(client=mock_client)
        
        with pytest.raises(Exception):
            await service.get_connection("nonexistent")

    @pytest.mark.asyncio 
    async def test_list_model_deployments_credential_error(self):
        """Test handling of credential errors during deployment listing."""
        with patch.object(foundry_service_module, 'config', mock_config):
            # Mock config with broken credentials
            mock_config.get_azure_credentials.side_effect = Exception("Credential error")
            
            service = FoundryService()
            deployments = await service.list_model_deployments()
            assert deployments == []
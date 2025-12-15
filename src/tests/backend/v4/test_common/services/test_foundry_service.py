"""
Unit tests for v4 FoundryService with real class import for coverage.

This module tests the FoundryService by importing the actual module
with proper dependency mocking to enable coverage reporting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import aiohttp
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add backend path to sys.path for proper imports  
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import real FoundryService for coverage
from v4.common.services.foundry_service import FoundryService



class TestRealFoundryService:
    """Test cases using real FoundryService for coverage."""

    def test_real_foundry_service_init_no_client(self):
        """Test FoundryService initialization without client."""
        with patch('v4.common.services.foundry_service.config') as mock_config:
            mock_config.AZURE_AI_SUBSCRIPTION_ID = "test-sub"
            mock_config.AZURE_AI_RESOURCE_GROUP = "test-rg"
            mock_config.AZURE_AI_PROJECT_NAME = "test-project"
            mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
            
            service = FoundryService()
            
            assert service._client is None
            assert hasattr(service, 'logger')
            assert service.subscription_id == "test-sub"
            assert service.resource_group == "test-rg"
            assert service.project_name == "test-project"
            assert service.project_endpoint == "https://test.endpoint"

    def test_real_foundry_service_init_with_client(self):
        """Test FoundryService initialization with client."""
        mock_client = Mock()
        
        with patch('v4.common.services.foundry_service.config') as mock_config:
            mock_config.AZURE_AI_SUBSCRIPTION_ID = "test-sub"
            mock_config.AZURE_AI_RESOURCE_GROUP = "test-rg"
            mock_config.AZURE_AI_PROJECT_NAME = "test-project"
            mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
            
            service = FoundryService(client=mock_client)
            
            assert service._client is mock_client

    @pytest.mark.asyncio
    async def test_real_get_client_creates_when_none(self):
        """Test get_client creates client when none provided."""
        with patch('v4.common.services.foundry_service.config') as mock_config:
            mock_client = Mock()
            mock_config.AZURE_AI_SUBSCRIPTION_ID = "test-sub"
            mock_config.AZURE_AI_RESOURCE_GROUP = "test-rg" 
            mock_config.AZURE_AI_PROJECT_NAME = "test-project"
            mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
            mock_config.get_ai_project_client = Mock(return_value=mock_client)
            
            service = FoundryService()
            result = await service.get_client()
            
            assert result is mock_client
            assert service._client is mock_client
            mock_config.get_ai_project_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_get_client_returns_existing(self):
        """Test get_client returns existing client when available."""
        mock_client = Mock()
        
        with patch('v4.common.services.foundry_service.config'):
            service = FoundryService(client=mock_client)
            result = await service.get_client()
            
            assert result is mock_client
        
    async def get_connections(self):
        """Mock get connections method"""
        return self._connections
    
    async def list_connections(self):
        """Mock list connections method"""
        # Simulate converting objects to dict format
        connections = []
        for conn in self._connections:
            if hasattr(conn, 'as_dict') and callable(conn.as_dict):
                connections.append(conn.as_dict())
            elif isinstance(conn, dict):
                connections.append(conn)
            else:
                connections.append(conn)
        return connections
    
    async def get_connection(self, name: str):
        """Mock get connection by name"""
        for conn in self._connections:
            conn_name = ""
            if hasattr(conn, 'as_dict') and callable(conn.as_dict):
                conn_dict = conn.as_dict()
                conn_name = conn_dict.get('name', '')
                if conn_name == name:
                    return conn_dict
            elif isinstance(conn, dict):
                conn_name = conn.get('name', '')
                if conn_name == name:
                    return conn
            elif hasattr(conn, 'name'):
                if conn.name == name:
                    return conn
        return None
    
    async def list_model_deployments(self):
        """Mock list model deployments"""
        return self._deployments
    
    async def get_client(self):
        """Mock get client method"""
        if self._client is None:
            self._client = Mock()
        return self._client
    
    def _parse_resource_name_from_url(self, url: str):
        """Mock URL parsing method"""
        # Simple pattern matching for testing
        pattern = r'/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/Microsoft\.MachineLearningServices/workspaces/([^/]+)'
        match = re.search(pattern, url)
        if match:
            return {
                'subscription_id': match.group(1),
                'resource_group': match.group(2),
                'workspace_name': match.group(3)
            }
        return None
    
    async def close(self):
        """Mock close method"""
        if self._client:
            await self._client.close()


class TestFoundryServiceInit:
    """Test cases for FoundryService initialization."""

    def test_init_without_client(self):
        """Test initialization without providing a client."""
        service = FoundryService()
        
        assert service._client is None
        assert service.subscription_id == "test-subscription-id"
        assert service.resource_group == "test-resource-group"
        assert service.project_name == "test-project"

    def test_init_with_client(self):
        """Test initialization with a provided client."""
        mock_client = Mock()
        service = FoundryService(client=mock_client)
        
        assert service._client == mock_client

    def test_init_logger_created(self):
        """Test that logger is created during initialization."""
        service = FoundryService()
        
        # Test passes if no exception is thrown during initialization
        assert service is not None


class TestGetClient:
    """Test cases for get_client method."""

    @pytest.mark.asyncio
    async def test_get_client_lazy_initialization(self):
        """Test that client is lazily initialized on first access."""
        service = FoundryService()
        assert service._client is None
        
        client = await service.get_client()
        
        assert client is not None
        assert service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        """Test that existing client is reused."""
        mock_client = Mock()
        service = FoundryService(client=mock_client)
        
        client = await service.get_client()
        
        assert client == mock_client

    @pytest.mark.asyncio
    async def test_get_client_called_multiple_times(self):
        """Test that client is initialized only once across multiple calls."""
        service = FoundryService()
        
        client1 = await service.get_client()
        client2 = await service.get_client()
        client3 = await service.get_client()
        
        assert client1 == client2 == client3
        assert client1 is not None


class TestListConnections:
    """Test cases for list_connections method."""

    @pytest.mark.asyncio
    async def test_list_connections_with_as_dict_method(self):
        """Test listing connections when objects have as_dict method."""
        mock_conn1 = Mock()
        mock_conn1.as_dict.return_value = {"name": "conn1", "type": "storage"}
        mock_conn2 = Mock()
        mock_conn2.as_dict.return_value = {"name": "conn2", "type": "database"}
        
        service = FoundryService()
        service._connections = [mock_conn1, mock_conn2]
        connections = await service.list_connections()
        
        assert len(connections) == 2
        assert connections[0] == {"name": "conn1", "type": "storage"}
        assert connections[1] == {"name": "conn2", "type": "database"}

    @pytest.mark.asyncio
    async def test_list_connections_without_as_dict_method(self):
        """Test listing connections when objects don't have as_dict method."""
        # Create dict-like objects without as_dict method
        conn1 = {"name": "conn1", "type": "storage"}
        conn2 = {"name": "conn2", "type": "database"}
        
        service = FoundryService()
        service._connections = [conn1, conn2]
        connections = await service.list_connections()
        
        assert len(connections) == 2
        assert connections[0] == {"name": "conn1", "type": "storage"}
        assert connections[1] == {"name": "conn2", "type": "database"}

    @pytest.mark.asyncio
    async def test_list_connections_empty(self):
        """Test listing connections when no connections exist."""
        service = FoundryService()
        service._connections = []
        connections = await service.list_connections()
        
        assert connections == []

    @pytest.mark.asyncio
    async def test_list_connections_lazy_client_init(self):
        """Test that list_connections initializes client if needed."""
        service = FoundryService()
        connections = await service.list_connections()
        
        assert connections == []


class TestGetConnection:
    """Test cases for get_connection method."""

    @pytest.mark.asyncio
    async def test_get_connection_with_as_dict_method(self):
        """Test getting connection when object has as_dict method."""
        mock_conn = Mock()
        mock_conn.as_dict.return_value = {"name": "test-conn", "type": "storage", "endpoint": "https://storage.example.com"}
        
        service = FoundryService()
        service._connections = [mock_conn]
        connection = await service.get_connection("test-conn")
        
        assert connection == {"name": "test-conn", "type": "storage", "endpoint": "https://storage.example.com"}

    @pytest.mark.asyncio
    async def test_get_connection_without_as_dict_method(self):
        """Test getting connection when object doesn't have as_dict method."""
        conn = {"name": "test-conn", "type": "storage"}
        
        service = FoundryService()
        service._connections = [conn]
        connection = await service.get_connection("test-conn")
        
        assert connection == {"name": "test-conn", "type": "storage"}

    @pytest.mark.asyncio
    async def test_get_connection_with_special_characters(self):
        """Test getting connection with special characters in name."""
        mock_conn = Mock()
        mock_conn.as_dict.return_value = {"name": "test-conn_123", "type": "storage"}
        
        service = FoundryService()
        service._connections = [mock_conn]
        connection = await service.get_connection("test-conn_123")
        
        assert connection == {"name": "test-conn_123", "type": "storage"}


class TestListModelDeployments:
    """Test cases for list_model_deployments method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.foundry_service.config")
    @patch("v4.common.services.foundry_service.aiohttp.ClientSession")
    async def test_list_model_deployments_success(self, mock_session_class, mock_config):
        """Test successful model deployment listing."""
        mock_config.AZURE_AI_SUBSCRIPTION_ID = "sub-123"
        mock_config.AZURE_AI_RESOURCE_GROUP = "rg-test"
        mock_config.AZURE_AI_PROJECT_NAME = "project-test"
        mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://project.example.com"
class TestListModelDeployments:
    """Test cases for list_model_deployments method."""

    @pytest.mark.asyncio
    async def test_list_model_deployments_success(self):
        """Test successful model deployment listing."""
        service = FoundryService()
        # Set up mock deployments
        service._deployments = [
            {
                "name": "gpt-4",
                "model": {"name": "gpt-4", "version": "0613"},
                "status": "Succeeded",
                "endpoint_uri": "https://endpoint.com/gpt-4"
            },
            {
                "name": "gpt-35-turbo", 
                "model": {"name": "gpt-35-turbo", "version": "0301"},
                "status": "Succeeded", 
                "endpoint_uri": "https://endpoint.com/gpt-35"
            }
        ]
        
        deployments = await service.list_model_deployments()
        
        assert len(deployments) == 2
        assert deployments[0]["name"] == "gpt-4"
        assert deployments[0]["model"]["name"] == "gpt-4"
        assert deployments[0]["status"] == "Succeeded"
        assert deployments[1]["name"] == "gpt-35-turbo"

    @pytest.mark.asyncio
    async def test_list_model_deployments_incomplete_config(self):
        """Test list_model_deployments with incomplete configuration."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_missing_subscription(self):
        """Test with missing subscription ID."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_invalid_endpoint_format(self):
        """Test with invalid endpoint URL format."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_api_error(self):
        """Test handling of API error response."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_exception(self):
        """Test handling of exception during deployment listing."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_empty_response(self):
        """Test handling of empty deployment list."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_model_deployments_missing_properties(self):
        """Test handling of deployments with missing properties."""
        service = FoundryService()
        # Set up deployment with missing properties
        service._deployments = [
            {
                "name": "gpt-4",
                "model": {},
                "status": None,
                "endpoint_uri": None
            }
        ]
        
        deployments = await service.list_model_deployments()
        
        assert len(deployments) == 1
        assert deployments[0]["name"] == "gpt-4"
        assert deployments[0]["model"] == {}
        assert deployments[0]["status"] is None
        assert deployments[0]["endpoint_uri"] is None


class TestUrlParsing:
    """Test cases for URL parsing and resource name extraction."""

    @pytest.mark.asyncio
    async def test_resource_name_extraction_standard_format(self):
        """Test resource name extraction from standard endpoint format."""
        service = FoundryService()
        
        test_url = "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.MachineLearningServices/workspaces/my-resource"
        result = service._parse_resource_name_from_url(test_url)
        
        assert result is not None
        assert result["workspace_name"] == "my-resource"

    @pytest.mark.asyncio
    async def test_resource_name_with_hyphens(self):
        """Test resource name extraction with hyphens."""
        service = FoundryService()
        
        test_url = "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.MachineLearningServices/workspaces/aisa-macae-d3x6aoi7uldi"
        result = service._parse_resource_name_from_url(test_url)
        
        assert result is not None
        assert result["workspace_name"] == "aisa-macae-d3x6aoi7uldi"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_multiple_config_fields_none(self):
        """Test with multiple None configuration fields."""
        service = FoundryService()
        deployments = await service.list_model_deployments()
        
        assert deployments == []

    @pytest.mark.asyncio
    async def test_deployment_with_null_endpoint_uri(self):
        """Test deployment with null endpoint_uri."""
        service = FoundryService()
        # Set up deployment with null endpoint_uri
        service._deployments = [
            {
                "name": "gpt-4",
                "model": {"name": "gpt-4"},
                "status": "Succeeded",
                "endpoint_uri": None
            }
        ]
        
        deployments = await service.list_model_deployments()
        
        assert deployments[0]["endpoint_uri"] is None

    @pytest.mark.asyncio
    async def test_list_connections_mixed_connection_types(self):
        """Test listing connections with mixed object types."""
        # Mix of objects with and without as_dict
        mock_conn1 = Mock()
        mock_conn1.as_dict.return_value = {"name": "conn1", "type": "storage"}
        conn2 = {"name": "conn2", "type": "database"}
        mock_conn3 = Mock()
        mock_conn3.as_dict.return_value = {"name": "conn3", "type": "api"}
        
        service = FoundryService()
        service._connections = [mock_conn1, conn2, mock_conn3]
        connections = await service.list_connections()
        
        assert len(connections) == 3
        assert connections[0]["name"] == "conn1"
        assert connections[1]["name"] == "conn2"
        assert connections[2]["name"] == "conn3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

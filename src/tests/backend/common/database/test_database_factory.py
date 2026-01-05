"""Unit tests for DatabaseFactory."""

import logging
import sys
import os
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import pytest

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

# Set required environment variables for testing
os.environ.setdefault('APPLICATIONINSIGHTS_CONNECTION_STRING', 'test_connection_string')
os.environ.setdefault('APP_ENV', 'dev')
os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com/')
os.environ.setdefault('AZURE_OPENAI_API_KEY', 'test_key')
os.environ.setdefault('AZURE_OPENAI_DEPLOYMENT_NAME', 'test_deployment')
os.environ.setdefault('AZURE_AI_SUBSCRIPTION_ID', 'test_subscription_id')
os.environ.setdefault('AZURE_AI_RESOURCE_GROUP', 'test_resource_group')
os.environ.setdefault('AZURE_AI_PROJECT_NAME', 'test_project_name')
os.environ.setdefault('AZURE_AI_AGENT_ENDPOINT', 'https://test.agent.azure.com/')
os.environ.setdefault('COSMOSDB_ENDPOINT', 'https://test.documents.azure.com:443/')
os.environ.setdefault('COSMOSDB_DATABASE', 'test_database')
os.environ.setdefault('COSMOSDB_CONTAINER', 'test_container')
os.environ.setdefault('AZURE_CLIENT_ID', 'test_client_id')
os.environ.setdefault('AZURE_TENANT_ID', 'test_tenant_id')

# Only mock external problematic dependencies - do NOT mock internal common.* modules
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.projects'] = Mock()
sys.modules['azure.ai.projects.aio'] = Mock()
sys.modules['azure.ai.projects.models'] = Mock()
sys.modules['azure.ai.projects.models._models'] = Mock()
sys.modules['azure.cosmos'] = Mock()
sys.modules['azure.cosmos.aio'] = Mock()
sys.modules['azure.cosmos.aio._database'] = Mock()
sys.modules['azure.core'] = Mock()
sys.modules['azure.core.exceptions'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['azure.keyvault'] = Mock()
sys.modules['azure.keyvault.secrets'] = Mock()
sys.modules['azure.keyvault.secrets.aio'] = Mock()
# Mock v4 modules that may be imported by database components
sys.modules['v4'] = Mock()
sys.modules['v4.models'] = Mock()
sys.modules['v4.models.messages'] = Mock()

# Import the REAL modules using backend.* paths for proper coverage tracking
from backend.common.database.database_factory import DatabaseFactory
from backend.common.database.database_base import DatabaseBase
from backend.common.database.cosmosdb import CosmosDBClient


class TestDatabaseFactoryInitialization:
    """Test DatabaseFactory initialization and class structure."""
    
    def test_database_factory_class_attributes(self):
        """Test that DatabaseFactory has correct class attributes."""
        assert hasattr(DatabaseFactory, '_instance')
        assert hasattr(DatabaseFactory, '_logger')
        assert DatabaseFactory._instance is None  # Should start as None
        assert isinstance(DatabaseFactory._logger, logging.Logger)
    
    def test_database_factory_is_static(self):
        """Test that DatabaseFactory methods are static."""
        # Verify that key methods are static
        assert callable(getattr(DatabaseFactory, 'get_database'))
        assert callable(getattr(DatabaseFactory, 'close_all'))
        
        # Static methods should not require instance
        # We can't instantiate DatabaseFactory easily, but we can check method types
        get_database_method = getattr(DatabaseFactory, 'get_database')
        close_all_method = getattr(DatabaseFactory, 'close_all')
        
        # Static methods should be callable on the class
        assert get_database_method is not None
        assert close_all_method is not None
    
    def test_singleton_instance_management(self):
        """Test that singleton instance is properly managed."""
        # Reset instance to ensure clean state
        DatabaseFactory._instance = None
        assert DatabaseFactory._instance is None
        
        # Set a mock instance
        mock_instance = Mock(spec=DatabaseBase)
        DatabaseFactory._instance = mock_instance
        assert DatabaseFactory._instance is mock_instance
        
        # Reset for other tests
        DatabaseFactory._instance = None


class TestDatabaseFactoryGetDatabase:
    """Test DatabaseFactory get_database method."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance before each test
        DatabaseFactory._instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset singleton instance after each test
        DatabaseFactory._instance = None
    
    @pytest.mark.asyncio
    async def test_get_database_creates_new_instance_when_none_exists(self):
        """Test that get_database creates new instance when singleton is None."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database(user_id="test_user")
                
                # Verify CosmosDBClient was created with correct parameters
                mock_cosmos_class.assert_called_once_with(
                    endpoint="https://test.documents.azure.com:443/",
                    credential="mock_credentials",
                    database_name="test_db",
                    container_name="test_container",
                    session_id="",
                    user_id="test_user"
                )
                
                # Verify initialize was called
                mock_cosmos_client.initialize.assert_called_once()
                
                # Verify instance is returned and stored as singleton
                assert result is mock_cosmos_client
                assert DatabaseFactory._instance is mock_cosmos_client
    
    @pytest.mark.asyncio
    async def test_get_database_returns_existing_singleton_instance(self):
        """Test that get_database returns existing singleton instance."""
        # Set up existing singleton
        existing_instance = Mock(spec=DatabaseBase)
        DatabaseFactory._instance = existing_instance
        
        with patch('backend.common.database.database_factory.CosmosDBClient') as mock_cosmos_class:
            result = await DatabaseFactory.get_database(user_id="test_user")
            
            # Should not create new instance
            mock_cosmos_class.assert_not_called()
            
            # Should return existing instance
            assert result is existing_instance
            assert DatabaseFactory._instance is existing_instance
    
    @pytest.mark.asyncio
    async def test_get_database_force_new_creates_new_instance(self):
        """Test that get_database with force_new=True creates new instance."""
        # Set up existing singleton
        existing_instance = Mock(spec=DatabaseBase)
        DatabaseFactory._instance = existing_instance
        
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database(user_id="test_user", force_new=True)
                
                # Verify new CosmosDBClient was created
                mock_cosmos_class.assert_called_once_with(
                    endpoint="https://test.documents.azure.com:443/",
                    credential="mock_credentials",
                    database_name="test_db",
                    container_name="test_container",
                    session_id="",
                    user_id="test_user"
                )
                
                # Verify initialize was called
                mock_cosmos_client.initialize.assert_called_once()
                
                # Verify new instance is returned but singleton is not updated
                assert result is mock_cosmos_client
                assert DatabaseFactory._instance is existing_instance  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_get_database_with_empty_user_id(self):
        """Test that get_database works with empty user_id."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database()  # No user_id provided
                
                # Verify CosmosDBClient was created with empty user_id
                mock_cosmos_class.assert_called_once_with(
                    endpoint="https://test.documents.azure.com:443/",
                    credential="mock_credentials",
                    database_name="test_db",
                    container_name="test_container",
                    session_id="",
                    user_id=""
                )
                
                assert result is mock_cosmos_client
    
    @pytest.mark.asyncio
    async def test_get_database_initialization_error(self):
        """Test that get_database handles initialization errors properly."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock(side_effect=Exception("Initialization failed"))
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client):
            with patch('backend.common.database.database_factory.config', mock_config):
                with pytest.raises(Exception, match="Initialization failed"):
                    await DatabaseFactory.get_database(user_id="test_user")
                
                # Singleton should remain None after failure
                assert DatabaseFactory._instance is None


class TestDatabaseFactoryCloseAll:
    """Test DatabaseFactory close_all method."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance before each test
        DatabaseFactory._instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset singleton instance after each test
        DatabaseFactory._instance = None
    
    @pytest.mark.asyncio
    async def test_close_all_with_existing_instance(self):
        """Test that close_all properly closes existing instance."""
        # Set up mock instance
        mock_instance = Mock(spec=DatabaseBase)
        mock_instance.close = AsyncMock()
        DatabaseFactory._instance = mock_instance
        
        await DatabaseFactory.close_all()
        
        # Verify close was called
        mock_instance.close.assert_called_once()
        
        # Verify singleton is reset to None
        assert DatabaseFactory._instance is None
    
    @pytest.mark.asyncio
    async def test_close_all_with_no_instance(self):
        """Test that close_all handles case when no instance exists."""
        # Ensure no instance exists
        DatabaseFactory._instance = None
        
        # Should not raise exception
        await DatabaseFactory.close_all()
        
        # Should remain None
        assert DatabaseFactory._instance is None
    
    @pytest.mark.asyncio
    async def test_close_all_handles_close_exception(self):
        """Test that close_all handles exceptions during close."""
        # Set up mock instance that raises exception on close
        mock_instance = Mock(spec=DatabaseBase)
        mock_instance.close = AsyncMock(side_effect=Exception("Close failed"))
        DatabaseFactory._instance = mock_instance
        
        # Should propagate the exception
        with pytest.raises(Exception, match="Close failed"):
            await DatabaseFactory.close_all()
        
        # With exception, singleton may not be reset (depends on implementation)
        # The current implementation doesn't use try-except, so the exception
        # would prevent the _instance = None assignment
        assert DatabaseFactory._instance is mock_instance


class TestDatabaseFactoryIntegration:
    """Test DatabaseFactory integration scenarios."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance before each test
        DatabaseFactory._instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset singleton instance after each test
        DatabaseFactory._instance = None
    
    @pytest.mark.asyncio
    async def test_multiple_get_database_calls_return_same_instance(self):
        """Test that multiple calls to get_database return the same instance."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                # First call
                result1 = await DatabaseFactory.get_database(user_id="user1")
                
                # Second call
                result2 = await DatabaseFactory.get_database(user_id="user2")
                
                # Should only create one instance
                mock_cosmos_class.assert_called_once()
                
                # Both calls should return the same instance
                assert result1 is result2
                assert result1 is mock_cosmos_client
    
    @pytest.mark.asyncio
    async def test_get_database_after_close_all(self):
        """Test that get_database works properly after close_all."""
        # First, create an instance
        mock_cosmos_client1 = Mock(spec=CosmosDBClient)
        mock_cosmos_client1.initialize = AsyncMock()
        mock_cosmos_client1.close = AsyncMock()
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client1):
                result1 = await DatabaseFactory.get_database(user_id="test_user")
                assert result1 is mock_cosmos_client1
                assert DatabaseFactory._instance is mock_cosmos_client1
        
        # Close all connections
        await DatabaseFactory.close_all()
        assert DatabaseFactory._instance is None
        
        # Create a new instance
        mock_cosmos_client2 = Mock(spec=CosmosDBClient)
        mock_cosmos_client2.initialize = AsyncMock()
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client2):
                result2 = await DatabaseFactory.get_database(user_id="test_user")
                
                # Should create new instance
                assert result2 is mock_cosmos_client2
                assert DatabaseFactory._instance is mock_cosmos_client2
                assert result2 is not result1
    
    @pytest.mark.asyncio
    async def test_force_new_does_not_affect_singleton(self):
        """Test that force_new instances don't interfere with singleton."""
        mock_cosmos_client1 = Mock(spec=CosmosDBClient)
        mock_cosmos_client1.initialize = AsyncMock()
        
        mock_cosmos_client2 = Mock(spec=CosmosDBClient) 
        mock_cosmos_client2.initialize = AsyncMock()
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.config', mock_config):
            # Create singleton instance
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client1):
                singleton = await DatabaseFactory.get_database(user_id="user1")
                assert DatabaseFactory._instance is mock_cosmos_client1
            
            # Create force_new instance
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client2):
                force_new = await DatabaseFactory.get_database(user_id="user2", force_new=True)
                
                # force_new should return new instance
                assert force_new is mock_cosmos_client2
                
                # But singleton should remain unchanged
                assert DatabaseFactory._instance is mock_cosmos_client1
                assert singleton is not force_new
            
            # Subsequent call should still return singleton
            result = await DatabaseFactory.get_database(user_id="user3")
            assert result is mock_cosmos_client1


class TestDatabaseFactoryConfigurationHandling:
    """Test DatabaseFactory configuration handling."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton instance before each test
        DatabaseFactory._instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset singleton instance after each test
        DatabaseFactory._instance = None
    
    @pytest.mark.asyncio
    async def test_config_values_passed_correctly(self):
        """Test that configuration values are passed correctly to CosmosDBClient."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        
        mock_credentials = Mock()
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://custom.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "custom_database"
        mock_config.COSMOSDB_CONTAINER = "custom_container"
        mock_config.get_azure_credentials.return_value = mock_credentials
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                await DatabaseFactory.get_database(user_id="custom_user")
                
                # Verify all config values were passed correctly
                mock_cosmos_class.assert_called_once_with(
                    endpoint="https://custom.documents.azure.com:443/",
                    credential=mock_credentials,
                    database_name="custom_database",
                    container_name="custom_container",
                    session_id="",
                    user_id="custom_user"
                )
                
                # Verify get_azure_credentials was called
                mock_config.get_azure_credentials.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_config_credential_error(self):
        """Test handling of config credential errors."""
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.side_effect = Exception("Credential error")
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with pytest.raises(Exception, match="Credential error"):
                await DatabaseFactory.get_database(user_id="test_user")
            
            # Singleton should remain None after credential error
            assert DatabaseFactory._instance is None


class TestDatabaseFactoryLogging:
    """Test DatabaseFactory logging functionality."""
    
    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        logger = DatabaseFactory._logger
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'backend.common.database.database_factory'
    
    def test_logger_is_class_attribute(self):
        """Test that logger is a class attribute and consistent."""
        logger1 = DatabaseFactory._logger
        logger2 = DatabaseFactory._logger
        assert logger1 is logger2
        assert isinstance(logger1, logging.Logger)


class TestDatabaseFactoryErrorHandling:
    """Test DatabaseFactory error handling scenarios."""
    
    def setup_method(self):
        """Setup for each test method."""
        DatabaseFactory._instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        DatabaseFactory._instance = None
    
    @pytest.mark.asyncio
    async def test_cosmos_client_creation_failure(self):
        """Test handling of CosmosDBClient creation failure."""
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', side_effect=Exception("Client creation failed")):
            with patch('backend.common.database.database_factory.config', mock_config):
                with pytest.raises(Exception, match="Client creation failed"):
                    await DatabaseFactory.get_database(user_id="test_user")
                
                # Singleton should remain None
                assert DatabaseFactory._instance is None
    
    @pytest.mark.asyncio
    async def test_state_consistency_after_errors(self):
        """Test that factory state remains consistent after various errors."""
        # Start with clean state
        assert DatabaseFactory._instance is None
        
        # Simulate creation failure
        mock_config = Mock()
        mock_config.get_azure_credentials.side_effect = Exception("Config error")
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with pytest.raises(Exception):
                await DatabaseFactory.get_database()
        
        # State should remain clean
        assert DatabaseFactory._instance is None
        
        # Now create successful instance
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        
        good_config = Mock()
        good_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        good_config.COSMOSDB_DATABASE = "test_db"
        good_config.COSMOSDB_CONTAINER = "test_container"
        good_config.get_azure_credentials.return_value = "credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client):
            with patch('backend.common.database.database_factory.config', good_config):
                result = await DatabaseFactory.get_database()
                assert result is mock_cosmos_client
                assert DatabaseFactory._instance is mock_cosmos_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

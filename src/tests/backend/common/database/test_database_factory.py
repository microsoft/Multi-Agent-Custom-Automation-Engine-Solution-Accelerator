"""Unit tests for DatabaseFactory."""

import logging
import sys
import os
from unittest.mock import AsyncMock, Mock, patch
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

# Import the REAL modules using backend.* paths for proper coverage tracking
from backend.common.database.database_factory import DatabaseFactory
from backend.common.database.database_base import DatabaseBase
from backend.common.database.cosmosdb import CosmosDBClient


class TestDatabaseFactoryInitialization:
    """Test DatabaseFactory initialization and class structure."""
    
    def test_database_factory_class_attributes(self):
        """Test that DatabaseFactory has correct class attributes."""
        assert hasattr(DatabaseFactory, '_shared_instance')
        assert hasattr(DatabaseFactory, '_logger')
        assert DatabaseFactory._shared_instance is None  # Should start as None
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
    
    def test_shared_instance_management(self):
        """Test that shared instance is properly managed."""
        # Reset instance to ensure clean state
        DatabaseFactory._shared_instance = None
        assert DatabaseFactory._shared_instance is None
        
        # Set a mock instance
        mock_instance = Mock(spec=DatabaseBase)
        DatabaseFactory._shared_instance = mock_instance
        assert DatabaseFactory._shared_instance is mock_instance
        
        # Reset for other tests
        DatabaseFactory._shared_instance = None


class TestDatabaseFactoryGetDatabase:
    """Test DatabaseFactory get_database method."""
    
    def setup_method(self):
        """Setup for each test method."""
        DatabaseFactory._shared_instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        DatabaseFactory._shared_instance = None
    
    @pytest.mark.asyncio
    async def test_get_database_creates_shared_instance_when_none_exists(self):
        """Test that get_database initializes the shared connection when none exists."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        mock_cosmos_client.client = Mock()
        mock_cosmos_client.database = Mock()
        mock_cosmos_client.container = Mock()
        mock_cosmos_client._initialized = True
        mock_cosmos_client.user_id = "test_user"
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database(user_id="test_user")
                
                # Verify initialize was called on the shared instance
                mock_cosmos_client.initialize.assert_called_once()
                
                # Shared instance should be cached
                assert DatabaseFactory._shared_instance is mock_cosmos_client
                
                # Result should have the correct user_id
                assert result.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_get_database_returns_per_request_instance_with_correct_user_id(self):
        """Test that each get_database call returns an instance scoped to the caller's user_id."""
        mock_shared = Mock(spec=CosmosDBClient)
        mock_shared.initialize = AsyncMock()
        mock_shared.client = Mock()
        mock_shared.database = Mock()
        mock_shared.container = Mock()
        mock_shared._initialized = True
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        # Pre-set shared instance to simulate already-initialized state
        DatabaseFactory._shared_instance = mock_shared
        
        with patch('backend.common.database.database_factory.CosmosDBClient') as mock_cosmos_class:
            # Make constructor return a real-enough mock with settable attributes
            mock_per_request = Mock(spec=CosmosDBClient)
            mock_per_request.user_id = "user_a"
            mock_cosmos_class.return_value = mock_per_request
            
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database(user_id="user_a")
                
                # Per-request instance should share the connection from the shared instance
                assert result.client is mock_shared.client
                assert result.database is mock_shared.database
                assert result.container is mock_shared.container
    
    @pytest.mark.asyncio
    async def test_get_database_different_users_get_different_instances(self):
        """Test that different user_ids produce distinct instances."""
        mock_shared = Mock(spec=CosmosDBClient)
        mock_shared.client = Mock()
        mock_shared.database = Mock()
        mock_shared.container = Mock()
        mock_shared._initialized = True
        DatabaseFactory._shared_instance = mock_shared
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient') as mock_cosmos_class:
            def make_instance(**kwargs):
                inst = Mock(spec=CosmosDBClient)
                inst.user_id = kwargs.get('user_id', '')
                return inst
            mock_cosmos_class.side_effect = make_instance
            
            with patch('backend.common.database.database_factory.config', mock_config):
                result1 = await DatabaseFactory.get_database(user_id="user_a")
                result2 = await DatabaseFactory.get_database(user_id="user_b")
                
                # Should be different instances
                assert result1 is not result2
                assert result1.user_id == "user_a"
                assert result2.user_id == "user_b"
    
    @pytest.mark.asyncio
    async def test_get_database_force_new_reinitializes_shared_connection(self):
        """Test that force_new=True re-creates the shared connection."""
        old_shared = Mock(spec=CosmosDBClient)
        old_shared.client = Mock()
        old_shared.database = Mock()
        old_shared.container = Mock()
        DatabaseFactory._shared_instance = old_shared
        
        new_shared = Mock(spec=CosmosDBClient)
        new_shared.initialize = AsyncMock()
        new_shared.client = Mock()
        new_shared.database = Mock()
        new_shared.container = Mock()
        new_shared._initialized = True
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        call_count = [0]
        def make_instance(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return new_shared
            inst = Mock(spec=CosmosDBClient)
            inst.user_id = kwargs.get('user_id', '')
            return inst
        
        with patch('backend.common.database.database_factory.CosmosDBClient', side_effect=make_instance):
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database(user_id="test_user", force_new=True)
                
                # Shared instance should be replaced
                assert DatabaseFactory._shared_instance is new_shared
                new_shared.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_database_with_empty_user_id(self):
        """Test that get_database works with empty user_id."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        mock_cosmos_client.client = Mock()
        mock_cosmos_client.database = Mock()
        mock_cosmos_client.container = Mock()
        mock_cosmos_client._initialized = True
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                result = await DatabaseFactory.get_database()  # No user_id provided
                
                # Should still work; per-request instance created with empty user_id
                assert result is not None
    
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
                
                # Shared instance should remain None after failure
                assert DatabaseFactory._shared_instance is None


class TestDatabaseFactoryCloseAll:
    """Test DatabaseFactory close_all method."""
    
    def setup_method(self):
        """Setup for each test method."""
        DatabaseFactory._shared_instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        DatabaseFactory._shared_instance = None
    
    @pytest.mark.asyncio
    async def test_close_all_with_existing_instance(self):
        """Test that close_all properly closes existing shared instance."""
        mock_instance = Mock(spec=DatabaseBase)
        mock_instance.close = AsyncMock()
        DatabaseFactory._shared_instance = mock_instance
        
        await DatabaseFactory.close_all()
        
        # Verify close was called
        mock_instance.close.assert_called_once()
        
        # Verify shared instance is reset to None
        assert DatabaseFactory._shared_instance is None
    
    @pytest.mark.asyncio
    async def test_close_all_with_no_instance(self):
        """Test that close_all handles case when no instance exists."""
        DatabaseFactory._shared_instance = None
        
        # Should not raise exception
        await DatabaseFactory.close_all()
        
        # Should remain None
        assert DatabaseFactory._shared_instance is None
    
    @pytest.mark.asyncio
    async def test_close_all_handles_close_exception(self):
        """Test that close_all handles exceptions during close."""
        mock_instance = Mock(spec=DatabaseBase)
        mock_instance.close = AsyncMock(side_effect=Exception("Close failed"))
        DatabaseFactory._shared_instance = mock_instance
        
        # Should propagate the exception
        with pytest.raises(Exception, match="Close failed"):
            await DatabaseFactory.close_all()
        
        # With exception, shared instance may not be reset (depends on implementation)
        # The current implementation doesn't use try-except, so the exception
        # would prevent the _shared_instance = None assignment
        assert DatabaseFactory._shared_instance is mock_instance


class TestDatabaseFactoryIntegration:
    """Test DatabaseFactory integration scenarios."""
    
    def setup_method(self):
        """Setup for each test method."""
        DatabaseFactory._shared_instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        DatabaseFactory._shared_instance = None
    
    @pytest.mark.asyncio
    async def test_multiple_get_database_calls_return_different_user_scoped_instances(self):
        """Test that multiple calls with different user_ids return separate instances."""
        mock_shared = Mock(spec=CosmosDBClient)
        mock_shared.initialize = AsyncMock()
        mock_shared.client = Mock()
        mock_shared.database = Mock()
        mock_shared.container = Mock()
        mock_shared._initialized = True
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        call_count = [0]
        def make_instance(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call creates the shared instance
                return mock_shared
            inst = Mock(spec=CosmosDBClient)
            inst.user_id = kwargs.get('user_id', '')
            return inst
        
        with patch('backend.common.database.database_factory.CosmosDBClient', side_effect=make_instance):
            with patch('backend.common.database.database_factory.config', mock_config):
                result1 = await DatabaseFactory.get_database(user_id="user1")
                result2 = await DatabaseFactory.get_database(user_id="user2")
                
                # Different user_ids should yield different instances
                assert result1 is not result2
                # Both share the same underlying connection
                assert result1.client is mock_shared.client
                assert result2.client is mock_shared.client
    
    @pytest.mark.asyncio
    async def test_get_database_after_close_all(self):
        """Test that get_database works properly after close_all."""
        mock_cosmos_client1 = Mock(spec=CosmosDBClient)
        mock_cosmos_client1.initialize = AsyncMock()
        mock_cosmos_client1.close = AsyncMock()
        mock_cosmos_client1.client = Mock()
        mock_cosmos_client1.database = Mock()
        mock_cosmos_client1.container = Mock()
        mock_cosmos_client1._initialized = True
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client1):
                result1 = await DatabaseFactory.get_database(user_id="test_user")
                assert DatabaseFactory._shared_instance is mock_cosmos_client1
        
        # Close all connections
        await DatabaseFactory.close_all()
        assert DatabaseFactory._shared_instance is None
        
        # Create a new instance
        mock_cosmos_client2 = Mock(spec=CosmosDBClient)
        mock_cosmos_client2.initialize = AsyncMock()
        mock_cosmos_client2.client = Mock()
        mock_cosmos_client2.database = Mock()
        mock_cosmos_client2.container = Mock()
        mock_cosmos_client2._initialized = True
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client2):
                result2 = await DatabaseFactory.get_database(user_id="test_user")
                
                # Should create new shared instance
                assert DatabaseFactory._shared_instance is mock_cosmos_client2
    
    @pytest.mark.asyncio
    async def test_force_new_replaces_shared_instance(self):
        """Test that force_new replaces the shared connection instance."""
        mock_cosmos_client1 = Mock(spec=CosmosDBClient)
        mock_cosmos_client1.initialize = AsyncMock()
        mock_cosmos_client1.client = Mock()
        mock_cosmos_client1.database = Mock()
        mock_cosmos_client1.container = Mock()
        mock_cosmos_client1._initialized = True
        
        mock_cosmos_client2 = Mock(spec=CosmosDBClient)
        mock_cosmos_client2.initialize = AsyncMock()
        mock_cosmos_client2.client = Mock()
        mock_cosmos_client2.database = Mock()
        mock_cosmos_client2.container = Mock()
        mock_cosmos_client2._initialized = True
        
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "test_db"
        mock_config.COSMOSDB_CONTAINER = "test_container"
        mock_config.get_azure_credentials.return_value = "mock_credentials"
        
        with patch('backend.common.database.database_factory.config', mock_config):
            # Create initial shared instance
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client1):
                await DatabaseFactory.get_database(user_id="user1")
                assert DatabaseFactory._shared_instance is mock_cosmos_client1
            
            # force_new should replace the shared instance
            with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client2):
                await DatabaseFactory.get_database(user_id="user2", force_new=True)
                assert DatabaseFactory._shared_instance is mock_cosmos_client2


class TestDatabaseFactoryConfigurationHandling:
    """Test DatabaseFactory configuration handling."""
    
    def setup_method(self):
        """Setup for each test method."""
        DatabaseFactory._shared_instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        DatabaseFactory._shared_instance = None
    
    @pytest.mark.asyncio
    async def test_config_values_passed_correctly(self):
        """Test that configuration values are passed correctly to CosmosDBClient."""
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        mock_cosmos_client.client = Mock()
        mock_cosmos_client.database = Mock()
        mock_cosmos_client.container = Mock()
        
        mock_credentials = Mock()
        mock_config = Mock()
        mock_config.COSMOSDB_ENDPOINT = "https://custom.documents.azure.com:443/"
        mock_config.COSMOSDB_DATABASE = "custom_database"
        mock_config.COSMOSDB_CONTAINER = "custom_container"
        mock_config.get_azure_credentials.return_value = mock_credentials
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client) as mock_cosmos_class:
            with patch('backend.common.database.database_factory.config', mock_config):
                await DatabaseFactory.get_database(user_id="custom_user")
                
                # get_database builds a shared instance and a per-request
                # instance, so the client is constructed twice with the same
                # config-derived arguments.
                assert mock_cosmos_class.call_count == 2
                mock_cosmos_class.assert_called_with(
                    endpoint="https://custom.documents.azure.com:443/",
                    credential=mock_credentials,
                    database_name="custom_database",
                    container_name="custom_container",
                    session_id="",
                    user_id="custom_user"
                )
                
                # Verify get_azure_credentials was invoked for each construction
                assert mock_config.get_azure_credentials.call_count == 2
    
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
            
            # Shared instance should remain None after credential error
            assert DatabaseFactory._shared_instance is None


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
        DatabaseFactory._shared_instance = None
    
    def teardown_method(self):
        """Cleanup after each test method."""
        DatabaseFactory._shared_instance = None
    
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
                
                # Shared instance should remain None
                assert DatabaseFactory._shared_instance is None
    
    @pytest.mark.asyncio
    async def test_state_consistency_after_errors(self):
        """Test that factory state remains consistent after various errors."""
        # Start with clean state
        assert DatabaseFactory._shared_instance is None
        
        # Simulate creation failure
        mock_config = Mock()
        mock_config.get_azure_credentials.side_effect = Exception("Config error")
        
        with patch('backend.common.database.database_factory.config', mock_config):
            with pytest.raises(Exception):
                await DatabaseFactory.get_database()
        
        # State should remain clean
        assert DatabaseFactory._shared_instance is None
        
        # Now create successful instance
        mock_cosmos_client = Mock(spec=CosmosDBClient)
        mock_cosmos_client.initialize = AsyncMock()
        mock_cosmos_client.client = Mock()
        mock_cosmos_client.database = Mock()
        mock_cosmos_client.container = Mock()
        mock_cosmos_client._initialized = True
        
        good_config = Mock()
        good_config.COSMOSDB_ENDPOINT = "https://test.documents.azure.com:443/"
        good_config.COSMOSDB_DATABASE = "test_db"
        good_config.COSMOSDB_CONTAINER = "test_container"
        good_config.get_azure_credentials.return_value = "credentials"
        
        with patch('backend.common.database.database_factory.CosmosDBClient', return_value=mock_cosmos_client):
            with patch('backend.common.database.database_factory.config', good_config):
                result = await DatabaseFactory.get_database()
                assert DatabaseFactory._shared_instance is mock_cosmos_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
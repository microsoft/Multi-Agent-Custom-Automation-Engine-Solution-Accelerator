"""
Comprehensive unit tests for app_config.py module.

This module contains extensive test coverage for:
- AppConfig class initialization
- Environment variable loading and validation
- Credential management
- Client creation methods
- Configuration getter and setter methods
"""

import pytest
import os
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.cosmos import CosmosClient
from azure.ai.projects.aio import AIProjectClient

# Add the backend directory to the Python path for imports
import sys
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend')
backend_path = os.path.abspath(backend_path)
sys.path.insert(0, backend_path)

# Set minimal environment variables before importing to avoid global instance creation error
os.environ.setdefault("APPLICATIONINSIGHTS_CONNECTION_STRING", "test_connection_string")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT_NAME", "test-gpt-4o")
os.environ.setdefault("AZURE_OPENAI_RAI_DEPLOYMENT_NAME", "test-gpt-4.1")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-11-20")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
os.environ.setdefault("AZURE_AI_SUBSCRIPTION_ID", "test-subscription-id")
os.environ.setdefault("AZURE_AI_RESOURCE_GROUP", "test-resource-group")
os.environ.setdefault("AZURE_AI_PROJECT_NAME", "test-project")
os.environ.setdefault("AZURE_AI_AGENT_ENDPOINT", "https://test.ai.azure.com")

# Import the class to test
try:
    from common.config.app_config import AppConfig
except ImportError:
    # Fallback for pytest execution
    import importlib.util
    app_config_path = os.path.join(backend_path, 'common', 'config', 'app_config.py')
    spec = importlib.util.spec_from_file_location("app_config", app_config_path)
    app_config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_config_module)
    AppConfig = app_config_module.AppConfig


class TestAppConfigInitialization:
    """Test cases for AppConfig class initialization and environment variable loading."""

    @patch.dict(os.environ, {}, clear=True)
    def test_initialization_with_minimal_env_vars(self):
        """Test AppConfig initialization with minimal required environment variables."""
        # Set only the absolutely required environment variables
        test_env = {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "test",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com"
        }
        
        with patch.dict(os.environ, test_env):
            config = AppConfig()
            
            # Test required variables are set correctly
            assert config.APPLICATIONINSIGHTS_CONNECTION_STRING == "test_connection_string"
            assert config.APP_ENV == "test"
            assert config.AZURE_OPENAI_DEPLOYMENT_NAME == "test-gpt-4o"
            assert config.AZURE_OPENAI_ENDPOINT == "https://test.openai.azure.com"
            assert config.AZURE_AI_SUBSCRIPTION_ID == "test-subscription-id"
            
            # Test optional variables have default values
            assert config.AZURE_TENANT_ID == ""
            assert config.AZURE_CLIENT_ID == ""
            assert config.COSMOSDB_ENDPOINT == ""

    @patch.dict(os.environ, {}, clear=True)
    def test_initialization_with_all_env_vars(self):
        """Test AppConfig initialization with all environment variables set."""
        test_env = {
            "AZURE_TENANT_ID": "test-tenant-id",
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-client-secret",
            "COSMOSDB_ENDPOINT": "https://test.cosmosdb.azure.com",
            "COSMOSDB_DATABASE": "test-database",
            "COSMOSDB_CONTAINER": "test-container",
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "prod",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "custom-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "custom-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://custom.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "custom-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "custom-resource-group",
            "AZURE_AI_PROJECT_NAME": "custom-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://custom.ai.azure.com",
            "FRONTEND_SITE_NAME": "https://custom.frontend.com",
            "MCP_SERVER_ENDPOINT": "http://custom.mcp.server:8000/mcp",
            "TEST_TEAM_JSON": "custom_team"
        }
        
        with patch.dict(os.environ, test_env):
            config = AppConfig()
            
            # Test all variables are set correctly
            assert config.AZURE_TENANT_ID == "test-tenant-id"
            assert config.AZURE_CLIENT_ID == "test-client-id"
            assert config.COSMOSDB_ENDPOINT == "https://test.cosmosdb.azure.com"
            assert config.APP_ENV == "prod"
            assert config.FRONTEND_SITE_NAME == "https://custom.frontend.com"
            assert config.MCP_SERVER_ENDPOINT == "http://custom.mcp.server:8000/mcp"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_variable_raises_error(self):
        """Test that missing required environment variables raise ValueError."""
        # Missing APPLICATIONINSIGHTS_CONNECTION_STRING
        incomplete_env = {
            "APP_ENV": "test",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com"
        }
        
        with patch.dict(os.environ, incomplete_env):
            with pytest.raises(ValueError, match="Environment variable APPLICATIONINSIGHTS_CONNECTION_STRING not found"):
                AppConfig()

    def test_logger_initialization(self):
        """Test that logger is properly initialized."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            assert hasattr(config, 'logger')
            assert isinstance(config.logger, logging.Logger)
            assert config.logger.name == "common.config.app_config"

    def _get_minimal_env(self):
        """Helper method to get minimal required environment variables."""
        return {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "test",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com"
        }


class TestAppConfigPrivateMethods:
    """Test cases for private methods in AppConfig class."""

    def setUp(self):
        """Set up test fixtures."""
        with patch.dict(os.environ, self._get_minimal_env()):
            self.config = AppConfig()

    def _get_minimal_env(self):
        """Helper method to get minimal required environment variables."""
        return {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "test",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com"
        }

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_get_required_with_existing_variable(self):
        """Test _get_required method with existing environment variable."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config._get_required("TEST_VAR")
            assert result == "test_value"

    def test_get_required_with_default_value(self):
        """Test _get_required method with default value when variable doesn't exist."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config._get_required("NON_EXISTENT_VAR", "default_value")
            assert result == "default_value"

    def test_get_required_without_default_raises_error(self):
        """Test _get_required method raises ValueError when variable doesn't exist and no default."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            with pytest.raises(ValueError, match="Environment variable NON_EXISTENT_VAR not found"):
                config._get_required("NON_EXISTENT_VAR")

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_get_optional_with_existing_variable(self):
        """Test _get_optional method with existing environment variable."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config._get_optional("TEST_VAR")
            assert result == "test_value"

    def test_get_optional_with_default_value(self):
        """Test _get_optional method with default value when variable doesn't exist."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config._get_optional("NON_EXISTENT_VAR", "default_value")
            assert result == "default_value"

    def test_get_optional_without_default_returns_empty_string(self):
        """Test _get_optional method returns empty string when variable doesn't exist and no default."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config._get_optional("NON_EXISTENT_VAR")
            assert result == ""

    @patch.dict(os.environ, {"BOOL_TRUE": "true", "BOOL_FALSE": "false", "BOOL_1": "1", "BOOL_0": "0"})
    def test_get_bool_method(self):
        """Test _get_bool method with various boolean values."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            assert config._get_bool("BOOL_TRUE") is True
            assert config._get_bool("BOOL_1") is True
            assert config._get_bool("BOOL_FALSE") is False
            assert config._get_bool("BOOL_0") is False
            assert config._get_bool("NON_EXISTENT_VAR") is False


class TestAppConfigCredentials:
    """Test cases for credential management methods in AppConfig class."""

    def _get_minimal_env(self):
        """Helper method to get minimal required environment variables."""
        return {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "dev",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com"
        }

    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_azure_credential_dev_environment(self, mock_default_credential):
        """Test get_azure_credential method in dev environment."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config.get_azure_credential()
            
            mock_default_credential.assert_called_once()
            assert result == mock_credential

    @patch('common.config.app_config.ManagedIdentityCredential')
    def test_get_azure_credential_prod_environment(self, mock_managed_credential):
        """Test get_azure_credential method in production environment."""
        mock_credential = MagicMock()
        mock_managed_credential.return_value = mock_credential
        
        env = self._get_minimal_env()
        env["APP_ENV"] = "prod"
        env["AZURE_CLIENT_ID"] = "test-client-id"
        
        with patch.dict(os.environ, env):
            config = AppConfig()
            result = config.get_azure_credential("test-client-id")
            
            mock_managed_credential.assert_called_once_with(client_id="test-client-id")
            assert result == mock_credential

    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_azure_credentials_caching(self, mock_default_credential):
        """Test that get_azure_credentials caches the credential."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            # First call
            result1 = config.get_azure_credentials()
            
            # Second call should return cached credential
            result2 = config.get_azure_credentials()
            
            mock_default_credential.assert_called_once()
            assert result1 == result2 == mock_credential

    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_access_token_success(self, mock_default_credential):
        """Test successful access token retrieval."""
        mock_token = MagicMock()
        mock_token.token = "test-access-token"
        
        mock_credential = MagicMock()
        mock_credential.get_token.return_value = mock_token
        mock_default_credential.return_value = mock_credential
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            # Test the sync version by calling the credential directly
            credential = config.get_azure_credentials()
            token = credential.get_token(config.AZURE_COGNITIVE_SERVICES)
            
            assert token.token == "test-access-token"
            mock_credential.get_token.assert_called_once_with(config.AZURE_COGNITIVE_SERVICES)

    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_access_token_failure(self, mock_default_credential):
        """Test access token retrieval failure."""
        mock_credential = MagicMock()
        mock_credential.get_token.side_effect = Exception("Token retrieval failed")
        mock_default_credential.return_value = mock_credential
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            # Test the sync version by calling the credential directly
            credential = config.get_azure_credentials()
            
            with pytest.raises(Exception, match="Token retrieval failed"):
                credential.get_token(config.AZURE_COGNITIVE_SERVICES)


class TestAppConfigClientMethods:
    """Test cases for client creation methods in AppConfig class."""

    def _get_minimal_env(self):
        """Helper method to get minimal required environment variables."""
        return {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "dev",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com",
            "COSMOSDB_ENDPOINT": "https://test.cosmosdb.azure.com",
            "COSMOSDB_DATABASE": "test-database"
        }

    @patch('common.config.app_config.CosmosClient')
    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_cosmos_database_client_success(self, mock_default_credential, mock_cosmos_client):
        """Test successful Cosmos DB client creation."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        mock_cosmos_instance = MagicMock()
        mock_database_client = MagicMock()
        mock_cosmos_instance.get_database_client.return_value = mock_database_client
        mock_cosmos_client.return_value = mock_cosmos_instance
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            result = config.get_cosmos_database_client()
            
            mock_cosmos_client.assert_called_once_with(
                "https://test.cosmosdb.azure.com",
                credential=mock_credential
            )
            mock_cosmos_instance.get_database_client.assert_called_once_with("test-database")
            assert result == mock_database_client

    @patch('common.config.app_config.CosmosClient')
    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_cosmos_database_client_caching(self, mock_default_credential, mock_cosmos_client):
        """Test that Cosmos DB client is cached."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        mock_cosmos_instance = MagicMock()
        mock_database_client = MagicMock()
        mock_cosmos_instance.get_database_client.return_value = mock_database_client
        mock_cosmos_client.return_value = mock_cosmos_instance
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            # First call
            result1 = config.get_cosmos_database_client()
            
            # Second call should use cached clients
            result2 = config.get_cosmos_database_client()
            
            # Cosmos client should only be created once
            mock_cosmos_client.assert_called_once()
            mock_cosmos_instance.get_database_client.assert_called_once()
            assert result1 == result2 == mock_database_client

    @patch('common.config.app_config.CosmosClient')
    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_cosmos_database_client_failure(self, mock_default_credential, mock_cosmos_client):
        """Test Cosmos DB client creation failure."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        mock_cosmos_client.side_effect = Exception("Cosmos connection failed")
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            with patch('logging.error') as mock_logger:
                with pytest.raises(Exception, match="Cosmos connection failed"):
                    config.get_cosmos_database_client()
                
                mock_logger.assert_called_once()

    @patch('common.config.app_config.AIProjectClient')
    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_ai_project_client_success(self, mock_default_credential, mock_ai_client):
        """Test successful AI Project client creation."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        mock_ai_instance = MagicMock()
        mock_ai_client.return_value = mock_ai_instance
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            result = config.get_ai_project_client()
            
            mock_ai_client.assert_called_once_with(
                endpoint="https://test.ai.azure.com",
                credential=mock_credential
            )
            assert result == mock_ai_instance

    @patch('common.config.app_config.AIProjectClient')
    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_ai_project_client_caching(self, mock_default_credential, mock_ai_client):
        """Test that AI Project client is cached."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        mock_ai_instance = MagicMock()
        mock_ai_client.return_value = mock_ai_instance
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            # First call
            result1 = config.get_ai_project_client()
            
            # Second call should return cached client
            result2 = config.get_ai_project_client()
            
            # AI client should only be created once
            mock_ai_client.assert_called_once()
            assert result1 == result2 == mock_ai_instance

    @patch('common.config.app_config.AIProjectClient')
    def test_get_ai_project_client_credential_failure(self, mock_ai_client):
        """Test AI Project client creation with credential failure."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            # Mock get_azure_credential to return None
            with patch.object(config, 'get_azure_credential', return_value=None):
                with pytest.raises(RuntimeError, match="Unable to acquire Azure credentials"):
                    config.get_ai_project_client()

    @patch('common.config.app_config.AIProjectClient')
    @patch('common.config.app_config.DefaultAzureCredential')
    def test_get_ai_project_client_creation_failure(self, mock_default_credential, mock_ai_client):
        """Test AI Project client creation failure."""
        mock_credential = MagicMock()
        mock_default_credential.return_value = mock_credential
        
        mock_ai_client.side_effect = Exception("AI client creation failed")
        
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            
            with patch('logging.error') as mock_logger:
                with pytest.raises(Exception, match="AI client creation failed"):
                    config.get_ai_project_client()
                
                mock_logger.assert_called_once()


class TestAppConfigUtilityMethods:
    """Test cases for utility methods in AppConfig class."""

    def _get_minimal_env(self):
        """Helper method to get minimal required environment variables."""
        return {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "dev",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "test-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "test-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "test-resource-group",
            "AZURE_AI_PROJECT_NAME": "test-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://test.ai.azure.com"
        }

    @patch.dict(os.environ, {"USER_LOCAL_BROWSER_LANGUAGE": "fr-FR"})
    def test_get_user_local_browser_language_with_env_var(self):
        """Test get_user_local_browser_language with environment variable set."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config.get_user_local_browser_language()
            assert result == "fr-FR"

    def test_get_user_local_browser_language_default(self):
        """Test get_user_local_browser_language with default value."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config.get_user_local_browser_language()
            assert result == "en-US"

    def test_set_user_local_browser_language(self):
        """Test set_user_local_browser_language method."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            config.set_user_local_browser_language("es-ES")
            
            assert os.environ["USER_LOCAL_BROWSER_LANGUAGE"] == "es-ES"
            assert config.get_user_local_browser_language() == "es-ES"

    def test_get_agents_method(self):
        """Test get_agents method returns the agents dictionary."""
        with patch.dict(os.environ, self._get_minimal_env()):
            config = AppConfig()
            result = config.get_agents()
            
            assert isinstance(result, dict)
            assert result == config._agents


class TestAppConfigIntegration:
    """Integration tests combining multiple AppConfig functionalities."""

    def _get_complete_env(self):
        """Helper method to get complete environment variables for integration tests."""
        return {
            "AZURE_TENANT_ID": "test-tenant-id",
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-client-secret",
            "COSMOSDB_ENDPOINT": "https://test.cosmosdb.azure.com",
            "COSMOSDB_DATABASE": "test-database",
            "COSMOSDB_CONTAINER": "test-container",
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "test_connection_string",
            "APP_ENV": "prod",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "prod-gpt-4o",
            "AZURE_OPENAI_RAI_DEPLOYMENT_NAME": "prod-gpt-4.1",
            "AZURE_OPENAI_API_VERSION": "2024-11-20",
            "AZURE_OPENAI_ENDPOINT": "https://prod.openai.azure.com",
            "AZURE_AI_SUBSCRIPTION_ID": "prod-subscription-id",
            "AZURE_AI_RESOURCE_GROUP": "prod-resource-group",
            "AZURE_AI_PROJECT_NAME": "prod-project",
            "AZURE_AI_AGENT_ENDPOINT": "https://prod.ai.azure.com",
            "FRONTEND_SITE_NAME": "https://prod.frontend.com",
            "MCP_SERVER_ENDPOINT": "http://prod.mcp.server:8000/mcp",
            "TEST_TEAM_JSON": "prod_team",
            "USER_LOCAL_BROWSER_LANGUAGE": "en-GB"
        }

    def test_complete_configuration_flow(self):
        """Test complete configuration flow with all settings."""
        with patch.dict(os.environ, self._get_complete_env()):
            config = AppConfig()
            
            # Verify all configurations are loaded correctly
            assert config.AZURE_TENANT_ID == "test-tenant-id"
            assert config.APP_ENV == "prod"
            assert config.AZURE_OPENAI_DEPLOYMENT_NAME == "prod-gpt-4o"
            assert config.COSMOSDB_ENDPOINT == "https://test.cosmosdb.azure.com"
            assert config.FRONTEND_SITE_NAME == "https://prod.frontend.com"
            assert config.MCP_SERVER_ENDPOINT == "http://prod.mcp.server:8000/mcp"
            
            # Test utility methods work correctly
            language = config.get_user_local_browser_language()
            assert language == "en-GB"
            
            agents = config.get_agents()
            assert isinstance(agents, dict)

    @patch('common.config.app_config.ManagedIdentityCredential')
    @patch('common.config.app_config.CosmosClient')
    @patch('common.config.app_config.AIProjectClient')
    def test_production_environment_client_creation(self, mock_ai_client, mock_cosmos_client, mock_managed_credential):
        """Test client creation in production environment."""
        mock_credential = MagicMock()
        mock_managed_credential.return_value = mock_credential
        
        mock_cosmos_instance = MagicMock()
        mock_database_client = MagicMock()
        mock_cosmos_instance.get_database_client.return_value = mock_database_client
        mock_cosmos_client.return_value = mock_cosmos_instance
        
        mock_ai_instance = MagicMock()
        mock_ai_client.return_value = mock_ai_instance
        
        with patch.dict(os.environ, self._get_complete_env()):
            config = AppConfig()
            
            # Test credential creation uses ManagedIdentityCredential in prod
            credential = config.get_azure_credential("test-client-id")
            mock_managed_credential.assert_called_with(client_id="test-client-id")
            
            # Test Cosmos client creation
            cosmos_client = config.get_cosmos_database_client()
            assert cosmos_client == mock_database_client
            
            # Test AI client creation
            ai_client = config.get_ai_project_client()
            assert ai_client == mock_ai_instance


if __name__ == "__main__":
    # Allow manual execution for debugging
    pytest.main([__file__, "-v"])
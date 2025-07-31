# Import AppConfig from app_config
from app_config import config
from helpers.azure_credential_utils import get_azure_credential


# This file is left as a lightweight wrapper around AppConfig for backward compatibility
# All configuration is now handled by AppConfig in app_config.py
class Config:
    # Use values from AppConfig
    AZURE_TENANT_ID = config.AZURE_TENANT_ID
    AZURE_CLIENT_ID = config.AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET = config.AZURE_CLIENT_SECRET

    # CosmosDB settings
    COSMOSDB_ENDPOINT = config.COSMOSDB_ENDPOINT
    COSMOSDB_DATABASE = config.COSMOSDB_DATABASE
    COSMOSDB_CONTAINER = config.COSMOSDB_CONTAINER

    # Azure OpenAI settings
    AZURE_OPENAI_DEPLOYMENT_NAME = config.AZURE_OPENAI_DEPLOYMENT_NAME
    AZURE_OPENAI_API_VERSION = config.AZURE_OPENAI_API_VERSION
    AZURE_OPENAI_ENDPOINT = config.AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_SCOPES = config.AZURE_OPENAI_SCOPES

    # Other settings
    FRONTEND_SITE_NAME = config.FRONTEND_SITE_NAME
    AZURE_AI_SUBSCRIPTION_ID = config.AZURE_AI_SUBSCRIPTION_ID
    AZURE_AI_RESOURCE_GROUP = config.AZURE_AI_RESOURCE_GROUP
    AZURE_AI_PROJECT_NAME = config.AZURE_AI_PROJECT_NAME
    AZURE_AI_AGENT_ENDPOINT = config.AZURE_AI_AGENT_ENDPOINT

    @staticmethod
    def GetAzureCredentials():
        """Get Azure credentials using the AppConfig implementation."""
        return get_azure_credential()

    @staticmethod
    def GetCosmosDatabaseClient():
        """Get a Cosmos DB client using the AppConfig implementation."""
        return config.get_cosmos_database_client()

    @staticmethod
    def CreateKernel():
        """Creates a new Semantic Kernel instance using the AppConfig implementation."""
        return config.create_kernel()

    @staticmethod
    def GetAIProjectClient():
        """Get an AIProjectClient using the AppConfig implementation."""
        return config.get_ai_project_client()

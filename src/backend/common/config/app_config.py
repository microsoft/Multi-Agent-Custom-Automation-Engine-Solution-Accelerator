# app_config.py
import logging
import os
from typing import Optional

from azure.ai.projects.aio import AIProjectClient
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv
from semantic_kernel import Kernel

# Load environment variables from .env file
load_dotenv()


class AppConfig:
    """Application configuration class that loads settings from environment variables."""

    def __init__(self):
        """Initialize the application configuration with environment variables."""
        self.logger = logging.getLogger(__name__)
        # Azure authentication settings
        self.AZURE_TENANT_ID = self._get_optional("AZURE_TENANT_ID")
        self.AZURE_CLIENT_ID = self._get_optional("AZURE_CLIENT_ID")
        self.AZURE_CLIENT_SECRET = self._get_optional("AZURE_CLIENT_SECRET")

        # CosmosDB settings
        self.COSMOSDB_ENDPOINT = self._get_optional("COSMOSDB_ENDPOINT")
        self.COSMOSDB_DATABASE = self._get_optional("COSMOSDB_DATABASE")
        self.COSMOSDB_CONTAINER = self._get_optional("COSMOSDB_CONTAINER")

        self.APPLICATIONINSIGHTS_CONNECTION_STRING = self._get_required(
            "APPLICATIONINSIGHTS_CONNECTION_STRING"
        )
        self.APP_ENV = self._get_required("APP_ENV", "prod")
        # self.AZURE_AI_MODEL_DEPLOYMENT_NAME = self._get_required(
        #     "AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o"
        # )

        self.AZURE_COGNITIVE_SERVICES = self._get_optional(
            "AZURE_COGNITIVE_SERVICES", "https://cognitiveservices.azure.com/.default"
        )

        self.AZURE_MANAGEMENT_SCOPE = self._get_optional(
            "AZURE_MANAGEMENT_SCOPE", "https://management.azure.com/.default"
        )

        # Azure OpenAI settings
        self.AZURE_OPENAI_DEPLOYMENT_NAME = self._get_required(
            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"
        )
        self.AZURE_OPENAI_API_VERSION = self._get_required(
            "AZURE_OPENAI_API_VERSION", "2024-11-20"
        )
        self.AZURE_OPENAI_ENDPOINT = self._get_required("AZURE_OPENAI_ENDPOINT")
        self.REASONING_MODEL_NAME = self._get_optional("REASONING_MODEL_NAME", "o3")
        # self.AZURE_BING_CONNECTION_NAME = self._get_optional(
        #     "AZURE_BING_CONNECTION_NAME"
        # )
        self.SUPPORTED_MODELS = self._get_optional("SUPPORTED_MODELS")
        # Frontend settings
        self.FRONTEND_SITE_NAME = self._get_optional(
            "FRONTEND_SITE_NAME", "http://127.0.0.1:3000"
        )

        # Azure AI settings
        self.AZURE_AI_SUBSCRIPTION_ID = self._get_required("AZURE_AI_SUBSCRIPTION_ID")
        self.AZURE_AI_RESOURCE_GROUP = self._get_required("AZURE_AI_RESOURCE_GROUP")
        self.AZURE_AI_PROJECT_NAME = self._get_required("AZURE_AI_PROJECT_NAME")
        self.AZURE_AI_AGENT_ENDPOINT = self._get_required("AZURE_AI_AGENT_ENDPOINT")
        self.AZURE_AI_PROJECT_ENDPOINT = self._get_optional("AZURE_AI_PROJECT_ENDPOINT")

        # Azure Search settings
        self.AZURE_SEARCH_ENDPOINT = self._get_optional("AZURE_AI_SEARCH_ENDPOINT")

        # Optional MCP server endpoint (for local MCP server or remote)
        # Example: http://127.0.0.1:8000/mcp
        self.MCP_SERVER_ENDPOINT = self._get_optional("MCP_SERVER_ENDPOINT")
        self.MCP_SERVER_NAME = self._get_optional(
            "MCP_SERVER_NAME", "MCPGreetingServer"
        )
        self.MCP_SERVER_DESCRIPTION = self._get_optional(
            "MCP_SERVER_DESCRIPTION", "MCP server with greeting and planning tools"
        )
        self.TENANT_ID = self._get_optional("AZURE_TENANT_ID")
        self.CLIENT_ID = self._get_optional("AZURE_CLIENT_ID")
        self.AZURE_AI_SEARCH_CONNECTION_NAME = self._get_optional(
            "AZURE_AI_SEARCH_CONNECTION_NAME"
        )
        self.AZURE_AI_SEARCH_INDEX_NAME = self._get_optional(
            "AZURE_AI_SEARCH_INDEX_NAME"
        )
        self.AZURE_AI_SEARCH_ENDPOINT = self._get_optional("AZURE_AI_SEARCH_ENDPOINT")
        self.AZURE_AI_SEARCH_API_KEY = self._get_optional("AZURE_AI_SEARCH_API_KEY")
        # self.BING_CONNECTION_NAME = self._get_optional("BING_CONNECTION_NAME")

        test_team_json = self._get_optional("TEST_TEAM_JSON")

        self.AGENT_TEAM_FILE = f"../../data/agent_teams/{test_team_json}.json"

        # Cached clients and resources
        self._azure_credentials = None
        self._cosmos_client = None
        self._cosmos_database = None
        self._ai_project_client = None

        self._agents = {}

    def get_azure_credential(self, client_id=None):
        """
        Returns an Azure credential based on the application environment.

        If the environment is 'dev', it uses DefaultAzureCredential.
        Otherwise, it uses ManagedIdentityCredential.

        Args:
            client_id (str, optional): The client ID for the Managed Identity Credential.

        Returns:
            Credential object: Either DefaultAzureCredential or ManagedIdentityCredential.
        """
        if self.APP_ENV == "dev":
            return (
                DefaultAzureCredential()
            )  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
        else:
            return ManagedIdentityCredential(client_id=client_id)

    def get_azure_credentials(self):
        """Retrieve Azure credentials, either from environment variables or managed identity."""
        if self._azure_credentials is None:
            self._azure_credentials = self.get_azure_credential(self.AZURE_CLIENT_ID)
        return self._azure_credentials

    async def get_access_token(self) -> str:
        """Get Azure access token for API calls."""
        try:
            credential = self.get_azure_credentials()
            token = credential.get_token(self.AZURE_COGNITIVE_SERVICES)
            return token.token
        except Exception as e:
            self.logger.error(f"Failed to get access token: {e}")
            raise

    def _get_required(self, name: str, default: Optional[str] = None) -> str:
        """Get a required configuration value from environment variables.

        Args:
            name: The name of the environment variable
            default: Optional default value if not found

        Returns:
            The value of the environment variable or default if provided

        Raises:
            ValueError: If the environment variable is not found and no default is provided
        """
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            logging.warning(
                "Environment variable %s not found, using default value", name
            )
            return default
        raise ValueError(
            f"Environment variable {name} not found and no default provided"
        )

    def _get_optional(self, name: str, default: str = "") -> str:
        """Get an optional configuration value from environment variables.

        Args:
            name: The name of the environment variable
            default: Default value if not found (default: "")

        Returns:
            The value of the environment variable or the default value
        """
        if name in os.environ:
            return os.environ[name]
        return default

    def _get_bool(self, name: str) -> bool:
        """Get a boolean configuration value from environment variables.

        Args:
            name: The name of the environment variable

        Returns:
            True if the environment variable exists and is set to 'true' or '1', False otherwise
        """
        return name in os.environ and os.environ[name].lower() in ["true", "1"]

    def get_cosmos_database_client(self):
        """Get a Cosmos DB client for the configured database.

        Returns:
            A Cosmos DB database client
        """
        try:
            if self._cosmos_client is None:
                self._cosmos_client = CosmosClient(
                    self.COSMOSDB_ENDPOINT,
                    credential=self.get_azure_credential(self.AZURE_CLIENT_ID),
                )

            if self._cosmos_database is None:
                self._cosmos_database = self._cosmos_client.get_database_client(
                    self.COSMOSDB_DATABASE
                )

            return self._cosmos_database
        except Exception as exc:
            logging.error(
                "Failed to create CosmosDB client: %s. CosmosDB is required for this application.",
                exc,
            )
            raise

    def create_kernel(self):
        """Creates a new Semantic Kernel instance.

        Returns:
            A new Semantic Kernel instance
        """
        # Create a new kernel instance without manually configuring OpenAI services
        # The agents will be created using Azure AI Agent Project pattern instead
        kernel = Kernel()
        return kernel

    def get_ai_project_client(self):
        """Create and return an AIProjectClient for Azure AI Foundry using from_connection_string.

        Returns:
            An AIProjectClient instance
        """
        if self._ai_project_client is not None:
            return self._ai_project_client

        try:
            credential = self.get_azure_credential(self.AZURE_CLIENT_ID)
            if credential is None:
                raise RuntimeError(
                    "Unable to acquire Azure credentials; ensure Managed Identity is configured"
                )

            endpoint = self.AZURE_AI_AGENT_ENDPOINT
            self._ai_project_client = AIProjectClient(
                endpoint=endpoint, credential=credential
            )

            return self._ai_project_client
        except Exception as exc:
            logging.error("Failed to create AIProjectClient: %s", exc)
            raise

    def get_user_local_browser_language(self) -> str:
        """Get the user's local browser language from environment variables.

        Returns:
            The user's local browser language or 'en-US' if not set
        """
        return self._get_optional("USER_LOCAL_BROWSER_LANGUAGE", "en-US")

    def set_user_local_browser_language(self, language: str):
        """Set the user's local browser language in environment variables.

        Args:
            language: The language code to set (e.g., 'en-US')
        """
        os.environ["USER_LOCAL_BROWSER_LANGUAGE"] = language

    # Get agent team list by user_id dictionary index
    def get_agents(self) -> dict[str, list]:
        """Get the list of agents configured in the application.

        Returns:
            A list of agent names or configurations
        """
        return self._agents


# Create a global instance of AppConfig
config = AppConfig()

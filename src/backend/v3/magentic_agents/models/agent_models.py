"""Models for agent configurations."""

import os
from dataclasses import dataclass


@dataclass(slots=True)
class MCPConfig:
    """Configuration for connecting to an MCP server."""
    url: str = ""
    name: str = "MCP"
    description: str = ""
    tenant_id: str = ""
    client_id: str = ""

    @classmethod
    def from_env(cls) -> "MCPConfig":
        url = os.getenv("MCP_SERVER_ENDPOINT")
        name = os.getenv("MCP_SERVER_NAME")
        description = os.getenv("MCP_SERVER_DESCRIPTION")
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        
        # Raise exception if any required environment variable is missing
        if not all([url, name, description, tenant_id, client_id]):
            raise ValueError(f"{cls.__name__} Missing required environment variables")
            
        return cls(
            url=url,
            name=name,
            description=description,
            tenant_id=tenant_id,
            client_id=client_id,
        )

@dataclass(slots=True)
class BingConfig:
    """Configuration for connecting to Bing Search."""
    connection_name: str = "Bing"

    @classmethod
    def from_env(cls) -> "BingConfig":
        connection_name = os.getenv("BING_CONNECTION_NAME")

        # Raise exception if required environment variable is missing
        if not connection_name:
            raise ValueError(f"{cls.__name__} Missing required environment variables")

        return cls(
            connection_name=connection_name,
        )

@dataclass(slots=True)
class SearchConfig:
    """Configuration for connecting to Azure AI Search."""
    connection_name: str | None = None
    endpoint: str | None = None
    index_name: str | None = None
    embedding_endpoint: str | None = None  # Azure OpenAI endpoint
    embedding_model: str | None = None  # e.g., "text-embedding-ada-002"
    api_key: str | None = None  # API key for Azure AI Search

    @classmethod
    def from_env(cls) -> "SearchConfig":
        connection_name = os.getenv("AZURE_AI_SEARCH_CONNECTION_NAME")
        index_name = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")
        endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        embedding_endpoint = os.getenv("AZURE_AI_SEARCH_EMBEDDING_ENDPOINT")
        embedding_model = os.getenv("AZURE_AI_SEARCH_EMBEDDING_MODEL_NAME")
        api_key = os.getenv("AZURE_AI_SEARCH_API_KEY")
        
        # Raise exception if any required environment variable is missing
        if not all([connection_name, index_name, endpoint]):
            raise ValueError(f"{cls.__name__} Missing required Azure Search environment variables")
            
        return cls(
            connection_name=connection_name,
            index_name=index_name,
            endpoint=endpoint,
            embedding_endpoint=embedding_endpoint,
            embedding_model=embedding_model,
            api_key=api_key,
        )
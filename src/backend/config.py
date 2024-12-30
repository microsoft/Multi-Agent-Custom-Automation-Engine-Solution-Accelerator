# config.py
import logging
import os

from autogen_core.components.models import AzureOpenAIChatCompletionClient
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import (ClientSecretCredential, DefaultAzureCredential,
                                get_bearer_token_provider)
from dotenv import load_dotenv

load_dotenv()


def GetRequiredConfig(name):
    return os.environ[name]


def GetOptionalConfig(name, default=""):
    if name in os.environ:
        return os.environ[name]
    return default


def GetBoolConfig(name):
    return name in os.environ and os.environ[name].lower() in ["true", "1"]



class Config:
    AZURE_TENANT_ID = GetOptionalConfig("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = GetOptionalConfig("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = GetOptionalConfig("AZURE_CLIENT_SECRET")

    COSMOSDB_ENDPOINT = GetRequiredConfig("COSMOSDB_ENDPOINT")
    COSMOSDB_DATABASE = GetRequiredConfig("COSMOSDB_DATABASE")
    COSMOSDB_CONTAINER = GetRequiredConfig("COSMOSDB_CONTAINER")

    AZURE_OPENAI_DEPLOYMENT_NAME = GetRequiredConfig("AZURE_OPENAI_DEPLOYMENT_NAME")
    AZURE_OPENAI_API_VERSION = GetRequiredConfig("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_ENDPOINT = GetRequiredConfig("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = GetOptionalConfig("AZURE_OPENAI_API_KEY")

    FRONTEND_SITE_NAME = GetOptionalConfig("FRONTEND_SITE_NAME", "http://127.0.0.1:3000")
    

    __azure_credentials = DefaultAzureCredential()
    __comos_client = None
    __cosmos_database = None
    __aoai_chatCompletionClient = None

    def GetAzureCredentials():
        # If we have specified the credentials in the environment, use them (backwards compatibility)
        if all(
            [Config.AZURE_TENANT_ID, Config.AZURE_CLIENT_ID, Config.AZURE_CLIENT_SECRET]
        ):
            return ClientSecretCredential(
                tenant_id=Config.AZURE_TENANT_ID,
                client_id=Config.AZURE_CLIENT_ID,
                client_secret=Config.AZURE_CLIENT_SECRET,
            )

        # Otherwise, use the default Azure credential which includes managed identity
        return Config.__azure_credentials

    # Gives us a cached approach to DB access
    def GetCosmosDatabaseClient():
        # TODO: Today this is a single DB, we might want to support multiple DBs in the future
        if Config.__comos_client is None:
            Config.__comos_client = CosmosClient(
                Config.COSMOSDB_ENDPOINT, Config.GetAzureCredentials()
            )

        if Config.__cosmos_database is None:
            Config.__cosmos_database = Config.__comos_client.get_database_client(
                Config.COSMOSDB_DATABASE
            )

        return Config.__cosmos_database

    def GetTokenProvider(scopes):
        return get_bearer_token_provider(Config.GetAzureCredentials(), scopes)

    def GetAzureOpenAIChatCompletionClient(model_capabilities):
        if Config.__aoai_chatCompletionClient is not None:
            return Config.__aoai_chatCompletionClient

        if Config.AZURE_OPENAI_API_KEY == "":
            # Use DefaultAzureCredential for auth
            Config.__aoai_chatCompletionClient = AzureOpenAIChatCompletionClient(
                model=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=Config.GetTokenProvider(
                    "https://cognitiveservices.azure.com/.default"
                ),
                model_capabilities=model_capabilities,
                temperature=0,
            )
        else:
            # Fallback behavior to use API key
            Config.__aoai_chatCompletionClient = AzureOpenAIChatCompletionClient(
                model=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_key=Config.AZURE_OPENAI_API_KEY,
                model_capabilities=model_capabilities,
                temperature=0,
            )

        return Config.__aoai_chatCompletionClient

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexerDataSourceConnection,
    SearchIndexer,
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType
)

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")

# Validate required environment variables
required_vars = [SEARCH_ENDPOINT, SEARCH_API_KEY, BLOB_CONNECTION_STRING, BLOB_CONTAINER_NAME]
if any(var is None for var in required_vars):
    raise ValueError("One or more required environment variables are missing.")

def create_search_resources():
    """Create Azure AI Search resources: data source, index, and indexer."""
    try:
        # Initialize SearchIndexClient for index operations
        index_client = SearchIndexClient(
            endpoint=SEARCH_ENDPOINT,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        
        # Initialize SearchIndexerClient for data source and indexer operations
        indexer_client = SearchIndexerClient(
            endpoint=SEARCH_ENDPOINT,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )

        # Define data source connection
        data_source = SearchIndexerDataSourceConnection(
            name="macae-blob-datasets",
            type="azureblob",
            connection_string=BLOB_CONNECTION_STRING,
            container={"name": BLOB_CONTAINER_NAME}
        )
        indexer_client.create_or_update_data_source_connection(data_source)
        print("Data source 'macae-blob-datasets' created successfully.")

        # Define index schema
        index = SearchIndex(
            name="macae-index",
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="metadata", type=SearchFieldDataType.String)
            ]
        )
        index_client.create_or_update_index(index)
        print("Index 'macae-index' created successfully.")

        # Define indexer
        indexer = SearchIndexer(
            name="macae-indexer",
            data_source_name="macae-blob-datasets",
            target_index_name="macae-index"
        )
        indexer_client.create_or_update_indexer(indexer)
        print("Indexer 'macae-indexer' created successfully.")

    except Exception as e:
        print(f"An error occurred while creating search resources: {e}")

if __name__ == "__main__":
    create_search_resources()

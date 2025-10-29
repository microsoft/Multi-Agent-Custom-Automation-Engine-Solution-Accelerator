import os
import sys
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SearchIndexerDataSourceConnection,
    SearchIndexer,
    SearchIndexerDataContainer,
    FieldMapping
)

# --- CONFIGURATION ---
search_service_endpoint = ""  # e.g., "https://<your-service-name>.search.windows.net"
admin_key = ""                # Your Azure Search admin key

storage_connection_string = ""  # Azure Blob Storage connection string
blob_container_name = ""        # Container name with PDFs

data_source_name = ""
index_name = "pdf-index"
indexer_name = ""

# --- Initialize Clients ---
index_client = SearchIndexClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(admin_key))
indexer_client = SearchIndexerClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(admin_key))

# --- Define Index Fields ---
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True)
]

index = SearchIndex(name=index_name, fields=fields)

# --- Create or Update Index ---
try:
    index_client.create_or_update_index(index)
    print(f"✅ Created or updated index: {index_name}")
except Exception as e:
    print(f"❌ Failed to create/update index: {e}")
    sys.exit(1)

# --- Define Data Source (Azure Blob Storage) ---
data_source = SearchIndexerDataSourceConnection(
    name=data_source_name,
    type="azureblob",
    connection_string=storage_connection_string,
    container=SearchIndexerDataContainer(name=blob_container_name),
    description="PDF files from Azure Blob Storage"
)

try:
    indexer_client.create_or_update_data_source_connection(data_source)
    print(f"✅ Created or updated data source: {data_source_name}")
except Exception as e:
    print(f"❌ Failed to create/update data source: {e}")
    sys.exit(1)

# --- Define Indexer for PDF Extraction ---
indexer = SearchIndexer(
    name=indexer_name,
    description="Indexer for PDF documents from Blob Storage",
    data_source_name=data_source_name,
    target_index_name=index_name,
    parameters={
        "configuration": {
            "parsingMode": "default",                 
            "dataToExtract": "contentAndMetadata",     
            "indexedFileNameExtensions": ".pdf",       
            "failOnUnsupportedContentType": False,
            "excludedFileNameExtensions": ".jpg,.png,.zip,.exe",
            "contentTypeDetection": "auto"
        }
    },
    field_mappings=[
        FieldMapping(source_field_name="metadata_storage_path", target_field_name="id"),
        FieldMapping(source_field_name="metadata_storage_name", target_field_name="title"),
        FieldMapping(source_field_name="content", target_field_name="content")
    ]
)

# --- Create or Update Indexer ---
try:
    indexer_client.create_or_update_indexer(indexer)
    print(f"✅ Created or updated indexer: {indexer_name}")
except Exception as e:
    print(f"❌ Failed to create/update indexer: {e}")
    sys.exit(1)

# --- Run Indexer ---
try:
    indexer_client.run_indexer(indexer_name)
    print("🚀 Indexer started successfully for PDF ingestion.")
except Exception as e:
    print(f"❌ Failed to run indexer: {e}")

import os
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
    BlobIndexerDataToExtract,
    BlobIndexerParsingMode,
    FieldMapping,
    FieldMappingFunction
)

# --- CONFIGURATION ---
search_service_endpoint = "https://macae-search.search.windows.net"
admin_key = "prm3QaLrqYIBeKAOO9GlcvMTOc6WlvVewKyHoTjXxhAzSeBLxz7K"

storage_connection_string = "DefaultEndpointsProtocol=https;AccountName=rfpstorage1010;AccountKey=zPdUD9vPl8MNzs1HfOS0xoFxEJh+HKTfvqQvGTLacf24CmP83TbHT/lU5zvyDuxbeJH8Ryck3C96+AStGXstYA==;EndpointSuffix=core.windows.net"
blob_container_name = "rfp-documents"

data_source_name = "clm-rfp-blob-datasource"
index_name = "clm-rfp-index"
indexer_name = "clm-rfp-indexer"

# --- Initialize Clients ---
index_client = SearchIndexClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(admin_key))
indexer_client = SearchIndexerClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(admin_key))

# --- Define Index ---
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="section", type=SearchFieldDataType.String, filterable=True, sortable=True),
    SearchableField(name="text", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
    SimpleField(name="source_csv", type=SearchFieldDataType.String, filterable=True)
]

index = SearchIndex(name=index_name, fields=fields)

try:
    index_client.create_index(index)
    print(f"✅ Created index: {index_name}")
except Exception as e:
    if "already exists" in str(e):
        print(f"⚠️ Index already exists: {index_name}")
    else:
        print(f"❌ Failed to create index: {e}")

# --- Define Data Source (Blob Storage) ---
data_source = SearchIndexerDataSourceConnection(
    name=data_source_name,
    type="azureblob",
    connection_string=storage_connection_string,
    container=SearchIndexerDataContainer(name=blob_container_name),
    description="CLM RFP CSVs from Azure Blob Storage"
)

try:
    indexer_client.create_data_source_connection(data_source)
    print(f"✅ Created data source: {data_source_name}")
except Exception as e:
    if "already exists" in str(e):
        print(f"⚠️ Data source already exists: {data_source_name}")
    else:
        print(f"❌ Failed to create data source: {e}")

# --- Define Indexer (CSV parsing) ---
indexer = SearchIndexer(
    name=indexer_name,
    description="Indexer for CLM RFP CSV data from Blob Storage",
    data_source_name=data_source_name,
    target_index_name=index_name,
    parameters={
    "configuration": {
        "parsingMode": "delimitedText",
        "delimiter": ",",
        "firstLineContainsHeaders": True,
        "dataToExtract": "contentAndMetadata",
        "documentRoot": "/",
        "failOnUnsupportedContentType": False,
        "indexedFileNameExtensions": ".csv",
        "contentTypeDetection": "auto",  # ✅ REQUIRED
        "detectEncodingFromByteOrderMarks": True,
        "encoding": "utf-8"
    }
}

,
    field_mappings=[
        FieldMapping(source_field_name="id", target_field_name="id"),
        FieldMapping(source_field_name="section", target_field_name="section"),
        FieldMapping(source_field_name="text", target_field_name="text"),
        FieldMapping(source_field_name="metadata_storage_name", target_field_name="source_csv")
    ]
)

try:
    indexer_client.create_indexer(indexer)
    print(f"✅ Created indexer: {indexer_name}")
except Exception as e:
    if "already exists" in str(e):
        print(f"⚠️ Indexer already exists: {indexer_name}")
    else:
        print(f"❌ Failed to create indexer: {e}")

# --- Run Indexer ---
try:
    indexer_client.run_indexer(indexer_name)
    print("🚀 Indexer started successfully.")
except Exception as e:
    print(f"❌ Failed to run indexer: {e}")

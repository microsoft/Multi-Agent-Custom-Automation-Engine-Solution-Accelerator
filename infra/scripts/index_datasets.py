from azure.identity import AzureCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, SearchFieldDataType
from azure.storage.blob import BlobServiceClient
import sys

if len(sys.argv) < 4:
    print("Usage: python index_datasets.py <storage_account_name> <blob_container_name> <ai_search_endpoint> [<ai_search_index_name>]")
    sys.exit(1)

storage_account_name = sys.argv[1]
blob_container_name = sys.argv[2]
ai_search_endpoint = sys.argv[3]
ai_search_index_name = sys.argv[4] if len(sys.argv) > 4 else "sample-dataset-index"
if not ai_search_endpoint.__contains__("search.windows.net"):
    ai_search_endpoint = f"https://{ai_search_endpoint}.search.windows.net"

credential = AzureCliCredential()

try:
    blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=credential)
    container_client = blob_service_client.get_container_client(blob_container_name)
    print("Fetching files in container...")
    blob_list = list(container_client.list_blobs())
except Exception as e:
    print(f"Error fetching files: {e}")
    sys.exit(1)

success_count = 0
fail_count = 0
data_list = []

try:
    index_fields = [ 
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchableField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True)
    ]
    index = SearchIndex(name=ai_search_index_name, fields=index_fields)

    print("Creating or updating Azure Search index...")
    search_index_client = SearchIndexClient(endpoint=ai_search_endpoint, credential=credential)
    index_result = search_index_client.create_or_update_index(index=index)
    print(f"Index '{ai_search_index_name}' created or updated successfully.")
except Exception as e:
    print(f"Error creating/updating index: {e}")
    sys.exit(1)

for idx, blob in enumerate(blob_list, start=1):
    #if blob.name.endswith(".csv"):
    title = blob.name.replace(".csv", "")
    title = title.replace(".json", "")
    data = container_client.download_blob(blob.name).readall()
    
    try:
        print(f"Reading data from blob: {blob.name}...")
        text = data.decode('utf-8')
        data_list.append({
            "content": text,
            "id": str(idx),
            "title": title
        })
        success_count += 1
    except Exception as e:
        print(f"Error reading file - {blob.name}: {e}")
        fail_count += 1
        continue

if not data_list:
    print(f"No data to upload to Azure Search index. Success: {success_count}, Failed: {fail_count}")
    sys.exit(1)

try:
    print("Uploading documents to the index...")
    search_client = SearchClient(endpoint=ai_search_endpoint, index_name=ai_search_index_name, credential=credential)
    result = search_client.upload_documents(documents=data_list)
    print(f"Uploaded {len(data_list)} documents.")
except Exception as e:
    print(f"Error uploading documents: {e}")
    sys.exit(1)

print(f"Processing complete. Success: {success_count}, Failed: {fail_count}")
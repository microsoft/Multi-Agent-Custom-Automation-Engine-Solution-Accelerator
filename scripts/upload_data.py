import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

# --- Azure Blob Storage configuration ---
storage_account_url = ""
container_name = "rfp-documents"  # Your blob container name
csv_folder = "../data/datasets/RFP_dataset"

# --- Use DefaultAzureCredential (ensure you're authenticated to Azure) ---
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential)

# --- Get container client (create container if it doesn't exist) ---
container_client = blob_service_client.get_container_client(container_name)
try:
    container_client.create_container()
    print(f"📦 Created container: {container_name}")
except Exception as e:
    print(f"ℹ️ Container may already exist: {e}")

# --- Loop through all CSV files and upload ---
for filename in os.listdir(csv_folder):
    if filename.endswith(".csv"):
        file_path = os.path.join(csv_folder, filename)
        blob_client = container_client.get_blob_client(filename)

        with open(file_path, "rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type='text/csv')
            )
            print(f"✅ Uploaded {filename} to blob storage")

print("🎉 All CSVs uploaded to Azure Blob Storage!")

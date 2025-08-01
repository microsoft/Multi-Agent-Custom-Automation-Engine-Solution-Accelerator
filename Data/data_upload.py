from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv() 

# Retrieve environment variables
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")
local_folder = "./datasets"

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

for filename in os.listdir(local_folder):
    file_path = os.path.join(local_folder, filename)
    if os.path.isfile(file_path):
        print(f"Uploading {filename}...")
        with open(file_path, "rb") as data:
            container_client.upload_blob(name=filename, data=data, overwrite=True)
print("Upload complete!")

import os
import uuid
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)
from PyPDF2 import PdfReader

# --- CONFIGURATION ---
search_service_endpoint =""
admin_key =""  
storage_account_url = ""
blob_container_name =""
local_data_folder = ""
index_name = ""

# --- STEP 1: Upload PDFs to Azure Blob Storage ---
print("Uploading PDF files to Azure Blob Storage using Azure AD authentication...")

try:
    # Authenticate using Azure AD
    blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=DefaultAzureCredential())
    container_client = blob_service_client.get_container_client(blob_container_name)

    # Create container if it doesn't exist
    if not container_client.exists():
        container_client.create_container()
        print(f"Created container: {blob_container_name}")
    else:
        print(f"Container already exists: {blob_container_name}")

    uploaded_files = []
    for root, _, files in os.walk(local_data_folder):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(root, filename)
                blob_path = os.path.relpath(file_path, local_data_folder)
                blob_client = container_client.get_blob_client(blob_path)

                with open(file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
                print(f"⬆️ Uploaded: {blob_path}")
                uploaded_files.append(filename)

    if not uploaded_files:
        print(" No PDF files found to upload.")
except Exception as e:
    print(f" Upload failed: {e}")

# --- STEP 2: Create Azure AI Search Index ---
print("\n Setting up Azure AI Search index...")

index_client = SearchIndexClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(admin_key))

index_fields = [ 
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True)
]

index = SearchIndex(name=index_name, fields=index_fields)

try:
    index_client.create_index(index)
    print(f" Created index: {index_name}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f" Index already exists: {index_name}")
    else:
        print(f" Failed to create index: {e}")

# --- STEP 3: Extract text from PDFs and index into Azure AI Search ---
print("\n Extracting text from PDFs and indexing into Azure AI Search...")

search_client = SearchClient(endpoint=search_service_endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file using PyPDF2."""
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f" Error reading {pdf_path}: {e}")
    return text.strip()

docs = []
for root, _, files in os.walk(local_data_folder):
    for filename in files:
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(root, filename)
            text_content = extract_text_from_pdf(file_path)

            if text_content:
                docs.append({
                    "id": str(uuid.uuid4()),
                    "content": text_content,
                    "title": filename
                })
                print(f" Extracted and prepared: {filename}")
            else:
                print(f" No text extracted from {filename}")

# --- Upload documents to index ---
if docs:
    try:
        batch_size = 500  # Upload in manageable chunks
        for i in range(0, len(docs), batch_size):
            chunk = docs[i:i + batch_size]
            results = search_client.upload_documents(chunk)
            succeeded = sum(1 for r in results if r.succeeded)
            print(f" Indexed {succeeded}/{len(chunk)} documents in batch {i//batch_size + 1}")
        print(f" Done! Total indexed documents: {len(docs)}")
    except Exception as e:
        print(f" Failed to upload documents: {e}")
else:
    print(" No documents to index.")

print("\n PDFs are now stored in Azure Blob Storage and indexed in Azure AI Search.")

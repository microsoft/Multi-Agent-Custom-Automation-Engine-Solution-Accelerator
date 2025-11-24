import os
import sys
import uuid
from pathlib import Path

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, SearchFieldDataType
from azure.core.credentials import AzureKeyCredential

# Optional import for DOCX extraction
try:
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError
except Exception:
    Document = None
    PackageNotFoundError = None

# --------------------------
# CONFIGURATION
repo_root = Path(__file__).resolve().parent
LOCAL_DOCX_FOLDER = repo_root / "data" / "datasets" / "legal_contract"

AZURE_SEARCH_SERVICE = ""
AZURE_SEARCH_ADMIN_KEY = ""
AZURE_SEARCH_INDEX_NAME = ""
# --------------------------

# Ensure folder exists and show resolved path
LOCAL_DOCX_FOLDER = LOCAL_DOCX_FOLDER.resolve()
os.makedirs(LOCAL_DOCX_FOLDER, exist_ok=True)
print(f"Using local DOCX folder: {LOCAL_DOCX_FOLDER}")

if Document is None:
    print("python-docx is not installed. Install with: pip install python-docx")
    sys.exit(1)

def extract_text_from_docx(file_path):
    file_path = str(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    try:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)
    except PackageNotFoundError:
        # Not a valid .docx archive (possibly a renamed file) — treat as skip
        raise
    except Exception:
        raise

# Collect documents
documents = []
skipped = []

for entry in sorted(os.listdir(LOCAL_DOCX_FOLDER)):
    if not entry.lower().endswith(".docx"):
        continue
    if entry.startswith("~$"):
        # skip Word temp files
        continue

    path = LOCAL_DOCX_FOLDER / entry
    if not path.is_file():
        continue

    try:
        text = extract_text_from_docx(path)
    except PackageNotFoundError:
        print(f"Skipping (invalid .docx): {entry}")
        skipped.append(entry)
        continue
    except Exception as e:
        print(f"Failed to extract {entry}: {e}")
        skipped.append(entry)
        continue

    if not text or not text.strip():
        print(f"Skipping (no text): {entry}")
        skipped.append(entry)
        continue

    documents.append({
        "id": str(uuid.uuid4()),
        "title": entry,
        "content": text,
        "metadata_storage_path": str(path)
    })

if not documents:
    print("No valid DOCX files found or extracted. Exiting.")
    if skipped:
        print("Skipped files:")
        for s in skipped:
            print(" -", s)
    sys.exit(1)

print(f"Extracted text from {len(documents)} DOCX file(s).")

# --------------------------
# Create / update Azure Search index
index_client = SearchIndexClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
)

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="title", type=SearchFieldDataType.String),
    SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
    SimpleField(name="metadata_storage_path", type=SearchFieldDataType.String, filterable=True, sortable=True)
]

index = SearchIndex(name=AZURE_SEARCH_INDEX_NAME, fields=fields)
index_client.create_or_update_index(index)
print("Azure Search index created/updated.")

# --------------------------
# Upload documents
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX_NAME,
    credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
)

upload_results = search_client.upload_documents(documents)
succeeded = sum(1 for r in upload_results if getattr(r, "succeeded", False) is True)
print(f"Uploaded {succeeded}/{len(documents)} documents to Azure Search.")

# Optional quick search
query = "Compliance"
try:
    results = search_client.search(query, top=5)
    print(f"\nSearch results for '{query}':")
    for r in results:
        title = r.get("title") or r.get("metadata_storage_path")
        snippet = (r.get("content") or "")[:150].replace("\n", " ")
        print(f" - {title}: {snippet}...")
except Exception as e:
    print("Search query failed:", e)
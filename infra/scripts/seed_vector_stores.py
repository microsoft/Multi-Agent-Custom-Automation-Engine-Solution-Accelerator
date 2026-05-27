"""Create Foundry IQ vector stores from data/datasets/ files.

Usage:
    python scripts/seed_vector_stores.py

Requires AZURE_AI_PROJECT_ENDPOINT in src/backend/.env.
Idempotent: finds existing vector stores by name and skips re-creation.

Note: CSV files are converted to JSON before upload because the
FileSearchTool only supports: .c .cpp .cs .css .doc .docx .go .html
.java .js .json .md .pdf .php .pptx .py .rb .sh .tex .ts .txt
"""

import csv
import io
import json as json_mod
import os
import sys
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load .env from src/backend/
_backend_env = Path(__file__).parent.parent / "src" / "backend" / ".env"
load_dotenv(str(_backend_env), override=True)

PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
if not PROJECT_ENDPOINT:
    print("ERROR: AZURE_AI_PROJECT_ENDPOINT not set. Check src/backend/.env")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data" / "datasets"

# -------------------------------------------------------------------
# Vector store definitions: name → list of data file paths
# -------------------------------------------------------------------
VECTOR_STORES: dict[str, list[Path]] = {
    "macae-retail-customer-data": sorted(
        (DATA_DIR / "retail" / "customer").glob("*")
    ),
    "macae-retail-order-data": sorted(
        (DATA_DIR / "retail" / "order").glob("*")
    ),
}


SUPPORTED_EXTENSIONS = {
    ".c", ".cpp", ".cs", ".css", ".doc", ".docx", ".go", ".html",
    ".java", ".js", ".json", ".md", ".pdf", ".php", ".pptx",
    ".py", ".rb", ".sh", ".tex", ".ts", ".txt",
}


def csv_to_json_bytes(path: Path) -> io.BytesIO:
    """Convert a CSV file to a JSON byte stream (list of row dicts)."""
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    content = json_mod.dumps(rows, indent=2).encode("utf-8")
    buf = io.BytesIO(content)
    buf.name = path.stem + ".json"
    return buf


def find_existing_store(oai, name: str) -> str | None:
    """Return vector store ID if one with this name already exists."""
    for vs in oai.vector_stores.list():
        if vs.name == name:
            return vs.id
    return None


def create_vector_store(oai, name: str, file_paths: list[Path]) -> str:
    """Create a vector store, upload files, and wait for ingestion."""
    existing_id = find_existing_store(oai, name)
    if existing_id:
        print(f"  SKIP: '{name}' already exists (id={existing_id})")
        return existing_id

    # Upload files
    file_ids = []
    for path in file_paths:
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix == ".csv":
            # Convert CSV → JSON in memory
            print(f"  Uploading {path.name} (converted to JSON)...")
            buf = csv_to_json_bytes(path)
            uploaded = oai.files.create(file=buf, purpose="assistants")
        elif suffix in SUPPORTED_EXTENSIONS:
            print(f"  Uploading {path.name}...")
            with open(path, "rb") as f:
                uploaded = oai.files.create(file=f, purpose="assistants")
        else:
            print(f"  SKIP: {path.name} (unsupported extension '{suffix}')")
            continue

        file_ids.append(uploaded.id)
        print(f"    → {uploaded.id}")

    if not file_ids:
        print(f"  WARN: No files found for '{name}', skipping vector store creation.")
        return ""

    # Create vector store
    vs = oai.vector_stores.create(name=name)
    print(f"  Created vector store '{name}' (id={vs.id})")

    # Ingest files
    batch = oai.vector_stores.file_batches.create(
        vector_store_id=vs.id,
        file_ids=file_ids,
    )
    print(f"  Ingesting {len(file_ids)} file(s)... (batch={batch.id})")

    # Poll until complete
    while batch.status in ("in_progress", "validating"):
        time.sleep(2)
        batch = oai.vector_stores.file_batches.retrieve(
            vector_store_id=vs.id,
            batch_id=batch.id,
        )
        print(f"    status={batch.status}, completed={batch.file_counts.completed}/{batch.file_counts.total}")

    if batch.status != "completed":
        print(f"  ERROR: Batch finished with status={batch.status}")
        print(f"    failed={batch.file_counts.failed}, cancelled={batch.file_counts.cancelled}")
    else:
        print(f"  Done: {batch.file_counts.completed} file(s) ingested.")

    return vs.id


def main():
    print(f"Project endpoint: {PROJECT_ENDPOINT}")
    print(f"Data directory: {DATA_DIR}")
    print()

    credential = DefaultAzureCredential()
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )
    oai = project.get_openai_client()

    for store_name, file_paths in VECTOR_STORES.items():
        print(f"\n{'='*60}")
        print(f"Vector store: {store_name}")
        print(f"  Files: {[p.name for p in file_paths if p.is_file()]}")
        create_vector_store(oai, store_name, file_paths)

    print(f"\n{'='*60}")
    print("All vector stores processed.")


if __name__ == "__main__":
    main()

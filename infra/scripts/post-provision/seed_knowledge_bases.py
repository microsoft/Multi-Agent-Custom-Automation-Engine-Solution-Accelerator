"""Create Foundry IQ Knowledge Bases on Azure AI Search.

Usage:
    python infra/scripts/post-provision/seed_knowledge_bases.py

Requires in src/backend/.env:
  - AZURE_AI_SEARCH_ENDPOINT
  - Optionally AZURE_OPENAI_ENDPOINT (for KB model reasoning)

Authentication: Uses DefaultAzureCredential (az login, managed identity, etc.)
to obtain a bearer token for the search service. No admin key required.

Idempotent: PUTs semantic configurations (overwrite), creates knowledge
sources and the KB only if they don't already exist (409 = skip).

Prerequisites:
  - Indexes must already exist on the search service (see seed_vector_stores.py
    or manual index creation).
  - The search service managed identity needs "Cognitive Services OpenAI User"
    role on the AI Services resource for the model to be callable by the KB.
  - The caller needs "Search Service Contributor" role on the search service.
"""

import json
import os
import sys
from pathlib import Path

import httpx
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load .env from src/backend/ (override=False so env vars set by post_deploy.ps1 take precedence)
_backend_env = Path(__file__).parent.parent.parent.parent / "src" / "backend" / ".env"
load_dotenv(str(_backend_env), override=False)

SEARCH_ENDPOINT = os.environ.get("AZURE_AI_SEARCH_ENDPOINT", "").rstrip("/")
AI_SERVICES_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")

if not SEARCH_ENDPOINT:
    print("ERROR: AZURE_AI_SEARCH_ENDPOINT must be set.")
    sys.exit(1)

_SEARCH_SCOPE = "https://search.azure.com/.default"


def _get_auth_headers() -> dict:
    """Get Authorization headers using DefaultAzureCredential (no admin key needed)."""
    credential = DefaultAzureCredential()
    token = credential.get_token(_SEARCH_SCOPE)
    credential.close()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.token}",
    }

API_VERSION = "2025-05-01-preview"
KB_API_VERSION = "2025-11-01-preview"

# -------------------------------------------------------------------
# Knowledge Base definitions
# -------------------------------------------------------------------
# Each KB maps to one or more Azure AI Search indexes.
# The model is used for reasoning/grounding by the KB MCP endpoint.

KNOWLEDGE_BASES: dict = {
    # ── Retail ──
    "macae-retail-customer-kb": {
        "description": "Retail customer data knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-retail-customer-ks",
                "description": "Customer profile and interaction data",
                "index_name": "macae-retail-customer-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    "macae-retail-orders-kb": {
        "description": "Retail order, product, and fulfillment knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-retail-order-ks",
                "description": "Order, product, and fulfillment data",
                "index_name": "macae-retail-order-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    # ── Content Generation ──
    "macae-content-gen-products-kb": {
        "description": "Contoso Paint product catalog for marketing content generation",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-content-gen-products-ks",
                "description": "Product catalog with SKU, pricing, and descriptions",
                "index_name": "macae-content-gen-products-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },

    # ── Example Pack ──
    # ┌─────────────────────────────────────────────────────────────────────────┐
    # │ TEMPLATE: Copy this block when adding a new content pack KB.            │
    # │                                                                         │
    # │ To customize:                                                           │
    # │   1. Change the KB name (dict key) → "<your-pack>-<purpose>-kb"         │
    # │   2. Change "description" → describe what data this KB provides         │
    # │   3. Change "deploymentId"/"modelName" if using a different model       │
    # │   4. Change source "name" → "<your-pack>-<purpose>-ks"                  │
    # │   5. Change source "description" → what the source data contains        │
    # │   6. Change "index_name" → must match pack.json search_indexes[].name   │
    # │   7. Update "searchable_fields" to match your index schema              │
    # │                                                                         │
    # │ The KB name here must match "knowledge_base_name" in your agent JSON.   │
    # └─────────────────────────────────────────────────────────────────────────┘
    # "example-pack-books-kb": {
    #     "description": "Example book catalog knowledge base for the starter content pack",
    #     "model": {
    #         "kind": "azureOpenAI",
    #         "azureOpenAIParameters": {
    #             "resourceUri": AI_SERVICES_ENDPOINT,
    #             "deploymentId": "gpt-5.4-mini",        # ← CHANGE: model deployment name
    #             "modelName": "gpt-5.4-mini",           # ← CHANGE: model name
    #         },
    #     },
    #     "sources": [
    #         {
    #             "name": "example-pack-books-ks",       # ← CHANGE: unique knowledge source name
    #             "description": "Book catalog with title, author, genre, year, and summary",  # ← CHANGE
    #             "index_name": "example-pack-books-index",  # ← CHANGE: must match pack.json
    #             "searchable_fields": ["content", "title"],  # ← CHANGE: fields in your index
    #         },
    #     ],
    # },
    # ── Contract Compliance ──
    "macae-contract-summary-kb": {
        "description": "Contract summary and key terms knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-contract-summary-ks",
                "description": "Contract summaries and key terms",
                "index_name": "contract-summary-doc-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    "macae-contract-risk-kb": {
        "description": "Contract risk analysis knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-contract-risk-ks",
                "description": "Contract risk factors and assessments",
                "index_name": "contract-risk-doc-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    "macae-contract-compliance-kb": {
        "description": "Contract compliance requirements and obligations knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-contract-compliance-ks",
                "description": "Compliance requirements and regulatory obligations",
                "index_name": "contract-compliance-doc-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    # ── RFP Analysis ──
    "macae-rfp-summary-kb": {
        "description": "RFP summary and requirements knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-rfp-summary-ks",
                "description": "RFP summaries and key requirements",
                "index_name": "macae-rfp-summary-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    "macae-rfp-risk-kb": {
        "description": "RFP risk assessment knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-rfp-risk-ks",
                "description": "RFP risk factors and mitigation data",
                "index_name": "macae-rfp-risk-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
    "macae-rfp-compliance-kb": {
        "description": "RFP compliance requirements knowledge base",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "macae-rfp-compliance-ks",
                "description": "RFP compliance and regulatory requirements",
                "index_name": "macae-rfp-compliance-index",
                "searchable_fields": ["content", "title"],
            },
        ],
    },
}


def _put_semantic_config(index_name: str, searchable_fields: list[str], headers: dict) -> None:
    """Ensure the index has a semantic configuration for the KB."""
    # GET current index definition
    url = f"{SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
    resp = httpx.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        print(f"  ⚠ Index '{index_name}' not found — skipping semantic config (create index first).")
        return
    resp.raise_for_status()
    index_def = resp.json()

    # Build semantic config
    content_fields = [{"fieldName": f} for f in searchable_fields]
    semantic_config = {
        "name": f"{index_name}-semantic-config",
        "prioritizedFields": {
            "titleField": {"fieldName": searchable_fields[0]} if searchable_fields else None,
            "prioritizedContentFields": content_fields,
            "prioritizedKeywordsFields": [],
        },
    }

    # Merge into index definition — reuse existing config name or create "default"
    semantic_search = index_def.get("semantic", {}) or {}
    existing_configs = semantic_search.get("configurations", []) or []

    # If configs exist, update the first one in place; otherwise create "default"
    if existing_configs:
        existing_configs[0]["prioritizedFields"] = semantic_config["prioritizedFields"]
        semantic_config_name = existing_configs[0]["name"]
    else:
        existing_configs.append(semantic_config)
        semantic_config_name = semantic_config["name"]

    semantic_search["configurations"] = existing_configs
    semantic_search["defaultConfiguration"] = semantic_config_name
    index_def["semantic"] = semantic_search

    # PUT updated index
    put_resp = httpx.put(url, headers=headers, json=index_def, timeout=30)
    if put_resp.status_code in (200, 204):
        print(f"  ✓ Semantic config on '{index_name}' updated.")
    else:
        print(f"  ✗ Failed to update semantic config on '{index_name}': {put_resp.status_code}")
        print(f"    {put_resp.text[:200]}")


def _create_knowledge_source(
    kb_name: str,
    source_name: str,
    description: str,
    index_name: str,
    headers: dict,
) -> None:
    """Create a knowledge source (top-level, then referenced by KB)."""
    url = f"{SEARCH_ENDPOINT}/knowledgesources/{source_name}?api-version={KB_API_VERSION}"
    body = {
        "name": source_name,
        "kind": "searchIndex",
        "description": description,
        "searchIndexParameters": {
            "searchIndexName": index_name,
        },
    }
    resp = httpx.put(url, headers=headers, json=body, timeout=30)
    if resp.status_code in (200, 201, 204):
        print(f"  ✓ Knowledge source '{source_name}' created/updated.")
    elif resp.status_code == 409:
        print(f"  - Knowledge source '{source_name}' already exists (skipped).")
    else:
        print(f"  ✗ Failed to create knowledge source '{source_name}': {resp.status_code}")
        print(f"    {resp.text[:200]}")


def _create_knowledge_base(kb_name: str, kb_def: dict, headers: dict) -> None:
    """Create the knowledge base itself (skip if 409)."""
    url = f"{SEARCH_ENDPOINT}/knowledgebases/{kb_name}?api-version={KB_API_VERSION}"
    body: dict = {
        "name": kb_name,
        "description": kb_def["description"],
        "knowledgeSources": [{"name": s["name"]} for s in kb_def["sources"]],
    }
    if kb_def.get("model"):
        body["models"] = [kb_def["model"]]

    resp = httpx.put(url, headers=headers, json=body, timeout=30)
    if resp.status_code in (200, 201, 204):
        print(f"  ✓ Knowledge base '{kb_name}' created/updated.")
    elif resp.status_code == 409:
        print(f"  - Knowledge base '{kb_name}' already exists (skipped).")
    else:
        print(f"  ✗ Failed to create knowledge base '{kb_name}': {resp.status_code}")
        print(f"    {resp.text[:200]}")


def _parse_only_filter() -> set[str] | None:
    """Optional CLI filter: --only kb1,kb2  → only process those KB names."""
    for i, arg in enumerate(sys.argv[1:], start=1):
        if arg == "--only" and i + 1 < len(sys.argv):
            return {n.strip() for n in sys.argv[i + 1].split(",") if n.strip()}
        if arg.startswith("--only="):
            return {n.strip() for n in arg.split("=", 1)[1].split(",") if n.strip()}
    return None


def main() -> None:
    """Provision all knowledge bases."""
    print(f"Search endpoint: {SEARCH_ENDPOINT}")
    print(f"AI services endpoint: {AI_SERVICES_ENDPOINT or '(not set — KB will have no model)'}")

    only_filter = _parse_only_filter()
    if only_filter is not None:
        print(f"Filter (--only): {sorted(only_filter)}")

    headers = _get_auth_headers()
    print()

    for kb_name, kb_def in KNOWLEDGE_BASES.items():
        if only_filter is not None and kb_name not in only_filter:
            continue
        print(f"── {kb_name} ──")

        # Step 1: Ensure semantic configs on each source index
        for source in kb_def["sources"]:
            _put_semantic_config(source["index_name"], source["searchable_fields"], headers)

        # Step 2: Create knowledge sources
        for source in kb_def["sources"]:
            _create_knowledge_source(
                kb_name=kb_name,
                source_name=source["name"],
                description=source["description"],
                index_name=source["index_name"],
                headers=headers,
            )

        # Step 3: Create the knowledge base
        _create_knowledge_base(kb_name, kb_def, headers)
        print()

    print("Done.")


if __name__ == "__main__":
    main()

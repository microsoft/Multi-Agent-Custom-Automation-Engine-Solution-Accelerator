"""Create RemoteTool connections in the AI Foundry project for each Knowledge Base.

Each KB needs a project connection so that MCPTool can authenticate to the KB MCP
endpoint using the project's managed identity (ProjectManagedIdentity auth type).

Connection naming convention: "{kb_name}-mcp"
Target URL pattern: "{search_endpoint}/knowledgebases/{kb_name}/mcp?api-version=2025-11-01-preview"

Usage:
    python infra/scripts/seed_kb_connections.py

Requires in src/backend/.env (or environment):
  - AZURE_AI_SEARCH_ENDPOINT
  - AZURE_AI_PROJECT_ENDPOINT  (the full project endpoint URL)

Optional (preferred — used to construct the project ARM resource ID directly,
avoiding fragile data-plane discovery that fails for service principals on
fresh deployments):
  - AI_FOUNDRY_RESOURCE_ID    (the AI Foundry / Cognitive Services account ARM id)
  - AZURE_AI_PROJECT_NAME     (the project name under the account)
  - AZURE_AI_PROJECT_RESOURCE_ID (explicit full project ARM id; overrides the above)
  - AZURE_AI_SUBSCRIPTION_ID  (or AZURE_SUBSCRIPTION_ID)
  - AZURE_AI_RESOURCE_GROUP   (or AZURE_RESOURCE_GROUP)

Authentication: DefaultAzureCredential — caller needs Contributor on the AI project.
Idempotent: PUTs connections (creates or updates).
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load .env from src/backend/ (override=False so env vars set by post_deploy.ps1 take precedence)
_backend_env = Path(__file__).parent.parent / "src" / "backend" / ".env"
load_dotenv(str(_backend_env), override=False)

SEARCH_ENDPOINT = os.environ.get("AZURE_AI_SEARCH_ENDPOINT", "").rstrip("/")
PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").rstrip("/")

if not SEARCH_ENDPOINT:
    print("ERROR: AZURE_AI_SEARCH_ENDPOINT must be set.")
    sys.exit(1)
if not PROJECT_ENDPOINT:
    print("ERROR: AZURE_AI_PROJECT_ENDPOINT must be set.")
    sys.exit(1)

KB_API_VERSION = "2025-11-01-preview"

# Dynamically import KB names from seed_knowledge_bases.py to stay in sync automatically.
try:
    from seed_knowledge_bases import KNOWLEDGE_BASES
    KB_NAMES = list(KNOWLEDGE_BASES.keys())
except ImportError:
    # Fallback: hardcoded list (kept for environments where import path differs)
    KB_NAMES = [
        # Retail Customer Satisfaction
        "macae-retail-customer-kb",
        "macae-retail-orders-kb",
        # Content Generation
        "macae-content-gen-products-kb",
        # Contract Compliance
        "macae-contract-summary-kb",
        "macae-contract-risk-kb",
        "macae-contract-compliance-kb",
        # RFP Evaluation
        "macae-rfp-summary-kb",
        "macae-rfp-risk-kb",
        "macae-rfp-compliance-kb",
    ]


def _parse_project_ids(project_endpoint: str) -> tuple[str, str, str, str]:
    """Extract subscription, resource group, account, and project from project endpoint.

    Endpoint format:
      https://{account}.services.ai.azure.com/api/projects/{project}
    We need to resolve the ARM resource ID. Use the discovery endpoint.
    """
    # The project endpoint looks like:
    # https://aif-macaetas273o4exp.services.ai.azure.com/api/projects/proj-macaetas273o4exp
    # We'll call the project properties endpoint to get the resource ID.
    return project_endpoint


def _get_management_headers(credential: DefaultAzureCredential) -> dict:
    """Get headers for ARM management plane."""
    token = credential.get_token("https://management.azure.com/.default")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.token}",
    }


def _get_project_headers(credential: DefaultAzureCredential) -> dict:
    """Get headers for AI project data plane."""
    token = credential.get_token("https://management.azure.com/.default")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.token}",
    }


def _discover_project_resource_id(credential: DefaultAzureCredential) -> str:
    """Call the project endpoint to discover the ARM resource ID."""
    # Use the data-plane to get project info
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }
    # The project properties endpoint
    url = f"{PROJECT_ENDPOINT}?api-version=2024-07-01-preview"
    resp = httpx.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        resource_id = data.get("id", "")
        if resource_id:
            return resource_id
    # Fallback: parse from existing connection
    return ""


def _build_project_resource_id_from_env() -> str:
    """Construct the project ARM resource ID from environment variables.

    Preferred resolution order:
      1. AZURE_AI_PROJECT_RESOURCE_ID (explicit override)
      2. AI_FOUNDRY_RESOURCE_ID + AZURE_AI_PROJECT_NAME
      3. (subscription, resource group) + (account, project) parsed from PROJECT_ENDPOINT

    Returns empty string if it cannot be constructed.
    """
    explicit = os.environ.get("AZURE_AI_PROJECT_RESOURCE_ID", "").strip().rstrip("/")
    if explicit:
        return explicit

    foundry_id = os.environ.get("AI_FOUNDRY_RESOURCE_ID", "").strip().rstrip("/")
    project_name_env = os.environ.get("AZURE_AI_PROJECT_NAME", "").strip()

    # Parse account name and project name from the project endpoint as a fallback.
    parsed = urlparse(PROJECT_ENDPOINT) if PROJECT_ENDPOINT else None
    parsed_account = ""
    parsed_project = ""
    if parsed and parsed.hostname:
        parsed_account = parsed.hostname.split(".", 1)[0]
        path_parts = [p for p in (parsed.path or "").split("/") if p]
        if path_parts:
            parsed_project = path_parts[-1]

    project_name = project_name_env or parsed_project

    # Path 2: foundry resource id + project name
    if foundry_id and project_name:
        # Ensure the id points to the account (not the project itself) before appending.
        if "/projects/" in foundry_id.lower():
            return foundry_id
        return f"{foundry_id}/projects/{project_name}"

    # Path 3: build from sub + rg + parsed account/project
    sub = (
        os.environ.get("AZURE_AI_SUBSCRIPTION_ID")
        or os.environ.get("AZURE_SUBSCRIPTION_ID")
        or ""
    ).strip()
    rg = (
        os.environ.get("AZURE_AI_RESOURCE_GROUP")
        or os.environ.get("AZURE_RESOURCE_GROUP")
        or ""
    ).strip()
    if sub and rg and parsed_account and project_name:
        return (
            f"/subscriptions/{sub}/resourceGroups/{rg}"
            f"/providers/Microsoft.CognitiveServices/accounts/{parsed_account}"
            f"/projects/{project_name}"
        )

    return ""


def _create_connection_via_arm(
    resource_id: str, connection_name: str, target_url: str, credential: DefaultAzureCredential
) -> bool:
    """Create or update a RemoteTool connection via ARM REST API."""
    # ARM endpoint for connections:
    # PUT https://management.azure.com{resource_id}/connections/{name}?api-version=2025-04-01-preview
    arm_url = f"https://management.azure.com{resource_id}/connections/{connection_name}?api-version=2025-04-01-preview"

    body = {
        "properties": {
            "category": "RemoteTool",
            "target": target_url,
            "authType": "ProjectManagedIdentity",
            "useWorkspaceManagedIdentity": True,
            "isSharedToAll": True,
            "audience": "https://search.azure.com",
            "metadata": {
                "ApiType": "Azure",
            },
        }
    }

    headers = _get_management_headers(credential)
    resp = httpx.put(arm_url, json=body, headers=headers, timeout=30)
    if resp.status_code in (200, 201):
        return True
    elif resp.status_code == 409:
        # Already exists — treat as success
        return True
    else:
        print(f"  ✗ Failed ({resp.status_code}): {resp.text[:300]}")
        return False


def _parse_only_filter() -> set[str] | None:
    """Optional CLI filter: --only kb1,kb2  → only process those KB names."""
    for i, arg in enumerate(sys.argv[1:], start=1):
        if arg == "--only" and i + 1 < len(sys.argv):
            return {n.strip() for n in sys.argv[i + 1].split(",") if n.strip()}
        if arg.startswith("--only="):
            return {n.strip() for n in arg.split("=", 1)[1].split(",") if n.strip()}
    return None


def main() -> None:
    """Provision RemoteTool connections for all knowledge bases."""
    only_filter = _parse_only_filter()
    selected_kbs = [k for k in KB_NAMES if only_filter is None or k in only_filter]

    print(f"Search endpoint: {SEARCH_ENDPOINT}")
    print(f"Project endpoint: {PROJECT_ENDPOINT}")
    print(f"Knowledge bases: {len(selected_kbs)}{' (filtered)' if only_filter is not None else ''}")
    print()

    credential = DefaultAzureCredential()

    # Resolve the project ARM resource ID.
    # Preferred path: build it directly from environment variables exported by
    # post_deploy.{sh,ps1} (these come from azd env / deployment outputs). This
    # avoids fragile data-plane discovery that fails for service principals on
    # fresh deployments where no connections exist yet.
    print("Resolving project resource ID...")
    resource_id = _build_project_resource_id_from_env()
    if resource_id:
        print(f"  Using project resource ID from environment: {resource_id}")
    else:
        print("  Env-based resolution unavailable. Trying data-plane discovery...")
        resource_id = _discover_project_resource_id(credential)
        if not resource_id:
            # Last-resort: parse from any existing connection.
            print("  Could not discover via data-plane. Trying existing connection...")
            try:
                from azure.ai.projects import AIProjectClient

                client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
                try:
                    connections = list(client.connections.list())
                except Exception as exc:  # noqa: BLE001
                    print(f"  Connection list failed: {exc}")
                    connections = []
                finally:
                    client.close()
                if connections:
                    # Format: /subscriptions/.../connections/name
                    conn_id = connections[0].id
                    resource_id = conn_id.rsplit("/connections/", 1)[0]
            except Exception as exc:  # noqa: BLE001
                print(f"  AIProjectClient fallback failed: {exc}")

    if not resource_id:
        print("ERROR: Could not determine project ARM resource ID.")
        print(
            "  Set one of the following so the script can build the resource ID:\n"
            "    - AZURE_AI_PROJECT_RESOURCE_ID (full ARM id), OR\n"
            "    - AI_FOUNDRY_RESOURCE_ID + AZURE_AI_PROJECT_NAME, OR\n"
            "    - AZURE_AI_SUBSCRIPTION_ID + AZURE_AI_RESOURCE_GROUP + AZURE_AI_PROJECT_ENDPOINT."
        )
        sys.exit(1)

    print(f"  Project resource ID: {resource_id}")
    print()

    success_count = 0
    for kb_name in selected_kbs:
        connection_name = f"{kb_name}-mcp"
        target_url = f"{SEARCH_ENDPOINT}/knowledgebases/{kb_name}/mcp?api-version={KB_API_VERSION}"

        print(f"── {connection_name} ──")
        print(f"  Target: {target_url}")

        ok = _create_connection_via_arm(resource_id, connection_name, target_url, credential)
        if ok:
            print(f"  ✓ Connection '{connection_name}' ready.")
            success_count += 1
        print()

    credential.close()
    print(f"Done — {success_count}/{len(selected_kbs)} connections provisioned.")
    if success_count < len(selected_kbs):
        sys.exit(1)


if __name__ == "__main__":
    main()

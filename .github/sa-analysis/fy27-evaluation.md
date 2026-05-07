# MACE FY27 Principle Evaluation

**SA**: Multi-Agent Custom Automation Engine Solution Accelerator  
**Repository**: https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator  
**Surveyed commit**: `92b0f85e`

## Scorecard

| Principle | Score | Rationale |
|---|---:|---|
| P1: Data-First Architecture | 4 / 5 | Team behavior and demo data are externalized in `data/agent_teams/*.json` and `data/datasets/**`, with scripted Blob upload and Azure AI Search indexing. It is not a 5 because schema contracts are implicit in JSON/CSV/PDF shapes and new data packs are not auto-discovered by the existing upload script. |
| P2: Composable Integration Facades | 3 / 5 | FastMCP services use a clear `Domain` enum, `MCPToolBase`, and factory pattern. Core Azure integrations for Search, Cosmos, OpenAI/Foundry, and storage are still direct service integrations without interchangeable mocks or facade adapters. |
| P3: Configuration Over Custom Code | 4 / 5 | Use-case behavior is mostly JSON-configured: agent personas, tool flags, RAG index names, reasoning model selection, and starting tasks are in team configs. The score is capped by hardcoded frontend reserved team IDs/names and upload script enumeration for only five packaged teams. |
| P4: Production-Mindful, POC-Ready Standards | 4 / 5 | The repo includes Bicep/AVM IaC, WAF parameters, managed identity, monitoring hooks, Container Apps, App Service, Dockerfiles, azd metadata, and deployment docs. Gaps remain around per-adaptation cost profiles, fully automated generated-team activation, and formal sample-data reset/runbook separation. |

**Total: 15 / 20 - Tier 2 (high feasibility, moderate activation hardening needed).**

## Four-Layer Mapping

| Layer | MACE components |
|---|---|
| Stable Core | `src/backend/v4/orchestration/`, `src/backend/v4/magentic_agents/`, `src/backend/auth/`, `src/backend/middleware/`, `src/mcp_server/core/factory.py`, `infra/main.bicep`, `infra/main_custom.bicep`, React app shell. |
| Configurable Layer | `data/agent_teams/*.json`, agent `system_message`, `agents[].index_name`, capability flags, model deployment names, `src/App/src/models/Team.tsx`, runtime env settings. |
| Use Case Packs | New team JSON under `data/agent_teams/`, datasets under `data/datasets/<usecase-or-industry>/`, optional MCP service under `src/mcp_server/services/`, optional UI wording updates. |
| Customer Edge | Customer datasets, real Search/Blob/Cosmos data, tenant auth, private networking, customer-specific MCP systems, production branding, and operational policy. |

## Adapter Recommendations

### `customize-use-case`

Primary surface: `data/agent_teams/<usecase>.json`, with optional `data/datasets/<usecase>/` and optional `src/mcp_server/services/<domain>_service.py`.

The skill must read existing team examples before generating. It should reserve default IDs/names from `TeamSelector.tsx`, keep generated teams at six agents or fewer, satisfy backend required fields, and preserve frontend contract expectations for `starting_tasks`.

### `adapt-for-industry`

Primary runtime surface: `data/agent_teams/<industry>_<scenario>.json` plus `data/datasets/<industry>/`. A planning bundle under `data/industry_packs/<industry>/` can be generated for documentation and handoff, but activation must promote the team config and datasets into MACE's real runtime upload/indexing paths.

The skill should create explicit schema mapping documentation because MACE schemas are implicit in team JSON and dataset headers. It must include industry compliance notes and a data-swap handoff that delegates cloud mutation, Blob overwrite, Search reindexing, and sample/demo reset to `deploy-adaptation`.

### `deploy-adaptation`

Primary activation surfaces:

- `azure.yaml` and `azure_custom.yaml`
- `infra/main.bicep`, `infra/main_custom.bicep`, parameter files, and AVM modules
- `infra/scripts/selecting_team_config_and_data.sh`
- `infra/scripts/Selecting-Team-Config-And-Data.ps1`
- `infra/scripts/index_datasets.py`
- `infra/scripts/upload_team_config.py`
- `data/datasets/**`
- Azure AI Search indexes, Blob containers, and Cosmos DB team/session state

The deployment skill must require environment proof, validation, sample/demo ownership proof, rollback/snapshot planning, and explicit confirmation before any reset, delete, overwrite, index recreation, or hook rerun. Cosmos reset is especially sensitive because it can delete user/session state; skip it unless the user explicitly scopes a demo-only container or record set.

## Workarounds for Gaps

| Gap | Adapter workaround |
|---|---|
| Implicit schemas | Generate `SCHEMA_MAPPING.md` and validate team JSON plus dataset headers before activation. |
| Upload script enumerates only packaged teams | Prefer UI/API upload for generated teams, or intentionally patch `upload_team_config.py` to discover approved generated files. |
| Search indexes are manually named | Require generated `index_name` values to match `macae-<domain>-<entity>-index` and document Blob container/index mapping. |
| UI defaults are hardcoded | Read `TeamSelector.tsx` reserved IDs/names before generation and hard-fail collisions. |
| Cloud reset risk | Route sample/demo reset, Blob overwrite, Search reindex, and Cosmos cleanup through `deploy-adaptation` only. |


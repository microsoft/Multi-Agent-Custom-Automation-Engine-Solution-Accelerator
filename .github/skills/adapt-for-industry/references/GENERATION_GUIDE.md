# MACE Industry Adaptation Guide

## Runtime Reality

The current Microsoft MACE clone does not auto-discover `data/industry_packs/`. Runtime activation uses:

- `data/agent_teams/*.json` for team configs.
- `data/datasets/**` for sample/demo data.
- UI/API upload through `/api/v4/upload_team_config`.
- `infra/scripts/index_datasets.py` for Azure AI Search index creation/update.
- `infra/scripts/selecting_team_config_and_data.sh` for packaged demos, currently hardcoded to five default teams.

Generate industry artifacts directly for those runtime paths, and optionally include a documented planning bundle for portability.

## Recommended Output Tree

```text
data/agent_teams/<industry>_<scenario>.json
data/datasets/<industry>/<entity>.csv
docs/adaptations/<industry>/README.md
docs/adaptations/<industry>/SCHEMA_MAPPING.md
docs/adaptations/<industry>/DATA_SWAP_GUIDE.md
docs/adaptations/<industry>/ACTIVATION_HANDOFF.md
docs/adaptations/<industry>/mcp_recommendations.md
```

## Industry Knowledge Starters

| Industry | Common entities | Compliance reminders |
|---|---|---|
| Healthcare | patients, encounters, appointments, claims, care gaps, providers | HIPAA, PHI minimization, HL7/FHIR mapping, audit trails. |
| Financial services | customers, accounts, transactions, cases, risk alerts, products | SOX, PCI-DSS, KYC/AML, fraud controls, retention. |
| Manufacturing | assets, work orders, suppliers, parts, quality events, shipments | ISO quality standards, supply chain traceability, safety incidents. |
| Legal | matters, contracts, clauses, obligations, risks, evidence | Privilege, eDiscovery, retention, jurisdiction, legal-advice disclaimer. |
| Education | students, courses, enrollments, interventions, advisors, outcomes | FERPA, accessibility, consent, student data minimization. |
| Public sector | constituents, services, cases, programs, benefits, compliance reviews | FedRAMP, accessibility, records retention, privacy impact. |
| Energy and utilities | assets, outages, inspections, work orders, customers, grid events | NERC CIP, safety, critical infrastructure, outage communications. |

## Team Design

Use 2-5 specialist agents plus `ProxyAgent` where clarification may be needed. Keep the total at six or fewer because the frontend upload UI rejects larger teams.

Recommended agent types:

- Domain data agent: RAG over the main entity dataset.
- Transaction/event agent: RAG over interactions, orders, claims, work orders, incidents, or cases.
- Compliance/risk agent: RAG or reasoning over regulations and policy checks.
- Recommendation/reasoning agent: `use_reasoning: true`, `deployment_name: "o4-mini"`, no direct data source unless needed.
- Tool/action agent: `use_mcp: true` only when a matching registered MCP service exists.
- `ProxyAgent`: final entry for clarification and human handoff.

## Dataset and Schema Rules

For each generated CSV:

- 10-20 synthetic rows.
- Header names in snake_case or lower camel case consistently within the file.
- Stable IDs and foreign keys that match across files.
- Dates in ISO format.
- No real customer data, secrets, SSNs, MRNs, account numbers, student IDs, or production identifiers.
- Sensitivity annotations in `SCHEMA_MAPPING.md`.

Search index names should follow:

```text
macae-<industry>-<entity>-index
```

## Data Swap Guide Requirements

`DATA_SWAP_GUIDE.md` is planning guidance only. It may describe how to map source columns, stage files locally, validate synthetic samples, and prepare an activation request. It must delegate all mutating operations to `deploy-adaptation`, including:

- Blob upload or overwrite.
- Search indexing/reindexing.
- Search document deletion or index recreation.
- Cosmos DB changes.
- Postdeploy hook reruns.
- Container rebuild or Azure redeploy.
- Sample/demo reset.

## UI Terminology

For industry terminology updates, prefer display-only edits:

- Team name and description.
- Agent names and descriptions.
- Starting task names/prompts.
- Home prompt placeholder or helper text.
- Team selector upload/help/error copy.
- Optional disclaimer for regulated industries.

Do not rename backend/API/internal keys such as `team_id`, `agents`, `starting_tasks`, `index_name`, or `use_rag` unless the backend and frontend contract files are updated together and validated.

## Activation Handoff

The handoff to `deploy-adaptation` should include:

- Generated files and changed paths.
- Target environment.
- Whether activation is data-only, backend-only, frontend-only, infrastructure-only, or mixed.
- Search indexes and Blob/container paths needed.
- Whether any existing sample/demo stores are reused.
- Snapshot/rollback plan.
- Explicit confirmation needed before reset or overwrite.


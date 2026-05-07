# MACE Use-Case Generation Guide

## Native MACE Output Shape

The runtime surface is `data/agent_teams/<usecase>.json`. Optional data lives under `data/datasets/<usecase>/`. Optional MCP tools live under `src/mcp_server/services/`, but adding a service file alone is not enough; the `Domain` enum and service registration path must be updated and redeployed.

## Archetypes

| Archetype | Existing examples | Use when | Generated shape |
|---|---|---|---|
| MCP workflow | `hr.json`, `marketing.json` | Agents perform actions through tools. | 1-3 MCP agents plus `ProxyAgent`; `use_mcp: true`; no `index_name`. |
| Retail-style RAG | `retail.json` | Agents answer from structured customer/order data. | RAG agents with `macae-<usecase>-<entity>-index`, a reasoning agent if synthesis is needed, and `ProxyAgent`. |
| Document-analysis RAG | `rfp_analysis_team.json`, `contract_compliance_team.json` | Agents analyze PDF/DOCX document sets. | Summary/risk/compliance-style agents mapped to Search indexes and document folders. |
| Hybrid | Combine above | Scenario needs data retrieval and actions. | Keep at six agents or fewer; use MCP only where service code already exists or is explicitly added. |

## Team JSON Skeleton

Use valid JSON, not JSONC. Preserve string keys used by backend and frontend.

```json
{
  "id": "usecase-unique-local-id",
  "team_id": "team-usecase-unique-id",
  "name": "Use Case Team Name",
  "status": "visible",
  "created": "",
  "created_by": "",
  "deployment_name": "gpt-4.1-mini",
  "agents": [
    {
      "input_key": "",
      "type": "",
      "name": "DomainDataAgent",
      "deployment_name": "gpt-4.1-mini",
      "icon": "",
      "system_message": "Describe the agent role, safe behavior, data source, escalation rules, and response constraints.",
      "description": "Routing description used by the orchestrator.",
      "use_rag": true,
      "use_mcp": false,
      "use_bing": false,
      "use_reasoning": false,
      "index_name": "macae-usecase-domain-index",
      "index_foundry_name": "",
      "coding_tools": false
    },
    {
      "input_key": "",
      "type": "",
      "name": "ProxyAgent",
      "deployment_name": "",
      "icon": "",
      "system_message": "",
      "description": "",
      "use_rag": false,
      "use_mcp": false,
      "use_bing": false,
      "use_reasoning": false,
      "index_name": "",
      "index_foundry_name": "",
      "coding_tools": false
    }
  ],
  "protected": false,
  "description": "What this team does and who it helps.",
  "logo": "",
  "plan": "",
  "starting_tasks": [
    {
      "id": "task-1",
      "name": "Representative task",
      "prompt": "A realistic prompt that demonstrates the use case.",
      "created": "",
      "creator": "",
      "logo": ""
    }
  ]
}
```

## Dataset Guidance

For RAG use cases, create one folder per logical index:

```text
data/datasets/<usecase>/<entity>/
```

or a flat folder when the scenario is simple. Include a README describing:

- Entity purpose.
- File type and columns.
- Which agent and `index_name` consumes it.
- Whether data is synthetic.
- Any fields that are sensitive and must not contain real customer data in demos.

Generate 10-20 synthetic rows per CSV entity when creating sample data. Use fake names, IDs, dates, and codes. Do not include real customer data or secrets.

## MCP Guidance

If the use case needs actions, first check whether an existing service domain in `src/mcp_server/services/` can serve the action. If not, propose:

1. A new `Domain` enum value in `src/mcp_server/core/factory.py`.
2. A new service file under `src/mcp_server/services/`.
3. Registration in the MCP server startup path.
4. Unit tests or manual tool-call tests.
5. Rebuild/redeploy through `deploy-adaptation`.

Do not mark an agent `use_mcp: true` unless the matching MCP service exists or is generated and registered in the same change set.

## UI and Contract Guidance

The UI displays generated team fields from `Team.tsx` and `HomeInput.tsx`. Preserve stable keys and change display copy only:

- Stable keys: `team_id`, `agents`, `starting_tasks`, `name`, `description`, `prompt`.
- Display copy: team name, agent descriptions, prompt-card names, placeholders, helper text, disclaimers.

After UI changes, run:

```bash
cd src/App
npm ci
npm run build
```

Then smoke-test the home page, team selector, uploaded team card, starting task cards, and plan creation.

## Activation Handoff

Generated use-case files are local until activated. Uploads, Blob writes, Search index creation, reindexing, script reruns, and redeployments are handled by `deploy-adaptation` after validation, environment proof, and sample/demo ownership checks.


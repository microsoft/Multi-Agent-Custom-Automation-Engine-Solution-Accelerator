---
name: deploy-adaptation
description: Safely activate, deploy, reindex, smoke test, or roll back MACE use-case and industry adaptations using the repo's actual Bicep, azd, Container Apps, App Service, Search, Blob, Cosmos, and UI evidence.
---

# Deploy Adaptation for MACE

Use this skill after `customize-use-case` or `adapt-for-industry` has generated or modified files. MACE has a mixed deployment surface: backend and MCP run as Container Apps, the frontend is App Service based, Bicep/AVM defines cloud resources, `azure.yaml` and `azure_custom.yaml` provide azd evidence, and sample team/data activation is handled by scripts under `infra/scripts/`.

This skill never treats destructive operations as the default path. Before Blob overwrite, Search reindex, Search document deletion, sample-data hook rerun, Cosmos cleanup, resource deletion, or redeploy, prove the environment, validate files, plan rollback, and get explicit confirmation.

For detailed decision tables, read [references/DEPLOYMENT_GUIDE.md](references/DEPLOYMENT_GUIDE.md).

## Step 1 - Read Deployment Evidence

Read these files before recommending commands:

- `.github/sa-analysis/architecture-survey.md`
- `.github/sa-analysis/fy27-evaluation.md`
- `.github/skills/customize-use-case/`
- `.github/skills/adapt-for-industry/`
- `azure.yaml`
- `azure_custom.yaml`
- `infra/main.bicep`
- `infra/main_custom.bicep`
- `infra/main.parameters.json`
- `infra/main.waf.parameters.json`
- `infra/scripts/selecting_team_config_and_data.sh`
- `infra/scripts/Selecting-Team-Config-And-Data.ps1`
- `infra/scripts/index_datasets.py`
- `infra/scripts/upload_team_config.py`
- `src/backend/Dockerfile`
- `src/mcp_server/Dockerfile`
- `src/App/Dockerfile`
- UI surfaces in `src/App/src/**`
- Data surfaces in `data/agent_teams/**`, `data/datasets/**`, and generated `docs/adaptations/**`

If evidence is missing or stale, pause and name the missing evidence. Do not invent Azure commands.

## Step 2 - Gather Request and Changed Paths

Ask the user to confirm:

1. Target azd environment, subscription, tenant, resource group, and deployment window.
2. Adaptation source: use-case skill, industry skill, manual edits, or branch.
3. Changed files or commit range.
4. Whether activation should upload team JSON, upload datasets, index Search, deploy code, update infrastructure, or only validate.
5. Whether any reset, overwrite, delete, reindex, script rerun, or Cosmos cleanup is requested.
6. Whether target stores are demo/sample-only.

Inspect `git status --short` and the named files. Do not read secrets or print secret values.

## Step 3 - Classify Impact

Classify exactly one impact:

| Impact | MACE examples |
|---|---|
| `data-only` | `data/agent_teams/*.json`, generated docs, `data/datasets/**`, team upload only, Search documents only. |
| `backend-only` | `src/backend/**`, `src/mcp_server/**`, MCP service registration, backend/MCP Dockerfiles. |
| `frontend-only` | `src/App/**` display copy, team selector UI, model types, static assets, frontend build config only. |
| `infrastructure-only` | `infra/**`, `azure.yaml`, `azure_custom.yaml`, image tags, identity, networking, resource SKU/settings. |
| `mixed` | More than one area, UI plus backend/API contract changes, data plus infra/Search schema, or any uncertainty. |

For UI changes, require frontend build and smoke checks only when changed paths touch `src/App/**` or surveyed UI/frontend surfaces. Keep backend/API/internal keys stable unless an intentional contract update is documented and validated.

## Step 4 - Preflight

Before activation or deployment:

```bash
az account show --query '{tenant:tenantId, subscription:id, name:name}' -o table
azd env list
azd env get-values
git status --short
```

Check Bicep when infra may change:

```bash
az bicep build --file infra/main.bicep --stdout > /dev/null
az bicep build --file infra/main_custom.bicep --stdout > /dev/null
```

Do not print secrets from azd env output. Confirm the target is non-production or approved production.

## Step 5 - Validate Before Deploy

Run the relevant validators:

```bash
python3 .github/skills/customize-use-case/validate.py
python3 .github/skills/adapt-for-industry/validate.py
```

If UI changed:

```bash
cd src/App
npm ci
npm run build
```

If backend/MCP Python changed, run the repo's Python tests/lint only if dependencies are restored in the current environment. Stop on validation failure.

## Step 6 - Plan Sample/Demo Reset

For a new industry or data pack, inventory:

- Local files under `data/datasets/**`.
- Blob containers and prefixes used by the target scenario.
- Azure AI Search indexes such as `macae-retail-customer-index`, `macae-retail-order-index`, `macae-rfp-summary-index`, `macae-rfp-risk-index`, `macae-rfp-compliance-index`, and generated `macae-<industry>-<entity>-index` names.
- Cosmos DB team/session/plan records.
- Generated docs and handoff files.
- Postdeploy scripts that upload or index packaged demos.

Step 6 is planning only. Do not reset, delete, overwrite, purge, truncate, recreate, or rerun sample-data hooks here.

Require explicit confirmation with:

- exact reset target list,
- sample/demo ownership evidence,
- rollback/snapshot plan,
- reason the operation cannot be additive,
- immediate next load/index command.

If ownership is ambiguous or a store may contain customer data, require a sibling demo store, path, index, container, or data-owner approval.

## Step 7 - Activate and Deploy

Choose the narrowest safe activation:

- Team JSON only: upload through MACE UI or `/api/v4/upload_team_config`; do not rerun packaged-data scripts.
- Dataset/Search only: upload scoped sample/demo files, then run `index_datasets.py` for the specific target index.
- MCP/backend code: rebuild and deploy backend/MCP only after tests and image plan are clear.
- Frontend only: build frontend and deploy the frontend/App Service path only.
- Infrastructure: run Bicep/azd provision after compile and review.
- Mixed: order as validation -> confirmed reset if needed -> infra -> data/Search -> backend/MCP -> frontend -> smoke tests.

Destructive sample/demo reset, if confirmed, happens immediately before loading the replacement data and never earlier.

## Step 8 - Smoke Test and Rollback

Smoke checks:

- Frontend `/health` or root route responds.
- Backend health/API route responds.
- Team selector lists or accepts the generated team.
- Starting task cards reflect the adapted use case or industry.
- A representative prompt creates a plan with the intended `team_id`.
- RAG agents retrieve from the intended Search indexes.
- Old sample entities are absent only when a reset was explicitly confirmed.

Rollback uses the snapshot/plan from Step 6: restore previous team JSON, restore prior dataset files or Search documents, redeploy prior image tag, or revert infra/app changes. Avoid `azd down` except as an explicitly confirmed teardown of a disposable environment.

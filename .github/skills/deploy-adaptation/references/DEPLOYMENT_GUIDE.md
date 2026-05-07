# MACE Deployment Adaptation Guide

## Topology Evidence

MACE uses `publish.surface: mixed`.

| Service | Host | Evidence | Notes |
|---|---|---|---|
| backend | Container App | `infra/main.bicep`, `infra/main_custom.bicep`, `src/backend/Dockerfile` | API, orchestration, Search/Cosmos/OpenAI integrations. |
| mcp | Container App | `infra/main.bicep`, `infra/main_custom.bicep`, `src/mcp_server/Dockerfile` | FastMCP tool server. |
| frontend | App Service | `infra/main.bicep`, `infra/main_custom.bicep`, `src/App/Dockerfile`, `src/App/frontend_server.py` | React build served by FastAPI static server. |
| data/search activation | Scripts | `infra/scripts/selecting_team_config_and_data.sh`, `infra/scripts/index_datasets.py`, `infra/scripts/upload_team_config.py` | Uploads packaged demo teams and indexes sample files. |

`azure.yaml` has postdeploy instructions but no service map. `azure_custom.yaml` has explicit azd services for backend, mcp, and frontend. Confirm which azd file/workflow the environment uses before recommending `azd deploy <service>`.

## Impact to Command Mapping

| Impact | Validation | Activation/deploy guidance |
|---|---|---|
| data-only | Adapter validator, JSON parse, dataset/schema review | Upload generated team via UI/API. For datasets, upload only scoped demo files and run `index_datasets.py` for the specific target index after confirmation. |
| backend-only | Python compile/tests, container build check | Rebuild/deploy backend or MCP container only when image/tag path is proven by Bicep/azd evidence. |
| frontend-only | `cd src/App && npm ci && npm run build` | Deploy frontend/App Service path only. Smoke root page, team selector, and plan creation. |
| infrastructure-only | `az bicep build` for changed templates | Run provision/azd only after Bicep review. Do not rerun sample-data hooks unless their inputs changed and reset is confirmed. |
| mixed | All relevant validators and ordered plan | Infra -> data/Search -> backend/MCP -> frontend -> smoke tests, with reset immediately before replacement load only if confirmed. |

## Team Config Activation

The packaged script `infra/scripts/upload_team_config.py` enumerates five files:

- `hr.json`
- `marketing.json`
- `retail.json`
- `rfp_analysis_team.json`
- `contract_compliance_team.json`

Generated team configs are not automatically included. Use one of these explicit paths:

1. Upload through the frontend team selector.
2. POST the generated JSON to `/api/v4/upload_team_config` with the authenticated user headers used by the app.
3. Intentionally patch `upload_team_config.py` to discover an approved generated file list, validate, and redeploy.

Do not assume `selecting_team_config_and_data.sh` activates generated teams unless it has been reviewed and changed for that purpose.

## Search and Blob Activation

`index_datasets.py` creates or updates a Search index with fields `id`, `content`, and `title` from blobs in one container. The script can update an index, so prefer scoped document replacement and index update over index recreation.

Before upload/reindex:

1. Identify source local path.
2. Identify Blob container/prefix.
3. Identify Search index name.
4. Prove it is sample/demo-only.
5. Back up or export existing sample/demo documents when replacing.
6. Validate generated data and mapping docs.
7. Confirm overwrite/reset immediately before the operation.

Never upload synthetic data into a container or index that may contain customer data. Create a sibling demo container/index instead.

## Cosmos DB Safety

Cosmos stores team configurations, sessions, plans, and runtime state. It is not a normal data-swap target. Do not delete or reset Cosmos containers as part of a use-case or industry activation unless:

- the target container or records are confirmed demo-only,
- the user explicitly requests Cosmos cleanup,
- a backup/export exists,
- the exact records or partition scope are listed,
- validation has passed,
- the user confirms immediately before execution.

Prefer uploading a new team config and selecting it over deleting old team records.

## UI Smoke Checks

Run only when UI/frontend files changed:

```bash
cd src/App
npm ci
npm run build
```

Then verify:

- The home page loads.
- Team selector opens and upload/drop zone messages render.
- Generated team JSON uploads or client-side validation explains what is wrong.
- Team card shows intended name, description, and agent badges.
- Starting task cards show industry/use-case terms.
- Creating a plan sends the selected `team_id`.

## Rollback

Plan rollback before activation:

- Team config: restore previous JSON or select the previous team.
- Search docs: restore exported sample/demo documents or re-run the previous scoped sample upload.
- Blob data: restore previous demo files or prefix snapshot when available.
- Backend/MCP/frontend: redeploy previous known image tag or revert source and rebuild.
- Bicep/infra: revert Bicep/parameter changes and re-provision only after review.

Avoid `azd down` for rollback. It is a teardown command and requires explicit confirmation for a disposable environment.


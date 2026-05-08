# Industry Pack Generation and Redeploy Runbook

Use this runbook to generate, review, activate, smoke-test, and roll back a MACE industry pack for a GA/demo run. It is intentionally data-first: a normal industry pack changes `data/agent_teams/**`, `data/datasets/**`, and `docs/adaptations/**`; application code redeploy is only needed when source, infrastructure, or runtime settings changed.

## 0. Safety rules

- Do not paste secrets, tenant IDs, subscription IDs, connection strings, or full local paths into docs or tickets.
- Do not run delete/reset/overwrite/reindex commands until the exact target and rollback plan are approved.
- Do not make Cosmos DB public access the default fix. For GA, use private networking so backend/MCP can reach Cosmos, Storage, and Search through approved private paths.
- Prefer dedicated demo Blob containers and Search indexes for generated packs. Never mix synthetic demo data with customer data unless the owner explicitly approves the target.
- The packaged postdeploy scripts only know the built-in teams unless intentionally updated; custom packs should use scoped upload/index commands or UI/API upload.

## 1. Prerequisites

From the repository root:

```bash
azd version
az version
python3 --version
jq --version
```

Install script dependencies before upload/reindex work. `infra/scripts/index_datasets.py` imports Azure SDK packages from `infra/scripts/requirements.txt`.

```bash
python3 -m pip install -r infra/scripts/requirements.txt
```

Required access:

- Azure CLI and Azure Developer CLI authenticated to the target tenant.
- Contributor or narrower equivalent permissions on the target resource group.
- Data-plane access to the target Storage account and Azure AI Search service, or an approved private-network execution path.
- Browser access to the frontend App Service.

Repository validation commands:

```bash
python3 .github/skills/adapt-for-industry/validate.py
python3 .github/skills/customize-use-case/validate.py
```

## 2. Set run variables

Use placeholders until the deployment owner confirms real values.

```bash
export AZD_ENV_NAME="<env-name>"
export RESOURCE_GROUP="<resource-group>"
export FRONTEND_APP="<frontend-app>"
export BACKEND_APP="<backend-app>"
export MCP_APP="<mcp-app>"
export CONTAINER_APP_ENV="<container-app-env>"
export STORAGE_ACCOUNT="<storage-account>"
export SEARCH_SERVICE="<search-service>"
export COSMOS_ACCOUNT="<cosmos-account>"

export INDUSTRY="<industry>"
export SCENARIO="<scenario>"
export TEAM_ID="<team-id>"
export TEAM_JSON="data/agent_teams/<industry>_<scenario>.json"
export DATASET_ROOT="data/datasets/<industry>"
export FRONTEND_HOST="<frontend-app>.azurewebsites.net"
```

For API commands below, use the frontend `/config` response when possible:

```bash
APP="https://${FRONTEND_HOST}"
CONFIG=$(curl -fsS "$APP/config")
API_URL=$(printf '%s' "$CONFIG" | jq -r '.API_URL')
if [ "$API_URL" = "/api" ]; then API_URL="${APP}/api"; fi
```

`API_URL` should include `/api`, for example `https://<backend-host>/api`. When `/config` returns `/api`, normalize it to `https://<frontend-host>/api` for command-line smoke tests.

## 3. Generate the pack with `/adapt-for-industry`

In Copilot CLI, run the project skill and provide the target details:

```text
/adapt-for-industry
Target industry: <industry>
Sub-domain/scenario: <scenario>
Demo narrative: <what the GA/demo should prove>
Compliance posture: <HIPAA/SOX/NERC CIP/etc. or "none beyond normal demo safety">
Core entities and data shape: <entities, files, known columns>
Capabilities: <RAG-only | MCP-enabled | reasoning | hybrid>
Data policy: synthetic demo data only unless explicitly approved otherwise
```

Expected runtime artifacts:

```text
data/agent_teams/<industry>_<scenario>.json
data/datasets/<industry>/*.csv
docs/adaptations/<industry>/README.md
docs/adaptations/<industry>/SCHEMA_MAPPING.md
docs/adaptations/<industry>/DATA_SWAP_GUIDE.md
docs/adaptations/<industry>/ACTIVATION_HANDOFF.md
docs/adaptations/<industry>/mcp_recommendations.md
```

## 4. Review and validate generated artifacts

```bash
python3 -m json.tool "$TEAM_JSON"
python3 .github/skills/adapt-for-industry/validate.py
git status --short
git diff -- data/agent_teams data/datasets docs/adaptations
```

Review checklist:

- `team_id` is stable, unique, and not one of the default team IDs.
- Team has six agents or fewer.
- `starting_tasks` has 3-4 concise `name` values and complete `prompt` values.
- Every RAG agent has an `index_name` that matches the docs and intended Azure AI Search index.
- `ProxyAgent` is last when the team uses RAG or MCP.
- Dataset rows are synthetic or explicitly approved demo data.
- `SCHEMA_MAPPING.md` maps every dataset to a Search index and consuming agent.
- `ACTIVATION_HANDOFF.md` lists exact team JSON, dataset paths, index names, and smoke expectations.

## 5. Commit-ready artifact checklist

Before opening a PR or handing off for deployment:

- [ ] Only intended docs/data files changed for a data-only industry pack.
- [ ] No application code changed unless the task explicitly required it.
- [ ] No secrets, tenant IDs, subscription IDs, connection strings, or full local paths were added.
- [ ] Validation passed or failures are documented with owner/action.
- [ ] Rollback plan names the previous team config, Blob containers/prefixes, Search indexes, and app settings.
- [ ] Any destructive action is excluded from normal instructions and requires separate confirmation.

## 6. Deploy or select Azure resources

Select and prove the target environment first:

`azd env get-values` can print sensitive values. Keep its output in your terminal only; do not paste it into chat, docs, issues, or tickets.

```bash
azd auth login
azd env list
azd env select "$AZD_ENV_NAME"
az account show --query '{tenant:tenantId, subscription:id, name:name}' -o table
azd env get-values
az group show --name "$RESOURCE_GROUP" --query '{name:name, location:location, tags:tags}' -o json
```

If the environment does not exist yet, follow `docs/DeploymentGuide.md` and run:

```bash
azd up
```

If only a generated industry pack changed, do not redeploy application code by default. If backend, MCP, frontend, or infrastructure files also changed, validate those changes and use the narrowest deployment path. The normal deployment workflow can use a hook-only `azure.yaml`; the repo's local-code deploy path in `docs/DeploymentGuide.md` swaps the custom azd/Bicep files into the active names. Before any `azd deploy <service>`, verify the azd file currently active for your command contains the intended `services:` entries for `backend`, `mcp`, or `frontend`; do not infer service support from filename alone.

## 7. Private-networking preflight

Record network state before any upload, reindex, or smoke test:

```bash
az cosmosdb show -g "$RESOURCE_GROUP" -n "$COSMOS_ACCOUNT" --query '{publicNetworkAccess:publicNetworkAccess,ipRules:ipRules,virtualNetworkRules:virtualNetworkRules,privateEndpointConnections:privateEndpointConnections[].privateEndpoint.id}' -o json
az storage account show -g "$RESOURCE_GROUP" -n "$STORAGE_ACCOUNT" --query '{publicNetworkAccess:publicNetworkAccess,networkRuleSet:networkRuleSet}' -o json
az search service show -g "$RESOURCE_GROUP" -n "$SEARCH_SERVICE" --query '{publicNetworkAccess:publicNetworkAccess,networkRuleSet:networkRuleSet,hostingMode:hostingMode}' -o json
az containerapp env show -g "$RESOURCE_GROUP" -n "$CONTAINER_APP_ENV" --query '{name:name,infraSubnet:properties.vnetConfiguration.infrastructureSubnetId,publicNetworkAccess:properties.publicNetworkAccess,defaultDomain:properties.defaultDomain}' -o json
az containerapp show -g "$RESOURCE_GROUP" -n "$BACKEND_APP" --query '{fqdn:properties.configuration.ingress.fqdn,envId:properties.environmentId,outboundIpAddresses:properties.outboundIpAddresses}' -o json
az webapp vnet-integration list -g "$RESOURCE_GROUP" -n "$FRONTEND_APP" -o table
az webapp config appsettings list -g "$RESOURCE_GROUP" -n "$FRONTEND_APP" --query "[?name=='BACKEND_API_URL' || name=='PROXY_API_REQUESTS'].{name:name,value:value}" -o table
```

Decision points:

- If Cosmos `publicNetworkAccess` is `Disabled`, local data-plane upload/query failures may be expected. The backend must reach Cosmos through private networking.
- If Storage or Search public access is disabled, run upload/indexing from an approved network path. Do not temporarily enable public access unless the deployment owner explicitly approves a time-bound demo exception.
- If the backend Container App is private or IP-restricted, proxy mode is valid only when the frontend App Service has approved DNS, routing, and outbound access to `BACKEND_API_URL`. Prove that path before setting `PROXY_API_REQUESTS=true`; do not use public access as the workaround.

## 8. Upload datasets and reindex Azure AI Search

For RAG teams, create/update Search indexes before uploading the team JSON because `/api/v4/upload_team_config` validates referenced indexes.

Use one dedicated Blob container per Search index when possible. `infra/scripts/index_datasets.py` indexes every blob in the container into an index with fields `id`, `content`, and `title`.

Template for one index:

```bash
export BLOB_CONTAINER="<demo-container-for-this-index>"
export SEARCH_INDEX="macae-<industry>-<entity>-index"

az storage container create \
  --account-name "$STORAGE_ACCOUNT" \
  --name "$BLOB_CONTAINER" \
  --auth-mode login \
  --public-access off

az storage blob upload-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --destination "$BLOB_CONTAINER" \
  --source "$DATASET_ROOT" \
  --auth-mode login \
  --pattern "<file-or-pattern>" \
  --overwrite false

python3 infra/scripts/index_datasets.py "$STORAGE_ACCOUNT" "$BLOB_CONTAINER" "$SEARCH_SERVICE" "$SEARCH_INDEX"
```

Use `--overwrite true` only after confirming the container is demo-only and rollback is ready.
Reindexing a reused Search index may leave stale documents unless an approved cleanup/export plan exists. Dedicated demo containers and Search indexes are the safest default for GA/demo runs.

## 9. Upload and select the generated team

Pre-upload gate: do not run POST/DELETE commands until `/config` points to the approved backend/proxy for the target `RESOURCE_GROUP` and `BACKEND_APP`.

```bash
APP="https://${FRONTEND_HOST}"
CONFIG=$(curl -fsS "$APP/config")
API_URL=$(printf '%s' "$CONFIG" | jq -r '.API_URL')
if [ "$API_URL" = "/api" ]; then API_URL="${APP}/api"; fi
BACKEND_FQDN=$(az containerapp show -g "$RESOURCE_GROUP" -n "$BACKEND_APP" --query 'properties.configuration.ingress.fqdn' -o tsv)
printf 'API_URL=%s\nBACKEND_FQDN=%s\n' "$API_URL" "$BACKEND_FQDN"
az webapp config appsettings list -g "$RESOURCE_GROUP" -n "$FRONTEND_APP" --query "[?name=='BACKEND_API_URL' || name=='PROXY_API_REQUESTS'].{name:name,value:value}" -o table
```

Continue only if `API_URL` is the approved direct backend API (`https://<backend-host>/api`) or the approved frontend proxy (`https://<frontend-host>/api`) whose `BACKEND_API_URL` targets `BACKEND_APP`.

Preferred options:

1. Upload the JSON from the MACE UI team selector, then select the team.
2. Upload through the API after Search indexes exist:

Use only the signed-in operator's approved principal for `x-ms-client-principal-id` (for example, from `az ad signed-in-user show --query id -o tsv`). Do not spoof another user or paste real principal IDs into docs, issues, or tickets.

```bash
curl -fsS -X POST \
  -H "x-ms-client-principal-id: <user-principal-id>" \
  -F "file=@${TEAM_JSON};type=application/json" \
  "${API_URL}/v4/upload_team_config?team_id=${TEAM_ID}" | jq '{status, team_id, name}'
```

Then set the current team for smoke tests:

```bash
curl -fsS -X POST \
  -H "Content-Type: application/json" \
  -H "x-ms-client-principal-id: <user-principal-id>" \
  -d "{\"team_id\":\"${TEAM_ID}\"}" \
  "${API_URL}/v4/select_team" | jq '{status, team_id, message}'
```

If upload fails with "Search index validation failed", re-check the index names in `agents[].index_name`, confirm the indexes exist in the target Search service, and rerun the index step.
If upload fails with a model deployment error, confirm the named `deployment_name` values exist in the target Azure AI Foundry project before retrying.

## 10. Point frontend to the intended backend

Check the browser-facing config:

```bash
curl -fsS "https://${FRONTEND_HOST}/config" | jq .
```

For direct backend access, `BACKEND_API_URL` is the backend base URL without `/api`:

```bash
az webapp config appsettings set \
  -g "$RESOURCE_GROUP" \
  -n "$FRONTEND_APP" \
  --settings BACKEND_API_URL="https://<backend-host>" PROXY_API_REQUESTS="false"

az webapp restart -g "$RESOURCE_GROUP" -n "$FRONTEND_APP"
```

For private or IP-restricted backend access, proxy through the frontend:

Before enabling proxy mode, prove the frontend App Service has approved VNet/DNS/routing/outbound access to the backend URL:

```bash
az webapp vnet-integration list -g "$RESOURCE_GROUP" -n "$FRONTEND_APP" -o table
```

Only continue if the deployment owner has verified that `https://<backend-host>` resolves and routes from the frontend over the approved private path. Acceptable evidence includes DNS resolution and a backend health/API call from the frontend App Service console, Kudu/SSH, or another approved private execution path that uses the same routing as the frontend.

```bash
az webapp config appsettings set \
  -g "$RESOURCE_GROUP" \
  -n "$FRONTEND_APP" \
  --settings BACKEND_API_URL="https://<backend-host>" PROXY_API_REQUESTS="true"

az webapp restart -g "$RESOURCE_GROUP" -n "$FRONTEND_APP"
```

After restart, `/config` should show the intended `API_URL`.

## 11. Smoke-test backend and UI

Backend/API:

```bash
APP="https://${FRONTEND_HOST}"
curl -fsS "$APP/health" | jq .

CONFIG=$(curl -fsS "$APP/config")
API_URL=$(printf '%s' "$CONFIG" | jq -r '.API_URL')
if [ "$API_URL" = "/api" ]; then API_URL="${APP}/api"; fi
printf '%s\n' "$CONFIG" | jq .

curl -fsS -H "x-ms-client-principal-id: <user-principal-id>" "$API_URL/v4/init_team" \
  | jq '{team_id, team_name:.team.name, agent_count:(.team.agents|length), starting_task_count:(.team.starting_tasks|length), starting_task_names:[.team.starting_tasks[]?.name]}'
```

Expected:

- `team_id` is the generated team ID.
- `agent_count` is non-zero and no more than six.
- `starting_task_count` is non-zero.
- `starting_task_names` match the generated Quick task cards.

Browser:

- Open `https://<frontend-host>`.
- Confirm the selected team label shows the generated team name.
- Confirm Quick task cards are visible.
- Run one generated starting task and verify answers cite or use the intended industry datasets.
- Confirm browser console has no relevant API/config errors.

If the browser shows "No team selected" or "Select a team to see available tasks," test `/api/v4/init_team` and `/api/v4/team_configs` first; do not debug CSS until the selected team and `starting_tasks` are present.

## 12. Rollback and cleanup

Prepare rollback before activation:

- Team config: keep the previous selected team ID. For a new demo-only team, rollback is usually selecting the previous team; delete the generated team only with explicit confirmation.
- Blob data: use dedicated demo containers where possible. If replacing existing demo objects, snapshot or copy them first.
- Search: prefer restoring prior documents or switching back to the prior index. Recreate/delete indexes only after approval.
- Frontend settings: record previous `BACKEND_API_URL` and `PROXY_API_REQUESTS` values before changing them.
- Code/infra: redeploy the previous known-good image/tag or revert reviewed source/infra changes.

Confirmed demo-only cleanup examples. Re-run the pre-upload gate first so the DELETE targets the approved backend/proxy:

```bash
curl -fsS -X DELETE \
  -H "x-ms-client-principal-id: <user-principal-id>" \
  "${API_URL}/v4/team_configs/${TEAM_ID}"
```

Avoid `azd down` for rollback unless the entire environment is disposable and teardown has been explicitly approved.

## Renewable energy example mapping

Generated pack:

```bash
export INDUSTRY="renewable_energy"
export SCENARIO="operations"
export TEAM_ID="team-renewable-energy-operations"
export TEAM_JSON="data/agent_teams/renewable_energy_operations.json"
export DATASET_ROOT="data/datasets/renewable_energy"
```

| Search index | Suggested demo Blob container | Source files |
|---|---|---|
| `macae-renewable-energy-renewable-assets-index` | `<renewable-assets-container>` | `renewable_assets.csv` |
| `macae-renewable-energy-generation-operations-index` | `<renewable-generation-container>` | `generation_forecasts.csv`, `market_settlements.csv` |
| `macae-renewable-energy-work-orders-index` | `<renewable-work-orders-container>` | `work_orders.csv` |
| `macae-renewable-energy-grid-compliance-index` | `<renewable-grid-compliance-container>` | `grid_interconnections.csv`, `compliance_obligations.csv`, `environmental_events.csv` |

The renewable generation and grid-compliance indexes are intentionally composite: multiple CSVs map into one Search index where `docs/adaptations/renewable_energy/SCHEMA_MAPPING.md` says the consuming agent needs combined context.

Example indexing pattern for the composite generation index:

```bash
export BLOB_CONTAINER="<renewable-generation-container>"
export SEARCH_INDEX="macae-renewable-energy-generation-operations-index"

az storage container create --account-name "$STORAGE_ACCOUNT" --name "$BLOB_CONTAINER" --auth-mode login --public-access off
az storage blob upload-batch --account-name "$STORAGE_ACCOUNT" --destination "$BLOB_CONTAINER" --source "$DATASET_ROOT" --auth-mode login --pattern "generation_forecasts.csv" --overwrite false
az storage blob upload-batch --account-name "$STORAGE_ACCOUNT" --destination "$BLOB_CONTAINER" --source "$DATASET_ROOT" --auth-mode login --pattern "market_settlements.csv" --overwrite false
python3 infra/scripts/index_datasets.py "$STORAGE_ACCOUNT" "$BLOB_CONTAINER" "$SEARCH_SERVICE" "$SEARCH_INDEX"
```

Expected smoke result after upload and selection:

- `/config` points to the intended backend API route.
- `$API_URL/v4/init_team` returns `team-renewable-energy-operations`.
- Team name is `Renewable Energy Operations Team`.
- Quick task cards include `Portfolio Performance Review`, `Maintenance and Curtailment Risk`, and `Grid Compliance Escalation`.

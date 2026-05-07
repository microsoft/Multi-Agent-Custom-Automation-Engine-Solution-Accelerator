# Redeployment Guide - customize-use-case for MACE

This runbook is a planning companion after `customize-use-case` changes local files. It is not the authority for destructive data/search/cloud activation. Use the sibling [deploy-adaptation](../deploy-adaptation/SKILL.md) skill before uploading data, reindexing Search, rerunning postdeploy scripts, resetting demo stores, or redeploying Azure resources.

## Preflight

From the repo root:

```bash
python3 .github/skills/customize-use-case/validate.py
git status --short
```

If infrastructure changed, validate Bicep with local tooling:

```bash
az bicep build --file infra/main.bicep --stdout > /dev/null
az bicep build --file infra/main_custom.bicep --stdout > /dev/null
```

If UI changed:

```bash
cd src/App
npm ci
npm run build
```

## Impact Guide

| Changed paths | Likely impact | Handoff |
|---|---|---|
| `data/agent_teams/<usecase>.json` only | data-only/runtime config | Upload through UI/API or a deliberately extended upload script via `deploy-adaptation`. |
| `data/datasets/<usecase>/**` | data-only/Search | Validate files, then let `deploy-adaptation` plan Blob upload and Search indexing. |
| `src/mcp_server/**` | backend-only or mixed | Requires MCP registration, tests, image rebuild, and redeploy. |
| `src/App/**` | frontend-only unless paired with API/schema changes | Build frontend and run UI smoke checks. |
| `infra/**`, `azure*.yaml` | infrastructure-only or mixed | Require Bicep/azd evidence and `deploy-adaptation`. |

## Activation Notes

`infra/scripts/upload_team_config.py` currently enumerates the packaged default team files. A generated team should be activated by one of these explicit choices:

1. Upload the JSON through the MACE team selector UI.
2. Use the `/api/v4/upload_team_config` endpoint with the generated JSON.
3. Intentionally patch `infra/scripts/upload_team_config.py` to discover approved generated files, then validate and redeploy.

Do not rerun `infra/scripts/selecting_team_config_and_data.sh` just because a generated use-case file exists; the script is packaged-demo oriented and can upload or overwrite sample data.

# Redeployment Guide - adapt-for-industry for MACE

This runbook is a planning companion after `adapt-for-industry` generates industry files. It is not a normal path for destructive cloud operations. Use [deploy-adaptation](../deploy-adaptation/SKILL.md) for environment proof, validation, sample/demo ownership checks, snapshots, explicit reset confirmation, activation, smoke tests, and rollback.

## Preflight

```bash
python3 .github/skills/adapt-for-industry/validate.py
git status --short
```

If UI terminology changed:

```bash
cd src/App
npm ci
npm run build
```

If Bicep or azd files changed:

```bash
az bicep build --file infra/main.bicep --stdout > /dev/null
az bicep build --file infra/main_custom.bicep --stdout > /dev/null
```

## Industry Activation Shape

Runtime-ready industry changes should include:

- `data/agent_teams/<industry>_<scenario>.json`
- `data/datasets/<industry>/**`
- `docs/adaptations/<industry>/SCHEMA_MAPPING.md`
- `docs/adaptations/<industry>/DATA_SWAP_GUIDE.md`
- `docs/adaptations/<industry>/ACTIVATION_HANDOFF.md`

Optional `data/industry_packs/<industry>/` content is a planning bundle only unless it is promoted into runtime paths.

## Data/Search Safety

Before any Blob upload, Search index update, document deletion, index recreation, or sample-data script rerun:

1. Prove the target subscription/resource group/environment.
2. Identify exact Blob containers/prefixes and Search indexes.
3. Distinguish demo/sample data from real customer data.
4. Capture rollback or snapshot plan.
5. Validate generated files.
6. Ask for explicit confirmation immediately before destructive reset or overwrite.

Prefer scoped document replacement in existing Azure AI Search indexes. Do not recreate indexes unless schema change is intentional, validated, and confirmed.

Cosmos DB holds team, session, and plan state. Do not reset Cosmos as part of an industry data swap unless the target is a confirmed demo-only container or record scope.

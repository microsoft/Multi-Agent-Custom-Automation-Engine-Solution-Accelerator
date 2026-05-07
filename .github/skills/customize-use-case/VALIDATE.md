# Validate `customize-use-case` for MACE

Run from the SA repo root:

```bash
python3 .github/skills/customize-use-case/validate.py
```

Run selected checks:

```bash
python3 .github/skills/customize-use-case/validate.py --check team_json --check ui_contract
```

Available checks: `environment`, `team_json`, `generated_artifacts`, `ui_contract`, `compile`, `iac_build`, `tests`.

## What it checks

- Python version and repo-root discovery.
- JSON parsing and backend-required fields for `data/agent_teams/*.json`.
- Generated team configs do not collide with reserved frontend team IDs/names and do not exceed six agents.
- Generated RAG/MCP teams include `ProxyAgent` last.
- Generated adaptation folders include expected documentation when present.
- Frontend team contract surfaces still exist: `Team.tsx`, `TeamSelector.tsx`, `HomeInput.tsx`, upload endpoint usage, `starting_tasks` rendering, and reserved defaults.
- Python files generated in adapter-relevant areas compile.
- Bicep build commands run when Azure CLI/Bicep tooling is present; external-tool absence or AVM restore/network failure is reported as skipped.
- Test frameworks are detected but not forced by default in minimal environments.

## Output

`stdout` is human-readable. `stderr` emits one JSON object per check for tools. Exit code is `0` when all required checks pass or are skipped for unavailable tooling, and `1` when a required check fails.

## Common failures

| Check | Meaning | Fix |
|---|---|---|
| `team_json` | A generated team JSON cannot be uploaded or displayed safely. | Add missing required keys, reduce agents to six or fewer, make `team_id`/`name` unique, or add final `ProxyAgent`. |
| `generated_artifacts` | A generated docs/data folder is incomplete. | Add README, schema mapping, data handoff, or dataset files required by the generated adaptation. |
| `ui_contract` | Frontend/backend team payload surfaces drifted. | Restore stable JSON keys, update display copy separately, and keep `Team.tsx`, `TeamSelector.tsx`, and `HomeInput.tsx` aligned. |
| `compile` | A generated Python file has syntax errors. | Fix the reported file before redeploying. |
| `iac_build` | Bicep compile failed with local tooling. | Fix Bicep syntax or restore AVM dependencies before `azd provision` or `azd up`. |

## Self-test

```bash
python3 .github/skills/customize-use-case/validate.py --self-test
```

Self-test validates the checker logic against in-memory generated-team examples.

# Validate `adapt-for-industry` for MACE

Run from the SA repo root:

```bash
python3 .github/skills/adapt-for-industry/validate.py
```

Run selected checks:

```bash
python3 .github/skills/adapt-for-industry/validate.py --check team_json --check generated_artifacts --check ui_contract
```

Available checks: `environment`, `team_json`, `generated_artifacts`, `ui_contract`, `compile`, `iac_build`, `tests`.

## What it checks

- Generated industry team configs satisfy backend upload and frontend display contracts.
- Team IDs/names do not collide with packaged defaults in `TeamSelector.tsx`.
- Generated teams have six agents or fewer and include a final `ProxyAgent` for RAG/MCP/clarification teams.
- Industry docs under `docs/adaptations/<industry>/` include schema mapping, data swap, and activation handoff content when present.
- Optional `data/industry_packs/<industry>/` bundles contain explicit promotion guidance because MACE does not auto-load that folder.
- UI contract surfaces still exist and preserve stable team JSON/API keys.
- Python code in generated MCP service areas compiles.
- Bicep build commands run when local Azure tooling is available and skip cleanly when unavailable.

## Output and failures

`stdout` is human-readable. `stderr` emits JSONL. Exit code `1` means a required check failed.

Most failures are caused by missing team fields, duplicate team names, a generated industry bundle that never maps back to `data/agent_teams` and `data/datasets`, or UI copy edits that renamed stable JSON/API keys.

## Self-test

```bash
python3 .github/skills/adapt-for-industry/validate.py --self-test
```

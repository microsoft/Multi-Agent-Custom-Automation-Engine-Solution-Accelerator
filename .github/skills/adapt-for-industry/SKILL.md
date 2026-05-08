---
name: adapt-for-industry
description: Generate a MACE industry adaptation using runtime team JSON, industry datasets, schema mapping, compliance guidance, UI terminology checks, validation, and safe activation handoff.
---

# Adapt MACE for an Industry

Use this skill to adapt MACE for a target industry such as healthcare, financial services, manufacturing, legal, education, public sector, retail, or energy. In this Microsoft clone, MACE does not natively auto-load `data/industry_packs/`; the runtime paths are `data/agent_teams/*.json` and `data/datasets/**`. Therefore an industry adaptation must generate files that can be promoted into those runtime paths.

For detailed industry patterns, read [references/GENERATION_GUIDE.md](references/GENERATION_GUIDE.md).

## Step A - Read Existing Industry and Data Patterns

Read:

1. `data/agent_teams/retail.json` - RAG pattern and Search index naming.
2. `data/agent_teams/rfp_analysis_team.json` and `data/agent_teams/contract_compliance_team.json` - document-analysis industry-adjacent patterns.
3. `data/datasets/retail/customer`, `data/datasets/retail/order`, `data/datasets/rfp`, and `data/datasets/contract_compliance`.
4. `infra/scripts/index_datasets.py` - Search index shape.
5. `infra/scripts/selecting_team_config_and_data.sh` - current packaged data upload/index sequence.
6. `infra/scripts/upload_team_config.py` - current hardcoded packaged team enumeration.
7. `src/App/src/components/common/TeamSelector.tsx`, `src/App/src/components/content/HomeInput.tsx`, and `src/App/src/models/Team.tsx` - frontend team upload/display contract.
8. `.github/sa-analysis/architecture-survey.md` and `.github/sa-analysis/fy27-evaluation.md`.

## Step B - Ask for the Target Industry

Ask the user for:

1. Target industry and sub-domain.
2. Target scenario or demo narrative.
3. Compliance posture: HIPAA, HL7/FHIR, SOX, PCI-DSS, KYC/AML, GDPR, FERPA, ISO, NERC CIP, FedRAMP, eDiscovery, privilege, or other.
4. Core entities and source data shape.
5. RAG-only, MCP-enabled, reasoning, or hybrid capabilities.
6. Whether generated data is synthetic only or maps to customer-provided data later.
7. Which UI display labels/copy should use industry terminology.

Multilingual/i18n/localization is out of scope. This skill adapts industry terminology and display copy in the existing language only.

## Step C - Generate the Industry Adaptation

Generate a runtime-ready adaptation:

```text
data/agent_teams/<industry>_<scenario>.json
data/datasets/<industry>/<entity>.csv
docs/adaptations/<industry>/README.md
docs/adaptations/<industry>/SCHEMA_MAPPING.md
docs/adaptations/<industry>/DATA_SWAP_GUIDE.md
docs/adaptations/<industry>/ACTIVATION_HANDOFF.md
docs/adaptations/<industry>/mcp_recommendations.md
```

Optionally create a planning bundle at `data/industry_packs/<industry>/` only as a documented package mirror. If you create that bundle, also generate explicit instructions that its `team_config.json` and `datasets/` must be promoted into MACE runtime paths before activation.

### Required team config rules

The generated industry team config must satisfy the same backend/frontend contract as `customize-use-case`:

- Unique `team_id` and `name`; do not collide with defaults in `TeamSelector.tsx`.
- Six agents or fewer.
- Required backend fields for top-level, agents, and starting tasks.
- RAG index names following `macae-<industry>-<entity>-index`.
- `ProxyAgent` last when the generated team uses RAG, MCP, or clarification.
- Explicit compliance reminders in relevant agent `system_message` values.
- Synthetic sample data only unless the user explicitly provides safe customer-owned data.

### GA repeatability rules

For GA/demo-ready packs, make activation deterministic:

- Use a stable, explicit `team_id`; deployment handoff must upload with that same ID instead of relying on generated IDs.
- Include 3-4 `starting_tasks` with concise `name` values and complete prompts so the Home page can render Quick task cards immediately after team selection.
- Keep each RAG agent's `index_name` matched to exactly one generated dataset and document that mapping in `SCHEMA_MAPPING.md`.
- Do not depend on packaged postdeploy scripts to discover a custom industry pack. Handoff must list the exact team JSON path, dataset paths, Search index names, and upload/index commands for this pack only.
- Add an expected smoke-test contract to `ACTIVATION_HANDOFF.md`: `/api/v4/init_team` returns the generated `team_id`, six-or-fewer agents, and non-empty `starting_tasks`; the UI shows the selected team and Quick task cards.
- If deployment targets Azure resources with private networking or governance policies, defer all connectivity decisions to `deploy-adaptation`; do not recommend enabling public access in generated docs.

## Step D - Schema Mapping and Sample Data

`docs/adaptations/<industry>/SCHEMA_MAPPING.md` must include:

- Canonical MACE concept to industry entity mapping.
- Field contracts per generated dataset.
- Data types, required flags, constraints, and relationships.
- Sensitivity tags such as PHI, PII, PCI, financial, legal privilege, student record, or IP-sensitive.
- Search index mapping and which agent consumes each index.

Generate 10-20 synthetic rows per entity. Keep identifiers fake and clearly non-production. Include 2-3 edge cases per entity, such as missing optional fields, boundary statuses, or exceptional workflows.

## Step E - UI Industry Update Checklist

Only update UI files when the adaptation changes user-visible terminology. Check in this order:

1. Labels/copy: home title, prompt placeholders, team selector messages, empty/error states, prompt-card text.
2. Form fields and review steps: upload dialog, chat input, plan approval/cancellation, task panels.
3. Routes/components: `HomePage`, `PlanPage`, `TeamSelector`, `TeamSelected`, plan/chat components.
4. Assets/branding: logo components, icon map, CSS theme/style files.
5. Validation messages: team upload, RAI, model, and search errors.
6. Frontend constants and contracts: `Team.tsx`, `inputTask.tsx`, `apiService.tsx`, `TeamService.tsx`.

Keep backend/API/internal schema keys stable unless an intentional backend/frontend contract change is documented and validated. Rename display labels/copy separately from JSON keys and API payload fields.

## Step F - Validate and Handoff

Run:

```bash
python3 .github/skills/adapt-for-industry/validate.py
```

Then hand off to [deploy-adaptation](../deploy-adaptation/SKILL.md) for all cloud-mutating work:

- Team config upload.
- Blob upload.
- Search index creation or document replacement.
- Postdeploy script rerun.
- Sample/demo reset.
- Cosmos cleanup.
- Backend/MCP/frontend rebuild or redeploy.

The generated `DATA_SWAP_GUIDE.md` must remain planning and safe data-format guidance. It must not include destructive cloud commands as normal steps.

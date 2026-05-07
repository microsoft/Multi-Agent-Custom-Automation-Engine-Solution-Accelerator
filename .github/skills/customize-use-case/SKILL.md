---
name: customize-use-case
description: Generate a MACE use-case adaptation by creating a valid agent team JSON, optional datasets, optional MCP service guidance, UI wording checklist, validation, and activation handoff.
---

# Customize Use Case for MACE

Use this skill to add a new business scenario to the Multi-Agent Custom Automation Engine Solution Accelerator. MACE loads use cases from JSON team configurations, so the primary output is a validated `data/agent_teams/<usecase>.json` file. Optional outputs are datasets under `data/datasets/<usecase>/`, MCP service code guidance, and UI copy updates when the scenario changes user-visible behavior.

For detailed generation rules and examples, read [references/GENERATION_GUIDE.md](references/GENERATION_GUIDE.md).

## Step A - Read Existing MACE Patterns

Before writing anything, read these files in the SA repo:

1. `data/agent_teams/hr.json` - MCP-only team pattern.
2. `data/agent_teams/marketing.json` - another MCP workflow pattern.
3. `data/agent_teams/retail.json` - RAG team pattern with Azure AI Search index names.
4. `data/agent_teams/rfp_analysis_team.json` and `data/agent_teams/contract_compliance_team.json` - document-analysis RAG patterns.
5. `src/backend/v4/common/services/team_service.py` and `src/backend/common/models/messages_af.py` - backend upload contract.
6. `src/App/src/models/Team.tsx`, `src/App/src/components/common/TeamSelector.tsx`, and `src/App/src/components/content/HomeInput.tsx` - frontend upload/display contract.
7. `src/mcp_server/core/factory.py` and `src/mcp_server/services/hr_service.py` - MCP registration and service pattern when tools are needed.
8. `.github/sa-analysis/architecture-survey.md` - publish, UI, and validation evidence.

Record the reserved team IDs and names from `TeamSelector.tsx`. Do not reuse them.

## Step B - Ask for the Target Use Case

Ask the user for:

1. Business problem and target users.
2. Desired team name and short identifier.
3. Whether agents need RAG, MCP tools, reasoning, or a hybrid.
4. Data sources and expected dataset formats.
5. Required agent roles and any human-in-the-loop clarifications.
6. Whether UI labels, prompt-card wording, disclaimers, or branding should change.
7. Whether cloud activation, Search indexing, or sample-data reset is in scope now or later.

Multilingual/i18n/localization is out of scope. This skill updates generic UI labels and copy only when the adapted use case needs different display wording.

## Step C - Generate the Use-Case Artifacts

Create these files as needed:

```text
data/agent_teams/<usecase>.json
data/datasets/<usecase>/README.md
data/datasets/<usecase>/<entity>.csv or .json
docs/adaptations/<usecase>/README.md
docs/adaptations/<usecase>/DATA_ACTIVATION_HANDOFF.md
```

If MCP tools are required, propose `src/mcp_server/services/<domain>_service.py` and explicit registration changes, but do not add MCP code unless the user confirms the tool/action surface. A new MCP service requires backend/MCP tests, container rebuild, and `deploy-adaptation`.

### Team JSON requirements

Generated `data/agent_teams/<usecase>.json` must:

- Use a unique `team_id` and `name` that do not collide with defaults in `TeamSelector.tsx`.
- Keep `agents` at six or fewer entries.
- Include top-level `name`, `status`, `deployment_name`, `agents`, `description`, `logo`, `plan`, and `starting_tasks`.
- Include required agent keys: `input_key`, `type`, `name`, `icon`, `deployment_name`, `system_message`, `description`, `use_rag`, `use_mcp`, `use_bing`, `use_reasoning`, `index_name`, and `coding_tools`.
- Include required starting task keys: `id`, `name`, `prompt`, `created`, `creator`, and `logo`.
- Use `gpt-4.1-mini` for normal agents and `o4-mini` only for reasoning agents.
- Use `macae-<usecase>-<entity>-index` for RAG index names.
- End with `ProxyAgent` when the generated team uses RAG, MCP, or needs clarification.

## Step D - UI Update Checklist

Only update UI files when the new use case needs user-visible wording, branding, or contract changes. Check surfaces in this order:

1. Labels/copy: `HomeInput.tsx`, `TeamSelector.tsx`, error cards, prompt-card titles, empty states.
2. Form fields and review steps: `ChatInput`, team upload dialog, plan approval/cancellation dialogs, task list and plan panels.
3. Routes/components: `App.tsx`, `HomePage`, `PlanPage`, `TeamSelected`, `TeamSelector`.
4. Assets/branding: `ContosoLogo.tsx`, `MsftColor.tsx`, `homeInput.tsx` icon map, CSS modules/styles.
5. Validation messages: upload errors, RAI/search/model validation errors, duplicate team messages.
6. Frontend constants, parsers, and API payload contracts: `Team.tsx`, `inputTask.tsx`, `apiService.tsx`, `TeamService.tsx`.

Keep backend/API/internal schema keys stable unless the backend/frontend contract change is intentional, documented, and covered by validation. Change display labels and copy separately from JSON keys such as `team_id`, `agents`, and `starting_tasks`.

## Step E - Validate

From the SA repo root, run:

```bash
python3 .github/skills/customize-use-case/validate.py
```

For details, see [VALIDATE.md](VALIDATE.md). Validation checks team JSON shape, reserved ID/name collisions, UI contract evidence, generated pack structure, Python compile safety, and Bicep build capability when local Azure tooling is available.

## Step F - Activation Handoff

This skill does not run cloud-mutating commands. After validation passes, hand off to [deploy-adaptation](../deploy-adaptation/SKILL.md) for any of these actions:

- Uploading generated team configs to the backend.
- Uploading files to Blob Storage.
- Creating/updating Azure AI Search indexes.
- Rerunning `infra/scripts/selecting_team_config_and_data.sh`.
- Rebuilding containers or redeploying Azure resources.
- Resetting sample/demo data.
- Touching Cosmos DB, Search documents, Blob paths, or production app settings.

For non-cloud local review, use [REDEPLOYMENT.md](REDEPLOYMENT.md) as a read-only planning runbook and route every mutating activation through `deploy-adaptation`.

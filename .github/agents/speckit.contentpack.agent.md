---
description: Create a new content pack (agent team + data + knowledge base) using the reference template and step-by-step guide.
---

# Content Packs

Optional, drop-in extensions to the Multi-Agent Custom Automation Engine. A pack
ships everything needed to add a domain-specific agent team **without touching
core code**.

The core solution works fine when the `content_packs/` folder is empty or absent.

---

## Folder Structure

```
content_packs/
└── <pack_name>/
    ├── pack.json               # optional — declares search indexes + blob uploads
    ├── agent_teams/
    │   └── *.json              # required — one or more team config files (any name)
    ├── datasets/               # optional — source data for grounding
    │   ├── data/*.csv
    │   └── docs/*.pdf
    └── scripts/                # optional — pack-local utilities
```

- `<pack_name>` should be lowercase snake_case (e.g. `pet_food`, `legal_review`).
- JSON files inside `agent_teams/` can be named anything — the upload script
  globs all `*.json` files in that directory.

---

## Designing Your Agent Team

Every pack needs at least one team config JSON in `agent_teams/`. The agents you
create should be tailored to your domain — there is no fixed pattern. Consider:

**What does the user need?** Design agents around the tasks your users will
perform, not around a template. Ask yourself:

| Question | Design decision |
|----------|----------------|
| Does the team need to look up data? | Add a **ResearchAgent** with `use_knowledge_base: true` |
| Does it need to generate images? | Add an agent with `use_toolbox: true` and the appropriate `toolbox_filter` |
| Should it ask the user clarifying questions? | Set `user_responses: true` on the relevant agent |
| Are there multiple distinct tasks? | Add specialist agents and a **TriageAgent** to route between them |
| Is it a simple Q&A over data? | A single agent with KB access may be enough — no triage needed |

**Examples from this repo:**

| Pack | Agents | Why |
|------|--------|-----|
| `content_gen` | Triage → Planning → Research → TextContent → ImageContent → Compliance | Complex creative workflow with multiple output types |
| `contract_compliance` | Triage → Research → Analysis | Document review with KB lookup |
| `hr_onboarding` | Single team (no KB) | Workflow-only, no data grounding needed |

**Key rules:**
- Every agent needs a unique `input_key` (used for routing between agents).
- The `team_id` must be a valid UUID using only hex characters (0-9, a-f).
  Use the pattern `00000000-0000-0000-0000-00000000NNNN` where NNNN is unique.
- At least one `starting_tasks` entry is required (the example prompt shown in the UI).

### Required Fields (validation will reject uploads without these)

**Team-level:**
```jsonc
{
  "id": "1",
  "team_id": "00000000-0000-0000-0000-000000000008",
  "name": "Your Team Name",
  "status": "visible",           // REQUIRED — team won't appear in UI without this
  "deployment_name": "gpt-5.4-mini",
  ...
}
```

**Each agent must include `type`:**
```jsonc
{
  "input_key": "my_agent",
  "type": "",                    // REQUIRED — empty string is fine, but field must exist
  "name": "MyAgent",
  ...
}
```

**Each starting task must include `created`, `creator`, `logo`:**
```jsonc
"starting_tasks": [
  {
    "id": "task-1",
    "name": "Example Task",
    "prompt": "A sample prompt users can click to start",
    "created": "",              // REQUIRED — empty string is fine
    "creator": "",              // REQUIRED — empty string is fine
    "logo": ""                  // REQUIRED — empty string is fine
  }
]
```

> Missing any of these fields results in a 400 error during upload.
> Use an existing pack (e.g. `hr_onboarding/agent_teams/hr.json`) as a
> reference for the full required schema.

---

## Data & Knowledge Bases

If your agents need to search domain-specific data, you need three things wired together:

```
CSV/PDF ──► AI Search Index ──► Knowledge Base (MCP) ──► Agent
            (pack.json)         (seed_knowledge_bases.py)  (agent_teams/*.json)
```

### Step 1 — Add your data

Put source files in `datasets/data/`. Supported formats:

| Format | How it's indexed |
|--------|-----------------|
| CSV | One document per row. Columns become searchable fields. |
| PDF/DOCX | Uploaded to blob; use `blob_indexes` in `pack.json` for document-crack indexing. |

### Step 2 — Create `pack.json`

```jsonc
{
  "name": "your_pack",
  "description": "What this pack does",
  "search_indexes": [
    {
      "index_name": "your-pack-data-index",
      "csv_path": "datasets/data/your_data.csv",
      "key_field": "id",
      "title_field": "product_name"
    }
  ],
  "blob_uploads": [
    {
      "container": "your-pack-dataset",
      "source": "datasets/data",
      "pattern": "*.csv"
    }
  ]
}
```

The `index_name` must be globally unique on your search service and will be
referenced in the KB registration.

### Step 3 — Register the Knowledge Base

Add an entry to `infra/scripts/post-provision/seed_knowledge_bases.py` in the `KNOWLEDGE_BASES`
dict. Place it before the `# ── Example Pack ──` comment block:

```python
    # ── Your Pack ──
    "your-pack-data-kb": {
        "description": "What this KB provides",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-5.4-mini",
                "modelName": "gpt-5.4-mini",
            },
        },
        "sources": [
            {
                "name": "your-pack-data-ks",
                "description": "What the source data contains",
                "index_name": "your-pack-data-index",  # Must match pack.json
                "searchable_fields": ["content", "title"],
            },
        ],
    },
```

**Naming convention (must be consistent across files):**

| Item | Pattern | Example |
|------|---------|---------|
| KB name (dict key) | `<pack>-<purpose>-kb` | `pet-food-catalog-kb` |
| Knowledge Source name | `<pack>-<purpose>-ks` | `pet-food-catalog-ks` |
| Search index name | `<pack>-<purpose>-index` | `pet-food-catalog-index` |

### Step 4 — Connect agents to the KB

In your team config JSON, set these fields on the agent that needs search:

```jsonc
"use_knowledge_base": true,
"knowledge_base_name": "your-pack-data-kb"  // Must match the key in seed_knowledge_bases.py
```

The agent's `system_message` should instruct it to **always use the search tool**
and **never hallucinate data**.

---

## Registering in the Deployment Script

Edit `infra/scripts/post-provision/Selecting-Team-Config-And-Data.ps1`. Search for `NEW CONTENT PACK`
— each insertion point has a comment template. There are **4 things** to do:

| # | What | Where |
|---|------|-------|
| 1 | Add `Write-Host "N. Your Pack Name"` | Menu display section |
| 2 | Add `elseif ($useCaseSelection -eq "N") { ... }` | Selection handler |
| 3 | Add deployment block (team config upload + `Deploy-ContentPack`) | After Content Gen block |
| 4 | Add `-or $useCaseSelection -eq "N"` to network/KB/success conditions | Only if pack has data |

After adding your entry, update `$allOption` to `N + 1` so "All" is always last.

---

## Agent Tool Options Reference

| Field | Type | Purpose |
|-------|------|---------|
| `use_knowledge_base` | bool | Connects a Foundry IQ KB as an MCP search tool |
| `knowledge_base_name` | string | Name of the KB (must exist in `seed_knowledge_bases.py`) |
| `use_file_search` | bool | Attaches an Azure AI vector store for file-level RAG |
| `vector_store_name` | string | Name of the vector store in Foundry |
| `use_toolbox` | bool | Connects MCP toolbox tools (e.g., `generate_marketing_image`) |
| `toolbox_filter` | string | Tag filter for which toolbox tools are available |
| `coding_tools` | bool | Enables code interpreter sandbox |
| `user_responses` | bool | Allows the agent to pause and ask the user a question |

> **`user_responses` guidance:** Default to `false` unless the user explicitly
> asks for the agent to collect human feedback or ask clarifying questions.
> When `false`, the agent runs autonomously without pausing for input. Only set
> to `true` on agents whose design requires them to ask the user a question
> mid-workflow (e.g., an intake agent gathering requirements).

---

## Deploying

```bash
# 1. Deploy infrastructure
azd up

# 2. Provision pack resources — select your pack or "All"
./infra/scripts/post-provision/Selecting-Team-Config-And-Data.ps1 -ResourceGroup <rg>
```

---

## Checklist

- [ ] `content_packs/<pack>/agent_teams/` has at least one valid JSON team config
- [ ] `team_id` is a valid hex UUID (0-9, a-f only)
- [ ] `starting_tasks` has at least one example prompt
- [ ] If using a KB: `pack.json` exists with matching `index_name`
- [ ] If using a KB: `datasets/data/` contains the source files
- [ ] If using a KB: entry added to `seed_knowledge_bases.py` with matching names
- [ ] If using a KB: agent has `use_knowledge_base: true` + correct `knowledge_base_name`
- [ ] Agent `system_message` tells it to search (not hallucinate)
- [ ] Pack registered in `Selecting-Team-Config-And-Data.ps1` (all 4 locations)
- [ ] `$allOption` updated if you added a new menu number

---

## Removing a Pack

Delete the pack folder. Previously uploaded team configs remain in Cosmos until
deleted via `DELETE /api/v4/team_configs/{team_id}`. Search indexes and blob
containers are also left in place — clean up with `az search` / `az storage`.


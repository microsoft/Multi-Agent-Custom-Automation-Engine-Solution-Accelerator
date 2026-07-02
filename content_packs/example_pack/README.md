# `example_pack` — Reference Content Pack

A minimal, copy-paste starter that demonstrates every feature needed to add a
new domain-specific agent team. Use this as a template when creating a new pack.

---

## Quick Summary

| Layer | What it does | File |
|-------|-------------|------|
| Data | CSV/PDF source files for grounding | `datasets/data/books.csv` |
| Search Index | Azure AI Search index built from data | Declared in `pack.json` |
| Knowledge Base | Foundry IQ KB wrapping the index (MCP endpoint) | Declared in `seed_knowledge_bases.py` |
| Agent Team | Team config with agents that query the KB | `agent_teams/example_pack.json` |

---

## Directory Structure

```
example_pack/
├── pack.json                        # Pack manifest — declares search indexes & blob uploads
├── README.md                        # This file
├── agent_teams/
│   └── example_pack.json            # Team config — agents, tools, KB connections
└── datasets/
    └── data/
        └── books.csv                # Source data — indexed into Azure AI Search
```

---

## How It Works End-to-End

```
books.csv ──► AI Search Index ──► Knowledge Base (MCP) ──► Agent (use_knowledge_base=true)
              (pack.json)         (seed_knowledge_bases.py)  (agent_teams/*.json)
```

1. **`pack.json`** tells the provisioning script to create an AI Search index
   from the CSV and upload the raw file to blob storage.
2. **`seed_knowledge_bases.py`** creates a Foundry IQ Knowledge Base that wraps
   the search index and exposes it as an MCP tool endpoint.
3. **`agent_teams/example_pack.json`** defines agents. Any agent with
   `"use_knowledge_base": true` and a `"knowledge_base_name"` gets the KB
   connected as a server-side MCP tool at runtime.

---

## Step-by-Step: Adding a New Content Pack

### Step 1 — Create the folder structure

```bash
cp -r content_packs/example_pack content_packs/<your_pack>
```

Rename files to match your pack name (e.g., `agent_teams/<your_team_name>.json`).

### Step 2 — Add your data

Replace `datasets/data/<your_data>` with your source data. Supported formats:

| Format | How it's indexed |
|--------|-----------------|
| CSV | One document per row. Columns become fields. Declare in `pack.json` → `search_indexes`. |
| PDF/DOCX | Uploaded to blob; use `blob_indexes` in `pack.json` for document-crack indexing. |

### Step 3 — Update `pack.json`

```jsonc
{
  "name": "your_pack",
  "description": "What this pack does",

  // Option A: CSV-based index (structured data)
  "search_indexes": [
    {
      "index_name": "your-pack-data-index",   // Must be globally unique on your search service
      "csv_path": "datasets/data/your_data.csv",
      "key_field": "id",                      // Column to use as document key
      "title_field": "name"                   // Column for the searchable title
    }
  ],

  // Option B: Blob/document-based index (PDFs, Word docs)
  "blob_indexes": [
    {
      "index_name": "your-pack-docs-index",
      "container": "your-pack-docs",
      "source": "datasets/docs",
      "pattern": "*"
    }
  ],

  // Raw file upload to blob (for traceability/backup)
  "blob_uploads": [
    {
      "container": "your-pack-dataset",
      "source": "datasets/data",
      "pattern": "*.csv"
    }
  ]
}
```

### Step 4 — Register the Knowledge Base

Add an entry to `infra/scripts/post-provision/seed_knowledge_bases.py` in the `KNOWLEDGE_BASES` dict:

```python
    # ── Your Pack ──
    "your-pack-data-kb": {
        "description": "Description of what this KB provides",
        "model": {
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": AI_SERVICES_ENDPOINT,
                "deploymentId": "gpt-4.1-mini",
                "modelName": "gpt-4.1-mini",
            },
        },
        "sources": [
            {
                "name": "your-pack-data-ks",          # Knowledge Source name
                "description": "What the source contains",
                "index_name": "your-pack-data-index", # Must match pack.json index_name
                "searchable_fields": ["content", "title"],
            },
        ],
    },
```

**Naming convention:**
- KB name: `<pack-name>-<purpose>-kb` (e.g., `example-pack-books-kb`)
- Knowledge Source name: `<pack-name>-<purpose>-ks`
- Index name: `<pack-name>-<purpose>-index`

### Step 5 — Configure agents in team config

Create `agent_teams/your_pack.json`. Key fields:

```jsonc
{
  "id": "1",
  "team_id": "00000000-0000-0000-0000-00000000xxxx",  // Stable UUID for idempotent uploads
  "name": "Your Team Name",
  "deployment_name": "gpt-4.1-mini",                   // Default model for the team
  "agents": [
    {
      "input_key": "research_agent",                   // Used for inter-agent handoff routing
      "name": "ResearchAgent",
      "deployment_name": "gpt-4.1-mini",
      "system_message": "Your agent instructions...",
      "description": "What this agent does",

      // ─── Knowledge Base (MCP tool) connection ───
      "use_knowledge_base": true,                      // REQUIRED to connect KB
      "knowledge_base_name": "your-pack-data-kb",     // Must match seed_knowledge_bases.py key

      // ─── Other tool options ───
      "use_file_search": false,                        // Azure AI file search (vector store)
      "vector_store_name": "",
      "use_toolbox": false,                            // MCP toolbox (e.g., image generation)
      "toolbox_filter": "",                            // Filter tag for toolbox tools

      // ─── Agent behavior ───
      "user_responses": false,                         // Can ask user for input mid-task
      "coding_tools": false,                           // Code interpreter sandbox
      "temperature": null,                             // null = model default
      "icon": ""
    }
  ],
  "starting_tasks": [
    {
      "id": "task-1",
      "name": "Example Task",
      "prompt": "A sample prompt users can click to start"
    }
  ]
}
```

### Step 6 — Register your pack in the deployment script

Edit `infra/scripts/post-provision/Selecting-Team-Config-And-Data.ps1`. There are **4 locations**
to update (each is marked with a `NEW CONTENT PACK` comment block in the script):

| # | Section | What to add |
|---|---------|-------------|
| 1 | **Menu display** (~line 430) | `Write-Host "8. Your Pack Name"` |
| 2 | **Selection handler** (~line 480) | `elseif ($useCaseSelection -eq "8") { ... }` |
| 3 | **Deployment block** (~line 800) | Upload team config + `Deploy-ContentPack` call |
| 4 | **KB seeding condition** (~line 820) | Add `-or $useCaseSelection -eq "8"` |
| 5 | **Network access condition** (~line 605) | Add `-or $useCaseSelection -eq "8"` (only if pack has data) |

Search for `NEW CONTENT PACK` in the script — each location has a commented-out
template you can copy and customize.

### Step 7 — Deploy and seed

```bash
# 1. Deploy infrastructure (creates search service, blob, etc.)
azd up

# 2. Provision pack resources (indexes, blob uploads, team configs, KBs)
#    Run the post-deploy script and select your pack or "All"
./infra/scripts/post-provision/Selecting-Team-Config-And-Data.ps1 -ResourceGroup <rg>
```

The script handles everything: team config upload, data indexing, and KB seeding.
For manual runs of individual steps:

```bash
# Upload team config only
python infra/scripts/post-provision/upload_team_config.py \
  "https://<backend-url>" \
  "content_packs/your_pack/agent_teams" \
  "<user-principal-id>" \
  "<team-uuid>"

# Seed KBs only (after indexes exist)
python infra/scripts/post-provision/seed_knowledge_bases.py
```

---

## Agent Tool Options Reference

| Field | Type | Purpose |
|-------|------|---------|
| `use_knowledge_base` | bool | Connects a Foundry IQ KB as an MCP search tool |
| `knowledge_base_name` | string | Name of the KB (must exist in `seed_knowledge_bases.py`) |
| `use_file_search` | bool | Attaches an Azure AI vector store for file-level RAG |
| `vector_store_name` | string | Name of the vector store in Foundry |
| `use_toolbox` | bool | Connects MCP toolbox tools (e.g., `generate_marketing_image`) |
| `toolbox_filter` | string | Tag filter to select which toolbox tools are available |
| `coding_tools` | bool | Enables the code interpreter sandbox |
| `user_responses` | bool | Allows the agent to pause and ask the user a question |

---

## Checklist for New Packs

Use this checklist to verify completeness:

- [ ] `content_packs/<pack>/pack.json` exists with correct `index_name`
- [ ] `content_packs/<pack>/datasets/` contains source data files
- [ ] `content_packs/<pack>/agent_teams/<pack>.json` exists with valid agents
- [ ] At least one agent has `"use_knowledge_base": true` with a valid `knowledge_base_name`
- [ ] KB entry added to `infra/scripts/post-provision/seed_knowledge_bases.py` (index_name matches pack.json)
- [ ] `team_id` is a stable UUID (prevents duplicate teams on re-upload)
- [ ] `starting_tasks` has at least one example prompt
- [ ] Agent `system_message` instructs the agent to use its search tool (not hallucinate)
- [ ] Ran `seed_knowledge_bases.py` after index creation
- [ ] Team config uploaded via post-deploy script or manual `upload_team_config.py`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent hallucinates instead of searching | `use_knowledge_base` is `false` or KB not seeded | Set `true` + run `seed_knowledge_bases.py` |
| "Index not found" during KB creation | Index hasn't been provisioned yet | Run pack provisioning before seeding KBs |
| Team not visible in UI | Team config not uploaded | Run `upload_team_config.py` or post-deploy script |
| KB MCP tool returns empty results | Index exists but has no documents | Re-run `provision_content_pack.py` to index data |
| Agent can't reach KB | Managed identity missing Search role | Assign "Search Index Data Reader" to the app identity |


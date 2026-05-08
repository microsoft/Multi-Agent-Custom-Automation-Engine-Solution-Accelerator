# Content Packs

Optional, drop-in extensions to the Multi-Agent Custom Automation Engine. A pack
ships everything needed to add a domain-specific agent team **without touching
core code**.

The core solution works fine when this folder is empty or absent.

> 💡 **Looking for a starting point?** See [example_pack/](example_pack/README.md)
> — a minimal, fully-working pack that demonstrates the team config, AI Search
> index, and blob upload features. Copy that folder and edit it.

## Convention

```
content_packs/
└── <pack_name>/
    ├── pack.json               # optional — declares pack-level Azure resources
    ├── agent_teams/
    │   └── <pack_name>.json    # required — uploaded automatically on deploy
    ├── datasets/               # optional — sample data your tools/scripts use
    │   ├── data/*.csv
    │   └── images/*.png
    ├── scripts/                # optional — pack-local one-off utilities
    └── mcp_tools/              # optional — pack-specific MCP services (manual wiring today)
```

`<pack_name>` should be lowercase snake_case (e.g. `content_gen`, `legal_review`).

## How packs are picked up

During deployment, [Selecting-Team-Config-And-Data.ps1](../infra/scripts/Selecting-Team-Config-And-Data.ps1)
discovers packs and provisions everything they declare:

1. **Team configs** — [upload_team_config.py](../infra/scripts/upload_team_config.py)
   globs `content_packs/*/agent_teams/*.json`, picks a deterministic UUID
   (`team_id` in the JSON if it's a UUID, otherwise `uuid5("…aaaa", "<pack>")`),
   and POSTs each to `/api/v4/upload_team_config`.
2. **Pack-level resources** — [provision_content_pack.py](../infra/scripts/provision_content_pack.py)
   reads each `pack.json` and provisions Azure resources it declares
   (currently: AI Search indexes built from CSVs, and raw-file blob uploads).

This means uploading a new pack is just: drop the folder in, redeploy.

## Manifest schema (`pack.json`)

```jsonc
{
  "name": "<pack>",
  "description": "...",
  "search_indexes": [          // optional
    {
      "index_name":  "<index>",
      "csv_path":    "datasets/data/<file>.csv",
      "key_field":   "id",          // optional, default "id"
      "title_field": "<column>"     // optional, default first non-key column
    }
  ],
  "blob_uploads": [            // optional
    {
      "container": "<container>",
      "source":    "datasets/data",  // file or directory inside the pack
      "pattern":   "*.csv"           // optional, default "*"
    }
  ]
}
```

Both lists are optional. A pack with no `pack.json` will still have its team
configs uploaded — the manifest only adds Azure-side provisioning.

## Removing a pack

Delete the pack folder. The team configs it previously uploaded remain in
Cosmos until you delete them via `DELETE /api/v4/team_configs/{team_id}` (the
deterministic UUID is `uuid5("00000000-0000-0000-0000-00000000aaaa", "<pack_name>")`).
Search indexes and blob containers created from the manifest are also left in
place — clean them up with `az search` / `az storage` if no longer needed.

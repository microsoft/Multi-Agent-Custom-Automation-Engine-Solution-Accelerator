# `example_pack` — reference content pack

A minimal, copy-paste starter that demonstrates every feature the deployment
scripts know how to provision automatically. Use this as a template when
adding a new pack.

## What's in the box

```
example_pack/
├── pack.json                          # manifest — declares search indexes & blob uploads
├── agent_teams/
│   └── example_pack.json              # team config — uploaded to the backend
└── datasets/
    └── data/
        └── books.csv                  # sample data — indexed and uploaded to blob
```

## What gets provisioned

When a user runs the post-deploy script and selects this pack (option 7/`all`,
or option 6 if you wire it as the default pack), the script will:

1. **Upload the team config** at [agent_teams/example_pack.json](agent_teams/example_pack.json)
   to `POST /api/v4/upload_team_config` (team_id `00000000-0000-0000-0000-0000000000ee`).
2. **Create the AI Search index** `example-pack-books-index` and merge-upload one
   document per row from [datasets/data/books.csv](datasets/data/books.csv).
3. **Upload the raw CSV** to blob container `example-pack-dataset` for traceability.

All steps are idempotent — re-running upserts.

## Manifest schema (`pack.json`)

```jsonc
{
  "name": "example_pack",                // logical pack name (folder name is fine)
  "description": "...",                  // shown in logs only
  "search_indexes": [                    // optional
    {
      "index_name": "example-pack-books-index",
      "csv_path":   "datasets/data/books.csv",
      "key_field":  "id",                // optional, default "id"
      "title_field": "title"             // optional, default first non-key column
    }
  ],
  "blob_uploads": [                      // optional
    {
      "container": "example-pack-dataset",
      "source":    "datasets/data",      // file or directory inside the pack
      "pattern":   "*.csv"               // optional, default "*"; only used when source is a dir
    }
  ]
}
```

## Adding your own pack

1. Copy this folder: `cp -r content_packs/example_pack content_packs/<your_pack>`.
2. Replace `agent_teams/example_pack.json` with your team config. Set a stable
   `team_id` UUID if you want the same pack to be re-uploadable across deploys.
3. Replace `datasets/data/books.csv` with your data and update `pack.json`
   so the `index_name`, `csv_path`, `key_field`, and `title_field` match.
4. Run the post-deploy script and select option **7 (All)** — every pack with a
   `pack.json` is provisioned automatically. No script changes needed.

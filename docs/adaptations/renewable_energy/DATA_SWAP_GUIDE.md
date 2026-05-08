# Renewable Energy Data Swap Guide

This guide is planning guidance only. It describes how to prepare customer-owned renewable energy data for the generated schema. It does not authorize or perform Blob uploads, Search indexing, Search document deletion, index recreation, Cosmos changes, postdeploy hook reruns, sample resets, container rebuilds, or Azure redeployments. Route those actions through the `deploy-adaptation` skill with explicit environment proof and confirmation.

## Source systems to map

| Source system category | Target dataset |
|---|---|
| Asset management or portfolio registry | `renewable_assets.csv` |
| SCADA/telemetry summaries or forecast platform exports | `generation_forecasts.csv` |
| EAM/CMMS work order system | `work_orders.csv` |
| Interconnection queue or transmission operator records | `grid_interconnections.csv` |
| Compliance register or GRC system | `compliance_obligations.csv` |
| Market settlement or revenue system | `market_settlements.csv` |
| Environmental, health, safety, or permitting tracker | `environmental_events.csv` |

## Preparation steps

1. Confirm the data owner, approved demo scope, and whether the data is synthetic, masked, or customer-owned.
2. Map source columns to the field contracts in `SCHEMA_MAPPING.md`.
3. Remove secrets, real access-control details, precise physical-security procedures, and unnecessary personal data.
4. Replace direct personal identifiers with role-based or synthetic contacts unless the customer has explicitly approved their use.
5. Normalize dates to ISO `YYYY-MM-DD`, booleans to `true` or `false`, and IDs to stable non-production values.
6. Preserve relationships: `asset_id` joins asset, forecast, work order, and settlement records; `site_id` joins asset, interconnection, compliance, and environmental records.
7. Label financial and critical-infrastructure fields for review before activation.
8. Validate generated artifacts locally with `python3 .github/skills/adapt-for-industry/validate.py`.
9. Prepare an activation request for `deploy-adaptation` that lists target environment, files, intended Search indexes, container grouping, snapshot needs, and rollback expectations.

## Search grouping plan

| Search index | Files to stage together |
|---|---|
| `macae-renewable-energy-renewable-assets-index` | `renewable_assets.csv` |
| `macae-renewable-energy-generation-operations-index` | `generation_forecasts.csv`, `market_settlements.csv` |
| `macae-renewable-energy-work-orders-index` | `work_orders.csv` |
| `macae-renewable-energy-grid-compliance-index` | `grid_interconnections.csv`, `compliance_obligations.csv`, `environmental_events.csv` |

## Acceptance checklist before activation

| Check | Required outcome |
|---|---|
| Ownership | Data owner approves use in the target demo or environment. |
| Scope | Demo/sample data is separated from production data. |
| Privacy | PII/GDPR fields are minimized or masked. |
| Critical infrastructure | Grid, substation, communications, and access details are abstracted to safe labels. |
| Financial controls | Settlement values are synthetic, masked, or approved for use. |
| Compliance | NERC CIP, FERC, ISO 55001, OSHA, environmental, and privacy obligations are reflected in field mapping. |
| Rollback | Previous team config, Blob data, Search index state, and Cosmos team/session impact are understood before any overwrite. |

## Handoff boundary

After data owners approve the mapped files, stop and invoke `deploy-adaptation` for any cloud-mutating activation. Do not directly overwrite Blob containers, recreate Azure AI Search indexes, delete Search documents, reset Cosmos DB, rerun postdeploy hooks, or redeploy services from this guide.

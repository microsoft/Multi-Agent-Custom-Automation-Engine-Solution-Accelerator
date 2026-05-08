# Renewable Energy Activation Handoff

Use the `deploy-adaptation` skill for activation. This file records what was generated and what must be confirmed before any cloud-mutating work.

For the generic hands-on flow, use [Industry Pack Generation and Redeploy Runbook](../INDUSTRY_PACK_REDEPLOY_RUNBOOK.md).

## Generated files

| File | Activation role |
|---|---|
| `data/agent_teams/renewable_energy_operations.json` | Upload as the Renewable Energy Operations Team config. |
| `data/datasets/renewable_energy/renewable_assets.csv` | Stage/index for `RenewableAssetAgent`. |
| `data/datasets/renewable_energy/generation_forecasts.csv` | Stage/index for `GenerationForecastAgent`. |
| `data/datasets/renewable_energy/work_orders.csv` | Stage/index for `MaintenanceRiskAgent`. |
| `data/datasets/renewable_energy/grid_interconnections.csv` | Stage/index for `GridComplianceAgent`. |
| `data/datasets/renewable_energy/compliance_obligations.csv` | Stage/index for `GridComplianceAgent`. |
| `data/datasets/renewable_energy/market_settlements.csv` | Stage/index for `GenerationForecastAgent`. |
| `data/datasets/renewable_energy/environmental_events.csv` | Stage/index for `GridComplianceAgent`. |
| `docs/adaptations/renewable_energy/*.md` | Planning, schema, swap, and MCP handoff documentation. |

## Activation scope

| Area | Expected action |
|---|---|
| Team config | Upload generated JSON through the UI/API or an explicitly approved deployment workflow. |
| Blob data | Stage approved CSV files into Search index source containers/prefixes. |
| Azure AI Search | Create or update the four renewable energy indexes listed below. |
| Cosmos DB | Avoid reset by default. Only update team records needed for the uploaded team. |
| Backend/MCP/frontend | No source changes were made. Rebuild/redeploy only if the activation path requires it. |
| UI terminology | No UI source file edits were made. Renewable terminology is contained in team JSON and docs. |

## Search indexes and data grouping

| Index | Agent | Source files |
|---|---|---|
| `macae-renewable-energy-renewable-assets-index` | `RenewableAssetAgent` | `renewable_assets.csv` |
| `macae-renewable-energy-generation-operations-index` | `GenerationForecastAgent` | `generation_forecasts.csv`, `market_settlements.csv` |
| `macae-renewable-energy-work-orders-index` | `MaintenanceRiskAgent` | `work_orders.csv` |
| `macae-renewable-energy-grid-compliance-index` | `GridComplianceAgent` | `grid_interconnections.csv`, `compliance_obligations.csv`, `environmental_events.csv` |

## Required proof before cloud mutation

1. Target subscription, tenant, resource group, and azd environment.
2. Backend endpoint and user principal used for team upload.
3. Storage account, Blob containers or prefixes, and whether existing data will be overwritten.
4. Search service endpoint and exact index names.
5. Confirmation that datasets are synthetic or approved customer-owned demo data.
6. Snapshot or rollback plan for existing team config, Blob documents, Search documents/indexes, and Cosmos records.
7. Explicit confirmation immediately before any overwrite, delete, reset, index recreation, postdeploy rerun, or redeploy.

## Rollback considerations

| Component | Rollback expectation |
|---|---|
| Team config | Keep a copy of the prior team record if updating an existing team. This generated team uses a new `team_id`, so rollback should usually be delete-only for that team record. |
| Blob data | Snapshot or copy previous objects before replacement if reusing containers. Prefer dedicated renewable energy containers/prefixes for demo activation. |
| Search indexes | Prefer scoped document replacement. Recreate an index only when schema changes are intentional and confirmed. |
| Cosmos DB | Do not clear sessions, plans, or user state unless a demo-only scope is proven and confirmed. |

## Recommended smoke checks after activation

1. Open the MACE UI and upload or select `Renewable Energy Operations Team`.
2. Confirm the team card shows six agents and the three renewable energy starting tasks.
3. Run `Portfolio Performance Review` and confirm answers draw from asset, forecast, work order, compliance, and settlement context.
4. Run `Grid Compliance Escalation` and confirm responses include compliance status and escalation-ready actions without exposing sensitive grid details.
5. Confirm no real personal, financial, or critical infrastructure data appears in generated demo outputs.

# Renewable Energy Industry Adaptation

This adaptation adds a runtime-ready renewable energy operations pack for MACE. It targets utility-scale wind, solar, and battery energy storage operations and supports a demo narrative around asset portfolio performance, maintenance and curtailment risk, grid/compliance review, and dispatch or remediation recommendations.

## Generated runtime files

| Path | Purpose |
|---|---|
| `data/agent_teams/renewable_energy_operations.json` | Uploadable MACE team configuration for the Renewable Energy Operations Team. |
| `data/datasets/renewable_energy/renewable_assets.csv` | Synthetic asset portfolio records. |
| `data/datasets/renewable_energy/generation_forecasts.csv` | Synthetic generation forecast and curtailment-risk records. |
| `data/datasets/renewable_energy/work_orders.csv` | Synthetic maintenance work order records. |
| `data/datasets/renewable_energy/grid_interconnections.csv` | Synthetic interconnection and grid constraint records. |
| `data/datasets/renewable_energy/compliance_obligations.csv` | Synthetic compliance obligation records. |
| `data/datasets/renewable_energy/market_settlements.csv` | Synthetic market settlement records. |
| `data/datasets/renewable_energy/environmental_events.csv` | Synthetic environmental event records. |

No `data/industry_packs/` mirror was created because this MACE clone activates runtime artifacts from `data/agent_teams/*.json` and `data/datasets/**`.

## Team design

| Agent | Capability | Search index | Role |
|---|---|---|---|
| `RenewableAssetAgent` | RAG | `macae-renewable-energy-renewable-assets-index` | Answers asset portfolio, operating status, capacity, and site readiness questions. |
| `GenerationForecastAgent` | RAG | `macae-renewable-energy-generation-operations-index` | Analyzes generation forecasts, curtailment risk, and market settlement context. |
| `MaintenanceRiskAgent` | RAG | `macae-renewable-energy-work-orders-index` | Reviews maintenance, safety, outage, and component-risk signals. |
| `GridComplianceAgent` | RAG | `macae-renewable-energy-grid-compliance-index` | Reviews grid interconnection, compliance obligation, and environmental event records. |
| `DispatchRecommendationAgent` | Reasoning | None | Synthesizes specialist-agent evidence into dispatch, maintenance, compliance, or remediation actions. |
| `ProxyAgent` | Clarification/handoff | None | Final proxy agent required for RAG-enabled teams. |

The team stays within the frontend limit of six agents. Two RAG indexes are composite groups so the pack can include all requested entities while preserving the hybrid RAG plus reasoning design.

## Compliance posture

Prompts and documentation include reminders for:

| Framework | Application in this pack |
|---|---|
| NERC CIP | Critical infrastructure, grid interconnection, communications, and continuity considerations. |
| FERC/market rules | Market settlement and dispatch-related controls. |
| ISO 55001 | Asset management, lifecycle maintenance, and reliability planning. |
| OSHA/safety | Work order safety flags and field-work escalation. |
| Environmental permitting | Environmental event and remediation tracking. |
| GDPR/privacy | Synthetic contact fields and privacy minimization for operator/community contacts. |

All generated records are synthetic demo data with fake identifiers and `.example.invalid` contacts.

## Demo starting tasks

1. Portfolio performance review across wind, solar, and storage assets.
2. Maintenance and curtailment risk prioritization.
3. Grid compliance escalation plan.

## Activation note

This skill generated files only. Cloud-mutating work such as team upload, Blob upload, Search index creation, document replacement, postdeploy script rerun, Cosmos cleanup, or rebuild/redeploy must be handled through the `deploy-adaptation` skill with explicit environment proof and confirmation.

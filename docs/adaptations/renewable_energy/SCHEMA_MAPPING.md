# Renewable Energy Schema Mapping

## Canonical concept mapping

| Canonical MACE concept | Renewable energy entity | Dataset | Primary key | Relationships |
|---|---|---|---|---|
| Domain master data | Renewable asset | `renewable_assets.csv` | `asset_id` | `site_id` links to grid, compliance, and environmental records. |
| Event/transaction signal | Generation forecast | `generation_forecasts.csv` | `forecast_id` | `asset_id` references `renewable_assets.asset_id`. |
| Event/transaction signal | Work order | `work_orders.csv` | `work_order_id` | `asset_id` references `renewable_assets.asset_id`. |
| External integration state | Grid interconnection | `grid_interconnections.csv` | `interconnection_id` | `site_id` references `renewable_assets.site_id`. |
| Policy/control state | Compliance obligation | `compliance_obligations.csv` | `obligation_id` | `site_id` references `renewable_assets.site_id`. |
| Financial transaction | Market settlement | `market_settlements.csv` | `settlement_id` | `asset_id` references `renewable_assets.asset_id`. |
| Event/exception signal | Environmental event | `environmental_events.csv` | `event_id` | `site_id` references `renewable_assets.site_id`. |

## Search index mapping

MACE Search indexes use the existing generic index shape created by `infra/scripts/index_datasets.py`: `id`, `content`, and `title`. The CSV files below are intended to be uploaded as documents into the listed index/container groups before indexing.

| Search index | Agent consumer | Source files | Notes |
|---|---|---|---|
| `macae-renewable-energy-renewable-assets-index` | `RenewableAssetAgent` | `renewable_assets.csv` | One entity index for asset portfolio records. |
| `macae-renewable-energy-generation-operations-index` | `GenerationForecastAgent` | `generation_forecasts.csv`, `market_settlements.csv` | Composite index by design so forecasts and settlement impact are retrieved together within the six-agent limit. |
| `macae-renewable-energy-work-orders-index` | `MaintenanceRiskAgent` | `work_orders.csv` | One entity index for maintenance and safety records. |
| `macae-renewable-energy-grid-compliance-index` | `GridComplianceAgent` | `grid_interconnections.csv`, `compliance_obligations.csv`, `environmental_events.csv` | Composite index by design so grid, obligation, and environmental context are retrieved together within the six-agent limit. |

## Field contracts

### `renewable_assets.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `asset_id` | string | Yes | Unique, format `RENEW-ASSET-NNN`. | IP-sensitive |
| `site_id` | string | Yes | Stable site identifier, joins to site-scoped datasets. | Critical infrastructure |
| `site_name` | string | Yes | Synthetic facility display name. | IP-sensitive |
| `asset_type` | string | Yes | `wind`, `solar`, or `battery_storage`. | Low |
| `region` | string | Yes | Operating region label, not a precise location. | Critical infrastructure |
| `capacity_mw` | decimal | Yes | Non-negative MW value. | IP-sensitive |
| `commercial_operation_date` | date | Yes | ISO `YYYY-MM-DD`. | Low |
| `operating_status` | string | Yes | Examples: `operating`, `constrained`, `commissioning`, `maintenance`, `retirement_review`, `curtailment_watch`. | Operational |
| `grid_node` | string | No | Synthetic grid node; may be blank for pending interconnection. | NERC CIP critical infrastructure |
| `owner_contact` | string | No | Fake `.example.invalid` contact only. | PII/GDPR |
| `sensitivity_tag` | string | Yes | Default `critical_infrastructure`. | Compliance metadata |
| `notes` | string | No | Short operational context. | Operational |

Edge cases include a blank `grid_node`, a retirement-review asset, and an asset under curtailment watch.

### `generation_forecasts.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `forecast_id` | string | Yes | Unique, format `FCST-YYYY-NNN`. | IP-sensitive |
| `asset_id` | string | Yes | Must match `renewable_assets.asset_id`. | IP-sensitive |
| `forecast_date` | date | Yes | ISO `YYYY-MM-DD`. | Operational |
| `forecast_window` | string | Yes | Examples: `day_ahead`, `evening_peak`. | Operational |
| `expected_mwh` | decimal | Yes | Non-negative MWh. | Commercially sensitive |
| `p50_mwh` | decimal | Yes | Non-negative MWh. | Commercially sensitive |
| `p90_mwh` | decimal | Yes | Non-negative MWh. | Commercially sensitive |
| `curtailment_risk` | string | Yes | `low`, `medium`, or `high`. | Operational |
| `weather_driver` | string | No | Synthetic weather or dispatch driver. | Low |
| `confidence_score` | decimal | Yes | 0.00 to 1.00. | Operational |
| `model_version` | string | Yes | Synthetic model version. | IP-sensitive |
| `exception_note` | string | No | May be blank. | Operational |

Edge cases include zero generation during outage, low confidence during commissioning, and high curtailment risk.

### `work_orders.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `work_order_id` | string | Yes | Unique, format `WO-RE-NNNN`. | Operational |
| `asset_id` | string | Yes | Must match `renewable_assets.asset_id`. | IP-sensitive |
| `opened_date` | date | Yes | ISO `YYYY-MM-DD`. | Operational |
| `priority` | string | Yes | `low`, `medium`, or `high`. | Operational |
| `status` | string | Yes | Examples: `open`, `scheduled`, `in_progress`, `blocked`, `overdue`. | Operational |
| `maintenance_type` | string | Yes | Preventive, corrective, commissioning, vegetation, planned outage, or diagnostic category. | Operational |
| `component` | string | Yes | Component under maintenance. | IP-sensitive |
| `estimated_downtime_hours` | decimal | Yes | Non-negative hours. | Operational |
| `assigned_team` | string | Yes | Synthetic team label. | Low |
| `technician_contact` | string | No | Fake `.example.invalid` contact only; may be blank. | PII/GDPR |
| `safety_flag` | boolean | Yes | `true` or `false`. | OSHA/safety |
| `due_date` | date | Yes | ISO `YYYY-MM-DD`. | Operational |
| `notes` | string | No | Maintenance context. | Operational |

Edge cases include a blocked work order, an overdue high-priority work order, and a missing technician contact.

### `grid_interconnections.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `interconnection_id` | string | Yes | Unique, format `IX-RE-NNN`. | Critical infrastructure |
| `site_id` | string | Yes | Must match `renewable_assets.site_id`. | Critical infrastructure |
| `queue_position` | integer | Yes | Positive integer. | Operational |
| `transmission_operator` | string | Yes | Synthetic operator name. | Critical infrastructure |
| `substation_id` | string | No | Synthetic identifier; may be blank for pending studies. | NERC CIP critical infrastructure |
| `interconnection_status` | string | Yes | Examples: `active`, `conditional`, `commissioning`, `maintenance_hold`, `pending`, `curtailment_watch`. | Operational |
| `max_export_mw` | decimal | Yes | Non-negative MW. | Critical infrastructure |
| `curtailment_limit_mw` | decimal | Yes | Non-negative MW, less than or equal to export limit when constrained. | Critical infrastructure |
| `study_due_date` | date | Yes | ISO `YYYY-MM-DD`. | Operational |
| `critical_infrastructure_flag` | boolean | Yes | `true` or `false`. | NERC CIP |
| `communications_channel` | string | No | Synthetic channel label only; may be blank. | NERC CIP critical infrastructure |
| `notes` | string | No | Constraint or study context. | Operational |

Edge cases include blank substation/channel values, zero export during maintenance, and active curtailment watch.

### `compliance_obligations.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `obligation_id` | string | Yes | Unique, format `COMP-RE-NNN`. | Compliance |
| `site_id` | string | Yes | Must match `renewable_assets.site_id`. | Critical infrastructure |
| `framework` | string | Yes | NERC CIP, FERC/market rules, ISO 55001, OSHA/safety, Environmental permitting, or GDPR/privacy. | Compliance |
| `requirement_area` | string | Yes | Control, evidence, or requirement description. | Compliance |
| `due_date` | date | Yes | ISO `YYYY-MM-DD`. | Compliance |
| `status` | string | Yes | Examples: `on_track`, `open`, `at_risk`, `overdue`, `missing_evidence`. | Compliance |
| `evidence_owner` | string | Yes | Synthetic organization owner. | Operational |
| `evidence_location` | string | No | Synthetic URI only; may be blank. | Compliance/IP-sensitive |
| `risk_level` | string | Yes | `low`, `medium`, or `high`. | Compliance |
| `renewal_frequency` | string | Yes | Examples: annual, quarterly, monthly, event-based, one-time, change-based. | Compliance |
| `escalation_required` | boolean | Yes | `true` or `false`. | Compliance |
| `notes` | string | No | Evidence or risk context. | Compliance |

Edge cases include overdue evidence, missing evidence location, and same-day safety evidence due.

### `market_settlements.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `settlement_id` | string | Yes | Unique, format `SETTLE-RE-NNN`. | Financial |
| `asset_id` | string | Yes | Must match `renewable_assets.asset_id`. | IP-sensitive |
| `market_date` | date | Yes | ISO `YYYY-MM-DD`. | Financial |
| `market` | string | Yes | Synthetic market label such as day-ahead or real-time. | Financial |
| `settlement_type` | string | Yes | Examples: energy, ancillary, capacity. | Financial |
| `settled_mwh` | decimal | Yes | Non-negative MWh. | Financial |
| `price_per_mwh` | decimal | Yes | May be negative in edge cases. | Financial |
| `total_value_usd` | decimal | Yes | Demo-only USD value. | Financial |
| `variance_usd` | decimal | Yes | Positive or negative demo variance. | Financial |
| `settlement_status` | string | Yes | `settled`, `estimated`, or `contested`. | Financial |
| `invoice_reference` | string | No | Synthetic invoice reference. | Financial |
| `notes` | string | No | Settlement context. | Financial |

Edge cases include negative pricing, contested settlement, and zero settlement during outage.

### `environmental_events.csv`

| Field | Type | Required | Constraints | Sensitivity tag |
|---|---|---:|---|---|
| `event_id` | string | Yes | Unique, format `ENV-RE-NNN`. | Environmental |
| `site_id` | string | Yes | Must match `renewable_assets.site_id`. | Critical infrastructure |
| `event_date` | date | Yes | ISO `YYYY-MM-DD`. | Environmental |
| `event_type` | string | Yes | Inspection, wildlife, complaint, spill, fire-code, or permit-related type. | Environmental |
| `severity` | string | Yes | `low`, `medium`, or `high`. | Environmental |
| `permit_id` | string | Yes | Synthetic permit ID only. | Compliance |
| `reported_to_agency` | boolean | Yes | `true` or `false`. | Compliance |
| `remediation_status` | string | Yes | Examples: open, scheduled, in_progress, escalated, closed. | Compliance |
| `wildlife_impact` | string | No | Synthetic impact category. | Environmental |
| `estimated_cost_usd` | decimal | Yes | Non-negative demo USD value. | Financial |
| `community_contact` | string | No | Fake `.example.invalid` contact only; may be blank. | PII/GDPR |
| `notes` | string | No | Event context. | Environmental |

Edge cases include a high-severity event, pending agency report, and missing community contact.

## Data handling and sensitivity notes

All rows are synthetic and non-production. Customer data swaps must preserve the same field contracts or document intentional schema changes. Do not include secrets, precise physical security details, real grid access details, real personal data, or production settlement data in demo datasets.

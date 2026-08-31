# infra_tf layout & naming conventions

The port lives in a new `infra_tf/` sibling of `infra/` so Bicep and Terraform **coexist**. Mirror
the source Bicep's module structure so the 1:1 mapping stays legible.

## Directory layout

```
infra_tf/
  providers.tf              # terraform{} + required_providers + backend + provider "azurerm"
  variables.tf              # one variable per Bicep param (+ subscription_id)
  main.tf                   # root: resources + module calls mirroring main.bicep
  outputs.tf                # every Bicep output, value-equivalent (contract-preserving)
  <env>.tfvars              # per-stage values, translated from params/<env>.bicepparam
  modules/
    <module-name>/          # one child module per Bicep module
      main.tf
      variables.tf
      outputs.tf
```

Runtime-only, **git-ignored**, never authored by this skill (the CI/CD skill writes them at run
time): `backend.tf` overrides, `backend.ci.hcl`, `state-scope.auto.tfvars`, `.terraform/`,
`*.tfstate*`, `tfplan`.

## Naming

- **Files/dirs**: lowercase, mirror the Bicep module path (`modules/monitoring/log-analytics.bicep`
  → `modules/monitoring-log-analytics/` or a nested `modules/monitoring/log_analytics/`; pick one
  and stay consistent — flat `modules/<area>-<name>/` is simplest).
- **Resource/variable/output identifiers**: `snake_case`. Bicep camelCase → snake_case
  (`appServicePlanSku` → `app_service_plan_sku`).
- **Azure resource *names*** (the `name = ...` value): reproduce the source's naming expression
  verbatim so deployed resource names are unchanged from the Bicep output.
- **Unique suffix**: where Bicep used `uniqueString(...)`, use a single `random_string.suffix`
  (6 lowercase alphanumerics) in the root and thread `local.suffix` through modules — matches the
  reference accelerator.

## Per-environment values

- One `infra_tf/<env>.tfvars` per stage discovered under `infra/params/` (e.g. `dev.bicepparam`
  → `dev.tfvars`). Same stage names as the Bicep pipeline so promotion order carries over.
- Keys are `snake_case`, values only. CI-identity values stay faithful
  (`deploying_user_principal_type = "ServicePrincipal"` in the CI stage's tfvars).
- Do **not** put backend/state coordinates in `<env>.tfvars`; those are the CI/CD skill's runtime
  `backend.ci.hcl` (from `vars.TF_BACKEND_*`).

## Backend (block only, values injected by CI)

Author only the **partial** block in `providers.tf`:

```hcl
backend "azurerm" {
  use_oidc         = true   # authenticate the backend with the GitHub OIDC token
  use_azuread_auth = true   # required where shared-key access is disabled on the SA
}
```

`resource_group_name` / `storage_account_name` / `container_name` / `key` are supplied at
`terraform init -backend-config=...` time by the pipeline from `vars.TF_BACKEND_*` — one state
`key = <env>.tfstate` per environment. The state storage account itself is a **manual bootstrap
prerequisite** owned by the CI/CD skill's `backend-bootstrap` doc; this skill never creates it.

## Provider auth (documentation only)

The generated HCL authenticates via OIDC in CI: `ARM_USE_OIDC=true` and
`ARM_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID` + `TF_VAR_subscription_id`, all GitHub **Variables**
(`vars.*`, never secrets). Locally the maintainer's `az login` session is used. This skill does not
set any of that — it only ensures `var.subscription_id` exists and the provider reads it.

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
  terraform.tfvars          # non-secret values for the selected deployment flavor
  <env>.tfvars              # per-stage values, translated from params/<env>.bicepparam
  modules/
    <source-area>/          # preserve the Bicep path below modules/
      <module-name>/        # one directory per reachable local *.bicep module
        main.tf
        variables.tf
        outputs.tf
        versions.tf
```

Runtime-only, **git-ignored**, never authored by this skill (the CI/CD skill writes them at run
time): `backend.tf` overrides, `backend.ci.hcl`, `state-scope.auto.tfvars`, `.terraform/`,
`*.tfstate*`, `tfplan`.

## Naming

- **Files/dirs**: lowercase and mirror the source hierarchy exactly below `modules/`. For example,
  `<implementation-root>/modules/monitoring/log-analytics.bicep` maps to
  `infra_tf/modules/monitoring/log-analytics/`. Remove only the `.bicep` extension; do not flatten,
  combine, or rename source modules.
- **Resource/variable/child-output identifiers**: `snake_case`. Bicep camelCase → snake_case
  (`appServicePlanSku` → `app_service_plan_sku`). Root contract outputs are different: ASCII-
  lowercase the exact public Bicep output key so the post-deploy bridge's uppercase operation
  preserves canonical and legacy aliases.
- **Azure resource *names*** (the `name = ...` value): reproduce the source's naming expression
  verbatim so deployed resource names are unchanged from the Bicep output.
- **Unique suffix**: where Bicep used `uniqueString(...)`, expose a nullable override and use a
  deterministic hash of the same source inputs as the non-interactive fallback. Preserve the
  source length and thread the resolved value through modules. Existing deployments set the
  override to their current suffix because Terraform cannot reproduce ARM's exact hash.

## Child-module file contract

Every generated child module always contains these four files:

| File | Mandatory contents |
|---|---|
| `main.tf` | Resources, locals, data sources, and nested module calls translated from the source file |
| `variables.tf` | One variable for every Bicep module parameter |
| `outputs.tf` | One output for every Bicep module output |
| `versions.tf` | Terraform version and every provider used by that module |

Create the file even when the source has no corresponding blocks. A source file reused by multiple
module calls still maps to one Terraform module directory. Provider requirements belong in each
child's `versions.tf`; provider authentication and subscription configuration belong only at root.

## Per-environment values

- Always emit `terraform.tfvars` for the selected flavor. Translate literal values from the
  selected sibling ARM `*.parameters.json` file or `.bicepparam` source.
- `infra/main.parameters.json` is the standard parameter bridge for `bicep` and `avm`;
  `infra/main.waf.parameters.json` supplies the fixed `avm-waf` settings. Override the standard
  file's environment-driven flavor default with the flavor selected for the conversion.
- ARM parameter expressions such as `${AZURE_ENV_NAME}` are azd substitutions, not Terraform
  syntax. Do not copy them literally. Supply non-secret runtime values through `TF_VAR_*`; never
  commit resolved secrets.
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

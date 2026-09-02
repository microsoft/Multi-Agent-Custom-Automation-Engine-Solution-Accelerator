# Bicep → Terraform mapping rules

Reference for the faithful 1:1 port. Apply these when translating `main.bicep` (and its modules)
into `infra_tf/`. When a construct isn't listed, prefer the idiomatic `azurerm` resource; fall back
to `azapi` only for preview/unsupported types. **Every deviation from a direct mapping must be
recorded in the skill's "Deviations" report.**

## Language constructs

| Bicep | Terraform |
|---|---|
| `param name type = default` | `variable "name" { type = ...; default = ... }` |
| `@allowed([...])` | `variable { validation { condition = contains([...], var.name); error_message = ... } }` |
| `@minValue(n)` / `@maxValue(n)` | `variable { validation { condition = var.n >= n } }` |
| `@minLength`/`@maxLength` | `variable { validation { condition = length(...) >= n } }` |
| `@secure()` param | `variable { sensitive = true }` |
| `var x = expr` | `locals { x = expr }` |
| `resource r 'type@api' = {...}` | `resource "azurerm_<type>" "r" {...}` (or `azapi_resource` for preview) |
| `module m 'path' = { params }` | `module "m" { source = "./modules/<name>"; <inputs> }` |
| `output name = expr` | `output "name" { value = expr }` (see output contract) |
| `uniqueString(...)` | Nullable override plus deterministic hash local with the same length; report that Terraform cannot reproduce ARM's exact hash |
| `resourceGroup().location` | `azurerm_resource_group.main.location` (RG is a resource in TF) |
| `subscription().id` | `data.azurerm_client_config.current.subscription_id` |
| `resourceGroup().id` | `azurerm_resource_group.main.id` |
| `deployer().objectId` | `data.azurerm_client_config.current.object_id` |
| `deployer().tenantId` | `data.azurerm_client_config.current.tenant_id` |
| `<resource>.id` / `.properties.x` | `<tf_resource>.id` / `<tf_resource>.<attr>` |
| `existing` resource | `data "azurerm_<type>" "..."` data source |
| `if (cond)` on a resource/module | `count = cond ? 1 : 0` only when the complete condition is known during planning; reference as `[0]` |
| `[for x in xs: ...]` resource/module loop | Use `for_each` with configuration-known map keys; values may contain apply-time results |
| ternary `cond ? a : b` | `cond ? a : b` |
| `union()/concat()` | `merge()/concat()` |
| `contains(array, value)` | `contains(collection, value)` |
| `contains(string, substring)` | `strcontains(string, substring)` |
| string interpolation `'${x}'` | `"${x}"` |
| `loadTextContent()` | `file("...")` |
| `dependsOn: [a, b]` (explicit only) | `depends_on = [a, b]` — otherwise rely on implicit refs |

## Scope & resource group

- Bicep `targetScope = 'resourceGroup'` with an assumed-existing RG maps to a managed Terraform
  resource: `resource "azurerm_resource_group" "main" { name = ...; location = ... }`.
  All resources reference `azurerm_resource_group.main`, so the Terraform port creates the group.
- Preserve the source RG naming expression. If the deployment receives the RG name externally,
  add a `resource_group_name` variable and create the managed group with that name.

## Plan-time-known cardinality

Terraform must know every resource and module instance address while creating the plan. Bicep can
condition resources on values produced during deployment, but Terraform cannot use an apply-time
resource attribute to decide `count` or the keys of `for_each`.

- Base `count` only on explicit configuration booleans, enum selections, or locals derived
  exclusively from configuration-known values.
- Never test a generated resource ID, principal ID, endpoint, or module output in `count`, even when
  it appears as `var.*` inside a child module. Trace every child variable to the root module
  argument that supplies it.
- Pass explicit booleans such as `use_existing_ai_project` and `assign_deployer_roles` separately
  from the resource IDs used by the created role assignments.
- Use maps with static semantic keys for generated identities:

  ```hcl
  workload_principals = {
    backend  = module.backend.principal_id
    frontend = module.frontend.principal_id
    mcp      = module.mcp.principal_id
  }
  ```

  `for_each = local.workload_principals` is valid because the keys are known even though the
  principal-ID values are not. Do not use `toset()` on generated IDs because set elements become
  instance keys and remain unknown until apply.
- Apply-time values may populate resource arguments after an instance is selected; they must not
  decide whether the instance exists.

Perform this provenance audit across root-to-child module boundaries. `terraform validate` does not
detect unknown cardinality; the failure normally appears during `terraform plan`.

## Type-aware functions and provider deprecations

- Terraform `contains()` accepts collections, not strings. Translate Bicep substring checks to
  `strcontains()`, including identity checks such as
  `strcontains(local.identity_type, "SystemAssigned")`.
- Inspect the selected provider schema for deprecated arguments before completing a mapping. Treat
  provider deprecation warnings as conversion defects.
- AzureRM Application Insights maps Bicep/ARM `disableIpMasking` to
  `ip_masking_enabled = !var.disable_ip_masking`. Do not emit deprecated
  `disable_ip_masking`, which is removed in AzureRM v5.
- AzureRM 4.81+ replaces `local_authentication_disabled` with the positive-form
  `local_authentication_enabled` argument for Cosmos DB and Application Insights resources.
- AzureRM Container App CORS uses `exposed_headers`, not the ARM-style `exposeHeaders` spelling.
- Omit `zone_redundancy_enabled` from a non-WAF Container Apps environment. AzureRM requires
  `infrastructure_subnet_id` whenever that argument is present, including when its value is null.
- When Search `disableLocalAuth` is true, omit `authOptions` from an AzAPI request instead of
  serializing an empty object; the Search API requires that property to be null.
- Do not place `DOCKER_REGISTRY_SERVER_URL` in `azurerm_linux_web_app.app_settings`; configure the
  registry through `site_config.application_stack` because AzureRM reserves that setting.
- Do not configure `site_config.linux_fx_version` on `azurerm_linux_web_app`; AzureRM 4.x computes
  it from `site_config.application_stack.docker_image_name` and `docker_registry_url`.
- Use subscription-scoped `role_definition_id` values for role assignments instead of display-name
  lookup, and pass the deployer's actual `User` or `ServicePrincipal` type explicitly.

## Provider skeleton (`providers.tf`)

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    # add only if used by the source:
    azapi  = { source = "Azure/azapi",  version = "~> 2.0" }   # preview Microsoft.* types
    random = { source = "hashicorp/random", version = "~> 3.6" } # uniqueString() replacement
  }
  # Partial backend — init values (rg/sa/container/key) supplied by CI, never committed.
  backend "azurerm" {
    use_oidc         = true
    use_azuread_auth = true
  }
}

data "azurerm_client_config" "current" {}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
  storage_use_azuread = true
}
```

## Child-module contract and provider declarations (REQUIRED)

Every reachable local Bicep module maps to one mirrored Terraform directory containing
`main.tf`, `variables.tf`, `outputs.tf`, and `versions.tf`. Reused source modules are generated once
and called multiple times. Every child module declares every provider it uses. Terraform only
auto-resolves the `hashicorp/*` namespace, so omitting AzAPI's source causes `terraform init` to fail:

> provider registry ... does not have a provider named registry.terraform.io/hashicorp/azapi

Every child ships `versions.tf`, including AzureRM-only modules:

```hcl
# infra_tf/modules/<name>/versions.tf
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }
}
```

Remove providers the module does not use and add `random` when it uses `random_*`. Declaring a
provider only in the root is not enough to establish a non-HashiCorp provider's source address.
Child modules declare requirements only; they never configure Azure credentials or subscription.

## Common resource-type map (azurerm)

| Bicep type (`Microsoft.*`) | Terraform resource |
|---|---|
| `Resources/resourceGroups` | `azurerm_resource_group` |
| `OperationalInsights/workspaces` | `azurerm_log_analytics_workspace` |
| `Insights/components` | `azurerm_application_insights` |
| `ContainerRegistry/registries` | `azurerm_container_registry` |
| `App/managedEnvironments` | `azurerm_container_app_environment` |
| `App/containerApps` | `azurerm_container_app` |
| `Web/serverfarms` | `azurerm_service_plan` |
| `Web/sites` (app) | `azurerm_linux_web_app` / `azurerm_windows_web_app` |
| `Web/sites` (function) | `azurerm_linux_function_app` |
| `ManagedIdentity/userAssignedIdentities` | `azurerm_user_assigned_identity` |
| `Authorization/roleAssignments` | `azurerm_role_assignment` |
| `KeyVault/vaults` | `azurerm_key_vault` (+ `azurerm_key_vault_secret`) |
| `DocumentDB/databaseAccounts` (nosql) | `azurerm_cosmosdb_account` (+ `_sql_database`/`_sql_container`) |
| `DocumentDB` (mongo) | `azurerm_cosmosdb_account` kind=MongoDB (+ `_mongo_database`) |
| `Sql/servers` + `/databases` | `azurerm_mssql_server` + `azurerm_mssql_database` |
| `Storage/storageAccounts` | `azurerm_storage_account` (+ `_container`/`_blob`) |
| `Search/searchServices` | `azurerm_search_service` |
| `CognitiveServices/accounts` | `azurerm_cognitive_account` (kind `AIServices`/`OpenAI`) |
| `CognitiveServices/accounts/deployments` | `azurerm_cognitive_deployment` |
| `EventGrid/systemTopics` (+ subs) | `azurerm_eventgrid_system_topic` (+ `_event_subscription`) |
| `EventHub/namespaces` (+ hubs) | `azurerm_eventhub_namespace` (+ `azurerm_eventhub`) |
| `DBforPostgreSQL/flexibleServers` | `azurerm_postgresql_flexible_server` |
| `AppConfiguration/configurationStores` | `azurerm_app_configuration` |
| `Network/virtualNetworks` (+ subnets) | `azurerm_virtual_network` (+ `azurerm_subnet`) |
| `Network/privateEndpoints` | `azurerm_private_endpoint` |
| `Network/privateDnsZones` | `azurerm_private_dns_zone` (+ `_virtual_network_link`) |
| `Insights/diagnosticSettings` | `azurerm_monitor_diagnostic_setting` |
| `Portal/dashboards` | `azurerm_portal_dashboard` |
| `Insights/workbooks` | `azurerm_application_insights_workbook` |

## Enum / value mappings (ARM → azurerm — easy to miss)

Some ARM enum values are spelled differently (or don't exist) in azurerm and will fail at
`terraform plan` (not `validate`, since these are provider-side value checks), so translate them:

- **Storage container `publicAccess`.** ARM/Bicep `'None'` → azurerm `container_access_type =
  "private"`. azurerm only accepts `"blob"`, `"container"`, `"private"` — a lowercased `"none"`
  errors with *"expected container_access_type to be one of ..."*. Map defensively, e.g.
  `container_access_type = lower(x.public_access) == "none" ? "private" : lower(x.public_access)`.
  (`'Blob'`→`"blob"`, `'Container'`→`"container"` map by lowercasing.)

## AI Foundry & preview types (`azapi`)

AI Foundry projects/connections and other preview `Microsoft.CognitiveServices/accounts/...`
resources have no stable `azurerm` resource. Use `azapi` when the selected AzureRM version lacks a
faithful resource:

```hcl
# enable project management on the AI Services account
resource "azapi_update_resource" "ai_services_allow_projects" {
  type        = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  resource_id = azurerm_cognitive_account.ai.id
  body = { properties = { allowProjectManagement = true } }
}

resource "azapi_resource" "ai_foundry_project" {
  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name                      = "${var.solution_name}-project-${local.suffix}"
  parent_id                 = azurerm_cognitive_account.ai.id
  location                  = azurerm_resource_group.main.location
  schema_validation_enabled = false

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind       = "AIServices"
    properties = {}
  }
  depends_on = [azapi_update_resource.ai_services_allow_projects]
}
```

Match the **exact `@api-version`** the source Bicep declared. For connection resources whose secret
`credentials.key` is write-only (GET returns null), add `lifecycle { ignore_changes = [body] }` to
prevent perpetual drift only when the provider/API demonstrably returns that write-only value as
null.

**`azapi_resource` gotchas (v2):**
- **`identity` is a top-level nested block, not an argument or a member of `body`.** Write
  `identity { type = "SystemAssigned" }`, never `identity = { type = "SystemAssigned" }` (the latter fails validate with
  *"An argument named identity is not expected here"*). The same applies to `timeouts`.
- **Set `schema_validation_enabled = false`** on any `azapi_resource` using a recent or preview
  `@api-version` (e.g. `2025-*`, `*-preview`). The provider's *embedded* schema lags behind ARM,
  so otherwise validate fails with *"api-version is invalid"* or *"<prop> is not expected here"*
  even though the real ARM API accepts it. This does not weaken real deployment validation. The
  Verify this requirement against the selected AzAPI version rather than assuming its embedded
  schema supports a newly released API version.
- **Do not set `schema_validation_enabled` on `azapi_update_resource`.** The update resource does
  not accept that argument in AzAPI 2.x, even when it targets a recent API version.
- Everything else (kind, properties, sku, …) goes inside the `body = { ... }` object.

## Dependencies

Preserve dependency edges, not only explicit `dependsOn` syntax. Prefer Terraform references that
create implicit dependencies. Add `depends_on` when translation turns a Bicep symbolic reference
into a plain string, constructed resource ID, or other expression from which Terraform cannot infer
the original edge. Record such explicit dependencies in the source-to-Terraform inventory.

## Derived defaults and nullable inputs

Terraform variable defaults cannot reference other variables, resources, or data sources. Translate
a Bicep parameter default such as `'aif-${solutionName}'` into a nullable override plus a local:

```hcl
variable "name" {
  type    = string
  default = null
}

locals {
  name = coalesce(var.name, "aif-${var.solution_name}")
}
```

Preserve Bicep nullable inputs with Terraform nullable types/defaults rather than empty-string
sentinels. Do not use `try()` or `coalesce()` to hide a missing required value.
When an empty string is the intended null fallback, use an explicit null conditional because Terraform `coalesce()` rejects both null and empty-string arguments.

For `uniqueString()` defaults, preserve non-interactive behavior with a deterministic fallback:

```hcl
variable "solution_unique_text" {
  type     = string
  default  = null
  nullable = true
}

locals {
  solution_unique_text = coalesce(
    var.solution_unique_text,
    substr(md5(join("-", [
      var.subscription_id,
      var.resource_group_name,
      var.solution_name,
    ])), 0, 5)
  )
}
```

Use the source's exact inputs and output length. Terraform cannot reproduce ARM `uniqueString()`
exactly, so existing deployments must set the override to their current suffix; fresh deployments
use the deterministic fallback without prompting. Do not make the override required and do not use
an unseeded random resource by default.

Values provided by Bicep deployment context are not user parameters. In particular, map
`deployer().objectId` directly to `data.azurerm_client_config.current.object_id`; do not introduce a
required `deployer_principal_id` variable unless the Bicep contract explicitly declares one.

## Fabric capacity

`Microsoft.Fabric/capacities` → `azurerm_fabric_capacity` (azurerm 4.x). Preserve `sku` and the
`administration_members` (from `FABRIC_ADMIN_MEMBERS`). If the installed provider version lacks it,
fall back to `azapi_resource` with `Microsoft.Fabric/capacities@<api-version>` and note the
deviation.

AzureRM models the Fabric SKU as a nested `sku { name = ..., tier = "Fabric" }` block, not a
top-level `sku_name` argument; the latter fails `terraform validate`.

## Parameters → variables → tfvars

- Each Bicep `param` becomes a `variable`. Keep the same name in `snake_case`
  (`solutionName` → `solution_name`), the same default, and encode decorators as `validation`.
- Add a `variable "subscription_id"` (the provider needs it; sourced from `TF_VAR_subscription_id`
  in CI) even if Bicep used `subscription().id` implicitly.
- Always create `infra_tf/terraform.tfvars` for the selected flavor. Translate literal values from
  the selected sibling ARM `*.parameters.json` file. For this repository,
  `main.parameters.json` is the standard `bicep`/`avm` bridge and `main.waf.parameters.json`
  supplies `avm-waf` literals and feature flags.
- Do not copy azd placeholders such as `${AZURE_ENV_NAME}` into tfvars: Terraform does not expand
  them. Map non-secret values to `TF_VAR_<snake_case_name>` and source sensitive values from the
  deployment environment or secret store.
- Translate `infra/params/<env>.bicepparam` assignments into `infra_tf/<env>.tfvars` (values only,
  `snake_case` keys). A Bicep `param foo = 'bar'` in the `.bicepparam` → `foo = "bar"` in `.tfvars`.

## Output contract (do not break)

The contract entrypoint may emit both canonical `UPPER_SNAKE` outputs and legacy camelCase aliases.
The post-deploy bridge runs `terraform output -json`, then **ascii-uppercases** each key. Therefore:

- Emit each root TF output using the **ASCII-lowercase form of the exact Bicep output name**:
  `output "RESOURCE_GROUP_NAME"` in Bicep → `output "resource_group_name"` in TF (upcases back to
  `RESOURCE_GROUP_NAME`), while legacy `resourceGroupName` → `resourcegroupname` (upcases back to
  `RESOURCEGROUPNAME`, matching bridge behavior for that alias). Do not insert or remove separators
  in root contract output names.
- Reproduce the **value expression** faithfully (same resource attribute / same computed string).
- Mark secret-bearing outputs `sensitive = true` (connection strings, keys) — matches how the
  reference marks `*_connection_string` / `instrumentation_key`.
- **Every contract-entrypoint output** must appear. Cross-check generated root `outputs.tf` against
  the separately inspected contract output list; a missing alias silently breaks post-deploy.
- Child-module outputs are internal Terraform identifiers and use `snake_case`.

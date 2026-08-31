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
| `uniqueString(...)` | `random_string.suffix` (6 lower-alnum) → `local.suffix` |
| `resourceGroup().location` | `azurerm_resource_group.main.location` (RG is a resource in TF) |
| `subscription().id` | `data.azurerm_client_config.current.subscription_id` |
| `resourceGroup().id` | `azurerm_resource_group.main.id` |
| `<resource>.id` / `.properties.x` | `<tf_resource>.id` / `<tf_resource>.<attr>` |
| `existing` resource | `data "azurerm_<type>" "..."` data source |
| `if (cond)` on a resource | `count = cond ? 1 : 0` (reference as `[0]`) |
| ternary `cond ? a : b` | `cond ? a : b` |
| `union()/concat()/contains()` | `merge()/concat()/contains()` |
| string interpolation `'${x}'` | `"${x}"` |
| `loadTextContent()` | `file("...")` |
| `dependsOn: [a, b]` (explicit only) | `depends_on = [a, b]` — otherwise rely on implicit refs |

## Scope & resource group

- Bicep `targetScope = 'resourceGroup'` with an assumed-existing RG → in Terraform the RG is a
  **managed resource**: `resource "azurerm_resource_group" "main" { name = ...; location = ... }`.
  All resources set `resource_group_name = azurerm_resource_group.main.name`. This is why the
  Terraform CI/CD skill drops the "ensure RG exists" step — Terraform creates it.
- Preserve the source's RG naming expression (e.g. `rg-${solutionName}-${suffix}`). If the source
  received the RG name as a param (`resourceGroupName`), keep a `resource_group_name` variable but
  still create the RG resource with that name so the port is self-contained.

## Provider skeleton (`providers.tf`)

```hcl
terraform {
  required_version = ">= 1.5.0"
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

## Child-module provider declarations (REQUIRED — common failure)

Terraform only auto-resolves the `hashicorp/*` namespace. Any **child module** that references a
non-hashicorp provider (notably `azapi`, whose real source is `Azure/azapi`) **must declare that
source itself** in its own `required_providers`, or `terraform init` fails with:

> provider registry ... does not have a provider named registry.terraform.io/hashicorp/azapi

So **every `infra_tf/modules/<name>/` that uses `azapi_*` (or `random_*`) must ship a `versions.tf`**
declaring those sources. `azurerm` also defaults correctly to `hashicorp/azurerm`, but declare it
too for any module that uses it (best practice, and harmless):

```hcl
# infra_tf/modules/<name>/versions.tf
terraform {
  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
    # add azurerm here too when the module uses azurerm_* resources/data sources:
    # azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}
```

Rule of thumb while authoring modules: if a module's `.tf` files contain `azapi_`, that module needs
`azapi` in its own `required_providers`. Declaring it only in the root `providers.tf` is **not**
enough — the requirement does not propagate down to child modules.

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
resources have no stable `azurerm` resource. Use `azapi` exactly as the reference accelerator does:

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
  body     = { kind = "AIServices", properties = {}, identity = { type = "SystemAssigned" } }
  depends_on = [azapi_update_resource.ai_services_allow_projects]
}
```

Match the **exact `@api-version`** the source Bicep declared. For connection resources whose secret
`credentials.key` is write-only (GET returns null), add `lifecycle { ignore_changes = [body] }` to
prevent perpetual drift (a known quirk documented in the reference accelerator).

**`azapi_resource` gotchas (v2):**
- **`identity` is a nested block, not an argument.** Write `identity { type = "SystemAssigned" }`,
  never `identity = { type = "SystemAssigned" }` (the latter fails validate with
  *"An argument named identity is not expected here"*). The same applies to `timeouts`.
- **Set `schema_validation_enabled = false`** on any `azapi_resource` using a recent or preview
  `@api-version` (e.g. `2025-*`, `*-preview`). The provider's *embedded* schema lags behind ARM,
  so otherwise validate fails with *"api-version is invalid"* or *"<prop> is not expected here"*
  even though the real ARM API accepts it. This does not weaken real deployment validation. The
  reference accelerator applies this flag to every preview-version azapi resource.
- **Do not set `schema_validation_enabled` on `azapi_update_resource`.** The update resource does
  not accept that argument in AzAPI 2.x, even when it targets a recent API version.
- Everything else (kind, properties, sku, …) goes inside the `body = { ... }` object.

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
- Translate `infra/params/<env>.bicepparam` assignments into `infra_tf/<env>.tfvars` (values only,
  `snake_case` keys). A Bicep `param foo = 'bar'` in the `.bicepparam` → `foo = "bar"` in `.tfvars`.

## Output contract (do not break)

`main.bicep` emits `UPPER_SNAKE` outputs the post-provision scripts read as env vars. The post-deploy
bridge runs `terraform output -json`, then **ascii-uppercases** each key. So:

- Emit each TF output using the **lowercase form** of the Bicep output name:
  `output "RESOURCE_GROUP_NAME"` in Bicep → `output "resource_group_name"` in TF (upcases back to
  `RESOURCE_GROUP_NAME`). Names are pure `[A-Z0-9_]`, so lower→upper round-trips exactly.
- Reproduce the **value expression** faithfully (same resource attribute / same computed string).
- Mark secret-bearing outputs `sensitive = true` (connection strings, keys) — matches how the
  reference marks `*_connection_string` / `instrumentation_key`.
- **Every** source output must appear. Cross-check the generated `outputs.tf` against the inspected
  output list before finishing; a missing or renamed output silently breaks post-deploy.

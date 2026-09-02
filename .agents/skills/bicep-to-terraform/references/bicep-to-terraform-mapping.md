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
| `uniqueString(...)` | No exact native equivalent. Prefer an explicit migration-safe input; if randomness is approved, preserve source length and report the deviation |
| `resourceGroup().location` | `azurerm_resource_group.main.location` (RG is a resource in TF) |
| `subscription().id` | `data.azurerm_client_config.current.subscription_id` |
| `resourceGroup().id` | `azurerm_resource_group.main.id` |
| `<resource>.id` / `.properties.x` | `<tf_resource>.id` / `<tf_resource>.<attr>` |
| `existing` resource | `data "azurerm_<type>" "..."` data source |
| `if (cond)` on a resource/module | `count = cond ? 1 : 0` for a singleton; reference as `[0]` |
| `[for x in xs: ...]` resource/module loop | Prefer `for_each` with a stable semantic key; use `count` only when identity is truly positional |
| ternary `cond ? a : b` | `cond ? a : b` |
| `union()/concat()/contains()` | `merge()/concat()/contains()` |
| string interpolation `'${x}'` | `"${x}"` |
| `loadTextContent()` | `file("...")` |
| `dependsOn: [a, b]` (explicit only) | `depends_on = [a, b]` — otherwise rely on implicit refs |

### `existing` resources

`resource ... existing = {}` is a compile-time lookup: it emits **nothing** into the compiled ARM
template, so it is invisible in `resources[]` and appears only in the manifest's
`existingResources[]`. Never treat a module as trivial because its resource list is empty — a module
with `resources: []` and a populated `existingResources[]` is a lookup-only module and must still be
ported.

`existing` has **two distinct meanings**, and they map to opposite Terraform constructs. **Do not
decide based on whether a parameter supplies the name or id** — it does in both cases. The question
that separates them is: *does this deployment create that resource itself?*

**1. Genuinely external** — the resource exists before the deployment runs (a shared vault, a
built-in role definition, a pre-provisioned VNet). Port it as a **`data` source**, keyed by the same
name/resource-group expression the Bicep used:

```hcl
data "azurerm_key_vault" "shared" {
  name                = var.existing_key_vault_name
  resource_group_name = var.platform_resource_group_name
}
```

**2. Created elsewhere in this same deployment** — another module already creates it, and this module
re-declares it only because Bicep's `scope:` and `parent:` require a *resource handle* rather than an
id string. That is a Bicep language workaround, not a real lookup. Terraform accepts the id directly,
so **thread the id through as a variable and write no data source at all**:

```bicep
// Bicep must re-declare the account purely to satisfy `scope:`
resource storageAccount 'Microsoft.Storage/storageAccounts@2025-08-01' existing = {
  name: last(split(storageAccountResourceId, '/'))
}
resource ra 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  ...
}
```

```hcl
variable "storage_account_resource_id" { type = string }

resource "azurerm_role_assignment" "storage_blob" {
  scope                = var.storage_account_resource_id
  principal_id         = var.principal_id
  role_definition_name = "Storage Blob Data Contributor"
}
```

A data source in case 2 is actively harmful: a pointless API call that also **races the module still
creating the resource**, since Terraform cannot infer ordering from a lookup-by-name and may read
before the resource exists.

Comparing the manifest's `existingResourceTypes` against its global `resourceTypes` is a useful first
pass — a type in both lists suggests case 2, a type in only the former suggests case 1 — but it is a
**type-level hint, not a verdict**: a deployment can create one resource of a type and reference a
different, external one of the same type. Confirm against the source before choosing.

In neither case may an `existing` declaration become a managed `resource` block, which would make
Terraform own — and on `destroy` delete — something the Bicep only read.

## Scope & resource group

- Bicep `targetScope = 'resourceGroup'` deploys into an existing resource group; it does not own
  that group. Map it to `data "azurerm_resource_group"` by default and keep creation as an external
  prerequisite, matching the source deployment boundary.
- Create `azurerm_resource_group` only when the source is subscription-scoped and explicitly
  creates the group, or when the user explicitly approves a self-contained Terraform deviation.
  For an existing deployment, include the required import/adoption procedure before managing it.
- Preserve the source resource-group name input/expression. Never silently change an externally
  owned resource group into a Terraform-owned resource.

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
faithful resource.

`bicep-facts.json` flags these for you: every type in `azapiRequiredTypes` (and every
`providerHints[]` entry whose `hint` is not `azurerm_expected`) is a candidate. Note that a GA
api-version does **not** imply azurerm coverage — AI Foundry projects ship GA-dated api-versions and
still need `azapi` — so confirm each candidate against the installed provider rather than judging by
the api-version alone.

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
  even though the real ARM API accepts it. This does not weaken real deployment validation — ARM
  still validates the payload at apply time; it only stops the provider from rejecting a body it
  cannot yet describe. Verify this requirement against the selected AzAPI version rather than
  assuming its embedded schema supports a newly released API version.
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

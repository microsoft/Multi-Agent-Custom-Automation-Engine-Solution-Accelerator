# Deployment Pre-Check Runner — Reference Guide

This document describes the **manual** deployment pre-check script. It is intended to be run **before** `azd up` to catch common configuration, identity, and capacity issues up front, saving time and avoiding mid-deployment failures.

> **Not wired into `azd up`.** The precheck is a standalone tool the operator invokes on demand. It is **not** registered as an `azd` hook, so `azd up` / `azd provision` will not run it automatically.

---

## How to Run

From the repository root, run the script that matches your shell:

```bash
# Linux / macOS / Codespaces
bash scripts/precheck.sh
```

```powershell
# Windows
pwsh scripts/precheck.ps1
```

| Platform | Script | Shell |
|----------|--------|-------|
| Windows (PowerShell) | [`scripts/precheck.ps1`](../scripts/precheck.ps1) | `pwsh` |
| Linux / macOS / Codespaces | [`scripts/precheck.sh`](../scripts/precheck.sh) | `bash` |

> **Note:** These scripts live in the top-level `scripts/` directory, separate from the `infra/scripts/` infrastructure code. They delegate model-quota work to `infra/scripts/quota_check_params.{ps1,sh}`.

### Exit Behavior

| Exit Code | Meaning |
|-----------|---------|
| `0` | All pre-checks passed (warnings allowed) |
| `1` | One or more critical checks failed — fix and re-run before invoking `azd up` |

When checks fail, the scripts collect **all** errors and display them as a numbered list at the end with actionable fix instructions.

### Severity Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Check passed |
| ⚠️ | Warning — surfaced in summary but does not block deployment |
| ❌ | Critical failure — blocks deployment |
| ℹ️ | Informational — context only |

---

## Pre-Checks Reference

The runner executes the following checks **in order**. Sections 10–12 and 15 were added after the original release to align with [DeploymentGuide.md](./DeploymentGuide.md) §1.1 / §1.2 and the most common cross-tenant footguns called out in [TroubleShootingSteps.md](./TroubleShootingSteps.md).

### 1. Environment Detection

| Detail | Description |
|--------|-------------|
| **What it checks** | Identifies the runtime environment: **Local**, **GitHub Codespaces**, or **Dev Container** |
| **Why it matters** | Some downstream checks are adjusted per environment (e.g., Docker is managed automatically in Codespaces / Dev Containers and is skipped on Local) |
| **Severity** | ℹ️ Informational only — never blocks deployment |

**How detection works:**

| Environment | Detection Signal |
|-------------|-----------------|
| GitHub Codespaces | `CODESPACES` or `CLOUDENV_ENVIRONMENT_ID` env vars are set |
| Dev Container | `REMOTE_CONTAINERS` or `DEVCONTAINER` env vars, or `/.dockerenv` file exists |
| Local | Default if neither of the above |

**Script references:** `detect_environment()` (bash) / `Test-Environment` (PowerShell).

---

### 2. Azure Developer CLI (azd)

| Detail | Description |
|--------|-------------|
| **What it checks** | `azd` is installed and version is **≥ 1.18.0** (and not the broken `1.23.9` build) |
| **Why it matters** | The project's `azure.yaml` declares `requiredVersions.azd: '>= 1.18.0 != 1.23.9'` |
| **Severity** | 🔴 **Critical** — blocks deployment if missing or outdated |
| **Fix** | Install or update: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd |

**Script references:** `check_azd()` / `Test-Azd`.

---

### 3. Azure CLI (az)

| Detail | Description |
|--------|-------------|
| **What it checks** | `az` CLI is installed **and** the user is logged in (`az account show` succeeds) |
| **Why it matters** | Required for provisioning Azure resources, quota checks, RBAC validation, and tenant inspection |
| **Severity** | 🔴 **Critical** — blocks deployment if not installed or not logged in |
| **Fix (not installed)** | Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |
| **Fix (not logged in)** | Run `az login` |

**Script references:** `check_azure_cli()` / `Test-AzureCLI`.

---

### 4. Bicep CLI

| Detail | Description |
|--------|-------------|
| **What it checks** | Bicep version is **≥ 0.33.0** (auto-installs via `az bicep install` if not found) |
| **Why it matters** | The project's `azure.yaml` declares `requiredVersions.bicep: '>= 0.33.0'` |
| **Severity** | 🔴 **Critical** — blocks deployment if version is too old and auto-install fails |
| **Fix** | Run `az bicep upgrade` or `az bicep install` |

**Script references:** `check_bicep()` / `Test-Bicep`.

---

### 5. Python

| Detail | Description |
|--------|-------------|
| **What it checks** | `python3` or `python` is available, plus `pip`/`pip3` |
| **Why it matters** | Backend and MCP services are Python-based; quota helper scripts also import Python utilities |
| **Severity** | 🔴 **Critical** (python) / 🟡 **Warning** (pip) |
| **Fix** | Install Python 3.x: https://www.python.org/downloads/ |

**Script references:** `check_python()` / `Test-Python`.

---

### 6. Node.js & npm

| Detail | Description |
|--------|-------------|
| **What it checks** | `node` and `npm` are installed |
| **Why it matters** | Required by the frontend `prepackage` hook (`npm install && npm run build`) |
| **Severity** | 🔴 **Critical** — blocks deployment |
| **Fix** | Install Node.js (includes npm): https://nodejs.org/ |

**Script references:** `check_node()` / `Test-Node`.

---

### 7. jq (JSON Processor) — Bash Only

| Detail | Description |
|--------|-------------|
| **What it checks** | `jq` is installed |
| **Why it matters** | Used by the bash precheck and `infra/scripts/quota_check_params.sh` to parse Azure CLI JSON output |
| **Severity** | 🔴 **Critical** (bash environments) |
| **Fix** | Install: https://jqlang.github.io/jq/download/ |

> **Note:** PowerShell scripts use `ConvertFrom-Json` natively, so `jq` is not required on Windows.

**Script references:** `check_jq()` (bash). Not applicable in PowerShell.

---

### 8. Docker

| Detail | Description |
|--------|-------------|
| **What it checks** | Docker is installed and the daemon is running |
| **Why it matters** | May be needed for container image builds or local MCP server testing |
| **Severity** | 🟡 **Warning** — does not block deployment |
| **Special behavior** | Skipped on **Local** (informational only); checked normally in **Codespaces** and **Dev Containers** where Docker is expected |
| **Fix** | Install Docker Desktop: https://www.docker.com/products/docker-desktop/ |

**Script references:** `check_docker()` / `Test-Docker`.

---

### 9. Azure Subscription Validation

| Detail | Description |
|--------|-------------|
| **What it checks** | Active Azure subscription exists with state = **Enabled** |
| **Why it matters** | A disabled, past-due, or expired subscription will cause all resource provisioning to fail |
| **Severity** | 🔴 **Critical** — blocks deployment |
| **Fix** | Reactivate the subscription in the [Azure Portal](https://portal.azure.com/#blade/Microsoft_Azure_Billing/SubscriptionsBlade). See [Reactivate a disabled Azure subscription](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-disabled). |

**Script references:** `check_azure_subscription()` / `Test-AzureSubscription`.

---

### 10. Azure Tenant Match

| Detail | Description |
|--------|-------------|
| **What it checks** | (a) The selected subscription's `tenantId` equals its `homeTenantId` (not a cross-tenant subscription); (b) the signed-in user is **not** a Guest in that tenant |
| **Why it matters** | Cross-tenant subscriptions can fail with `CrossTenantDeploymentNotPermitted`. Guest accounts frequently lack the directory permissions `azd up` needs to create role assignments and app registrations. |
| **Severity** | 🟡 **Warning** — surfaces a clear early signal but does not block deployment |
| **Fix (cross-tenant)** | Switch context to a subscription in the same tenant as your identity: `az account set --subscription <id>` |
| **Fix (guest)** | Sign in with a Member account in the target tenant, or have an administrator convert your Guest account to a Member |

> Microsoft Graph returns `userType=null` for many native Member accounts; the precheck only flags an explicit `Guest` value.

**Source:** [TroubleShootingSteps.md → CrossTenantDeploymentNotPermitted](./TroubleShootingSteps.md#subscription--access-issues)
**Script references:** `check_tenant_match()` / `Test-TenantMatch`.

---

### 11. Azure RBAC Roles (DeploymentGuide §1.1)

| Detail | Description |
|--------|-------------|
| **What it checks** | At subscription scope, the caller holds **Contributor** **and** at least one access-admin role: **User Access Administrator** *or* **Role Based Access Control Administrator**. **Owner** satisfies both requirements on its own. |
| **Why it matters** | Without `Microsoft.Authorization/roleAssignments/write` (UAA / RBAC Admin / Owner), the Bicep deployment cannot create the managed-identity role assignments the solution depends on. |
| **Severity** | 🟡 **Warning** — informational, because the caller may rely on inherited Management Group assignments that aren't visible at subscription scope, or on a service principal whose roles can't be enumerated from the user context |
| **Fix** | Ask a subscription admin to grant the missing role(s), or scope the deployment to a resource group where you already hold them. See [AzureAccountSetUp.md](./AzureAccountSetUp.md). |

> The check enumerates each individual role for visibility but only flags a warning when the **Contributor + (UAA or RBAC Admin)** combination is missing **and** Owner is not present.

**Script references:** `check_azure_roles()` / `Test-AzureRoles`.

---

### 12. App Registration Permission (DeploymentGuide §1.1)

| Detail | Description |
|--------|-------------|
| **What it checks** | The signed-in user is allowed to create Microsoft Entra ID application registrations. Two paths are evaluated in order: **(1)** a directory role assigned to the user that explicitly grants app-creation rights, or **(2)** the tenant's default user permissions (`/policies/authorizationPolicy → defaultUserRolePermissions.allowedToCreateApps == true`). |
| **Why it matters** | The post-deployment app authentication setup creates an app registration. Without permission, `azd` provisioning can succeed but the auth wiring step (or any future hook that creates app registrations) will fail. |
| **Severity** | 🟡 **Warning** — does not block infrastructure provisioning |
| **Fix** | Ask a tenant administrator to enable "Users can register applications" in Microsoft Entra → User settings, or assign you one of the granting directory roles below. |

#### Directory roles that grant app-creation rights

- Global Administrator
- Application Administrator
- Cloud Application Administrator
- Application Developer

#### Behavior notes

- Output always references the signed-in **UPN** so the verdict is unambiguous.
- The check is **skipped** when the active identity is not a user (e.g., service principal or managed identity), because their app-creation rights derive from Microsoft Graph API permissions that can't be reliably probed from the CLI.
- If neither the directory-role lookup nor the tenant-policy lookup is readable from the caller's context, the check emits a warning rather than a pass/fail.

**Script references:** `check_app_registration_permission()` / `Test-AppRegistrationPermission`.

---

### 13. Azure Resource Providers (DeploymentGuide §1.2)

| Detail | Description |
|--------|-------------|
| **What it checks** | All resource providers used by `infra/main.bicep` are in the **Registered** state on the active subscription |
| **Why it matters** | Unregistered providers cause `MissingSubscriptionRegistration` / `ResourceProviderError` failures partway through provisioning |
| **Severity** | 🟡 **Warning** — does not block (some providers auto-register on first use) |
| **Fix** | Register each provider once per subscription: `az provider register --namespace <Namespace>` |

#### Providers Verified

| Provider Namespace | Used For |
|---|---|
| `Microsoft.CognitiveServices` | Azure AI Foundry / OpenAI |
| `Microsoft.Search` | Azure AI Search |
| `Microsoft.App` | Azure Container Apps |
| `Microsoft.ContainerRegistry` | ACR |
| `Microsoft.DocumentDB` | Cosmos DB |
| `Microsoft.KeyVault` | Key Vault |
| `Microsoft.Storage` | Storage Accounts |
| `Microsoft.Web` | App Service / Function plans |
| `Microsoft.OperationalInsights` | Log Analytics |
| `Microsoft.Insights` | Application Insights |
| `Microsoft.ManagedIdentity` | User-assigned managed identities |

**Script references:** `check_resource_providers()` / `Test-ResourceProviders`.

---

### 14. azd Environment Variables

| Detail | Description |
|--------|-------------|
| **What it checks** | Key azd environment variables are set to valid values |
| **Why it matters** | Invalid regions or deployment types cause Bicep parameter validation failures during provisioning |
| **Severity** | 🔴 **Critical** (if set to an invalid value) / ℹ️ **Info** (if not set — `azd up` will prompt) |

#### Variables Validated

| Variable | Valid Values | Fix Command |
|----------|-------------|-------------|
| `AZURE_LOCATION` | `australiaeast`, `centralus`, `eastasia`, `eastus2`, `japaneast`, `northeurope`, `southeastasia`, `uksouth` | `azd env set AZURE_LOCATION '<region>'` |
| `AZURE_ENV_OPENAI_LOCATION` | `australiaeast`, `eastus2`, `francecentral`, `japaneast`, `norwayeast`, `swedencentral`, `uksouth`, `westus` | `azd env set AZURE_ENV_OPENAI_LOCATION '<region>'` |
| `AZURE_ENV_MODEL_DEPLOYMENT_TYPE` | `Standard`, `GlobalStandard` | `azd env set AZURE_ENV_MODEL_DEPLOYMENT_TYPE 'GlobalStandard'` |
| `AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE` | `Standard`, `GlobalStandard` | `azd env set AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE 'GlobalStandard'` |
| `AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE` | `Standard`, `GlobalStandard` | `azd env set AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE 'GlobalStandard'` |

> **Note:** The allowed region lists come from `infra/main.bicep` parameter constraints. If those change in Bicep, update the corresponding arrays in both precheck scripts.

**Script references:** `check_azd_env()` / `Test-AzdEnvironment`.

---

### 15. Deployment Hook Scripts

| Detail | Description |
|--------|-------------|
| **What it checks** | All scripts referenced by deployment hooks (prepackage, postdeploy) and quota validation exist on disk |
| **Why it matters** | Missing scripts cause hook failures during packaging or post-deployment steps |
| **Severity** | 🟡 **Warning** — alerts but does not block provisioning |

#### Scripts Verified

| Script Path | Purpose |
|-------------|---------|
| `infra/scripts/package_frontend.sh` | Frontend prepackage hook (bash) |
| `infra/scripts/package_frontend.ps1` | Frontend prepackage hook (PowerShell) |
| `infra/scripts/selecting_team_config_and_data.sh` | Post-deploy team config (bash) |
| `infra/scripts/Selecting-Team-Config-And-Data.ps1` | Post-deploy team config (PowerShell) |
| `infra/scripts/validate_model_quota.sh` | Model quota validation (bash) |
| `infra/scripts/validate_model_quota.ps1` | Model quota validation (PowerShell) |
| `infra/scripts/validate_model_deployment_quota.sh` | Model deployment quota validation (bash) |
| `infra/scripts/validate_model_deployment_quotas.ps1` | Model deployment quota validation (PowerShell) |

**Script references:** `check_hook_scripts()` / `Test-HookScripts`.

---

### 16. Azure OpenAI Model Quota (DeploymentGuide §1.3)

| Detail | Description |
|--------|-------------|
| **What it checks** | Available Azure OpenAI token quota for every model the solution deploys, across either the user-selected region or all default regions. **Delegates** to `infra/scripts/quota_check_params.{ps1,sh}` and lets that helper print its own tabular output. |
| **Why it matters** | Insufficient quota causes model deployment failures during provisioning. Surfacing the per-region availability lets the user pick a region with headroom before running `azd up`. |
| **Severity** | ℹ️ **Informational** — the precheck never adds an error or warning to the summary based on quota numbers. The user reads the table the helper prints and decides. |
| **Prerequisites** | Azure CLI logged in; `jq` available (bash); the helper script present at `infra/scripts/quota_check_params.{ps1,sh}` |

#### Default Models Checked

The model list is **never** passed by the precheck — it always comes from the helper script's defaults:

| Model SKU (as reported by Azure) | Required Capacity | Deployment Type |
|-------|------------------|-----------------|
| `gpt4.1` | 150 | GlobalStandard |
| `o4-mini` | 50 | GlobalStandard |
| `gpt4.1-mini` | 50 | GlobalStandard |

> ⚠️ **Naming gotcha:** Azure exposes these SKUs without a hyphen between `gpt` and the version (e.g., `OpenAI.GlobalStandard.gpt4.1`, **not** `gpt-4.1`). The defaults inside the helper already use the correct form. To override, edit `$DefaultModelCapacity` in `infra/scripts/quota_check_params.ps1` (and the matching constant in the bash sibling).

#### Default Regions Scanned

`australiaeast`, `eastus2`, `francecentral`, `japaneast`, `norwayeast`, `swedencentral`, `uksouth`, `westus`

The precheck resolves `AZURE_ENV_OPENAI_LOCATION` from the process environment first, then from `azd env get-value`. If a value is found, **only that region** is forwarded to the helper via `-Regions` / `--regions` (strict mode). If nothing is set, no region argument is passed and the helper scans all eight defaults.

#### How it works

1. Precheck reads the active subscription id from `az account show` and exports it as `AZURE_SUBSCRIPTION_ID` for the duration of the helper invocation (then restores the previous value).
2. Precheck invokes the platform-appropriate helper:
   - PowerShell: `pwsh -NoProfile -File infra/scripts/quota_check_params.ps1 [-Regions <region>]` (falls back to `powershell` if `pwsh` is missing)
   - Bash: `AZURE_SUBSCRIPTION_ID=<id> bash infra/scripts/quota_check_params.sh [--regions <region>]`
3. The helper honors the pre-set `AZURE_SUBSCRIPTION_ID` env var and skips its interactive subscription picker.
4. The helper queries `az cognitiveservices usage list` for each (model, region) pair and prints the table directly to the console.

**Fix:** Request a quota increase at https://aka.ms/oai/stuquotarequest, or switch to a region with available headroom:
```bash
azd env set AZURE_ENV_OPENAI_LOCATION '<region_with_available_quota>'
```

**Script references:**
- Bash: `check_model_quota()` in `scripts/precheck.sh` → delegates to `infra/scripts/quota_check_params.sh`
- PowerShell: `Test-ModelQuota` in `scripts/precheck.ps1` → delegates to `infra/scripts/quota_check_params.ps1`

---

## Troubleshooting

### The precheck reports an error but I believe the check is wrong

The precheck is a standalone diagnostic and is **not** part of `azd up`. If you disagree with a finding, you can simply skip running the script and invoke `azd up` directly. Please also open an issue describing the false positive so the check can be tightened.

### Precheck passes but deployment still fails

The prechecks cover the most common failure points but cannot catch every possible issue. If deployment fails after prechecks pass, check:
- Azure policy restrictions on your subscription (`RequestDisallowedByPolicy`)
- Soft-deleted Cognitive Services / Key Vault resources colliding with new names (`FlagMustBeSetForRestore`)
- Container Apps regional environment caps (`MaxNumberOfRegionalEnvironmentsInSubExceeded`)
- Network/firewall restrictions blocking ACR or `*.openai.azure.com`
- Restricted-model access requirements for `gpt-5`, `o3`, `o3-pro`, etc. (`SpecialFeatureOrQuotaIdRequired`)

See [TroubleShootingSteps.md](./TroubleShootingSteps.md) for the full error-code reference.

### Updating allowed regions

If the allowed regions change in `infra/main.bicep`, update the corresponding arrays in both scripts:

- **Bash** (`scripts/precheck.sh`): `ALLOWED_LOCATIONS` and `ALLOWED_AI_LOCATIONS` arrays near the top
- **PowerShell** (`scripts/precheck.ps1`): `$AllowedLocations` and `$AllowedAILocations` arrays near the top

The default region list inside `infra/scripts/quota_check_params.{ps1,sh}` should also be kept in sync with `ALLOWED_AI_LOCATIONS`.

### Updating required RBAC roles or resource providers

- **RBAC roles:** edit `RequiredRoles` (PowerShell) / `REQUIRED_ROLES` (bash) near the role-check function.
- **Resource providers:** edit `RequiredProviders` (PowerShell) / `REQUIRED_PROVIDERS` (bash) near the provider-check function.

---

## File Reference

| File | Description |
|------|-------------|
| `scripts/precheck.sh` | Bash precheck script (Linux / macOS / Codespaces) |
| `scripts/precheck.ps1` | PowerShell precheck script (Windows) |
| `infra/scripts/quota_check_params.sh` | Quota helper invoked by the bash precheck (honors `AZURE_SUBSCRIPTION_ID`) |
| `infra/scripts/quota_check_params.ps1` | Quota helper invoked by the PowerShell precheck (honors `AZURE_SUBSCRIPTION_ID`) |
| `azure.yaml` | Main azd config (precheck is **not** wired as a hook here) |
| `azure_custom.yaml` | Custom (WAF / local-build) azd config (precheck is **not** wired as a hook here) |
| `infra/main.bicep` | Source of truth for allowed regions and model parameters |
| `infra/main.parameters.json` | azd environment variable → Bicep parameter mappings |

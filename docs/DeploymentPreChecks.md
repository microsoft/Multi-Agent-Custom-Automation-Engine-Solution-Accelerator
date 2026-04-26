# Deployment Pre-Check Runner — Reference Guide

This document describes the automated deployment pre-checks that run as part of `azd up`. These checks help catch common configuration and environment issues **before** Azure provisioning begins, saving time and avoiding mid-deployment failures.

---

## How It Works

The pre-check runner is registered as a **`preprovision`** hook in both `azure.yaml` and `azure_custom.yaml`. When a user runs `azd up`, Azure Developer CLI automatically executes the appropriate script before provisioning starts:

| Platform | Script | Shell |
|----------|--------|-------|
| Windows (PowerShell) | [`scripts/precheck.ps1`](../scripts/precheck.ps1) | `pwsh` |
| Linux / macOS / Codespaces | [`scripts/precheck.sh`](../scripts/precheck.sh) | `bash` |

> **Note:** These scripts are located in the top-level `scripts/` directory, completely separate from the existing `infra/scripts/` infrastructure code.

### Exit Behavior

| Exit Code | Meaning |
|-----------|---------|
| `0` | All pre-checks passed — provisioning proceeds |
| `1` | One or more critical checks failed — provisioning is blocked |

When checks fail, the scripts collect **all** errors and display them as a numbered list at the end with actionable fix instructions.

---

## Pre-Checks Reference

### 1. Environment Detection

| Detail | Description |
|--------|-------------|
| **What it checks** | Identifies the runtime environment: **Local**, **GitHub Codespaces**, or **Dev Container** |
| **Why it matters** | Some checks are adjusted per environment (e.g., Docker is managed in Codespaces/Dev Containers) |
| **Severity** | Informational only — never blocks deployment |

**How detection works:**

| Environment | Detection Signal |
|-------------|-----------------|
| GitHub Codespaces | `CODESPACES` or `CLOUDENV_ENVIRONMENT_ID` environment variables are set |
| Dev Container | `REMOTE_CONTAINERS` or `DEVCONTAINER` env vars, or `/.dockerenv` file exists |
| Local | Default if neither of the above |

**Script references:**
- Bash: `detect_environment()` function in `scripts/precheck.sh`
- PowerShell: `Test-Environment` function in `scripts/precheck.ps1`

---

### 2. Azure Developer CLI (azd)

| Detail | Description |
|--------|-------------|
| **What it checks** | `azd` is installed and version is **≥ 1.18.0** |
| **Why it matters** | The project's `azure.yaml` declares `requiredVersions.azd: '>= 1.18.0 != 1.23.9'` |
| **Severity** | 🔴 **Critical** — blocks deployment if missing or outdated |
| **Fix** | Install or update: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd |

**Script references:**
- Bash: `check_azd()` function in `scripts/precheck.sh`
- PowerShell: `Test-Azd` function in `scripts/precheck.ps1`

---

### 3. Azure CLI (az)

| Detail | Description |
|--------|-------------|
| **What it checks** | `az` CLI is installed **and** the user is logged in (`az account show` succeeds) |
| **Why it matters** | Required for provisioning Azure resources, quota checks, and role assignments |
| **Severity** | 🔴 **Critical** — blocks deployment if not installed or not logged in |
| **Fix (not installed)** | Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |
| **Fix (not logged in)** | Run `az login` |

**Script references:**
- Bash: `check_azure_cli()` function in `scripts/precheck.sh`
- PowerShell: `Test-AzureCLI` function in `scripts/precheck.ps1`

---

### 4. Bicep CLI

| Detail | Description |
|--------|-------------|
| **What it checks** | Bicep version is **≥ 0.33.0** (auto-installs via `az bicep install` if not found) |
| **Why it matters** | The project's `azure.yaml` declares `requiredVersions.bicep: '>= 0.33.0'` |
| **Severity** | 🔴 **Critical** — blocks deployment if version is too old and auto-install fails |
| **Fix** | Run `az bicep upgrade` or `az bicep install` |

**Script references:**
- Bash: `check_bicep()` function in `scripts/precheck.sh`
- PowerShell: `Test-Bicep` function in `scripts/precheck.ps1`

---

### 5. Python

| Detail | Description |
|--------|-------------|
| **What it checks** | `python3` or `python` is available, plus `pip`/`pip3` |
| **Why it matters** | Backend and MCP services are Python-based; frontend packaging uses `pip install -r requirements.txt` |
| **Severity** | 🔴 **Critical** (python) / 🟡 **Warning** (pip) |
| **Fix** | Install Python 3.x: https://www.python.org/downloads/ |

**Script references:**
- Bash: `check_python()` function in `scripts/precheck.sh`
- PowerShell: `Test-Python` function in `scripts/precheck.ps1`

---

### 6. Node.js & npm

| Detail | Description |
|--------|-------------|
| **What it checks** | `node` and `npm` are installed |
| **Why it matters** | Required by the frontend `prepackage` hook (`npm install && npm run build`) |
| **Severity** | 🔴 **Critical** — blocks deployment |
| **Fix** | Install Node.js (includes npm): https://nodejs.org/ |

**Script references:**
- Bash: `check_node()` function in `scripts/precheck.sh`
- PowerShell: `Test-Node` function in `scripts/precheck.ps1`

---

### 7. jq (JSON Processor) — Bash Only

| Detail | Description |
|--------|-------------|
| **What it checks** | `jq` is installed |
| **Why it matters** | Used by existing quota validation scripts (`infra/scripts/validate_model_quota.sh`, `infra/scripts/validate_model_deployment_quota.sh`) to parse JSON |
| **Severity** | 🔴 **Critical** (bash environments) |
| **Fix** | Install: https://jqlang.github.io/jq/download/ |

> **Note:** PowerShell scripts use `ConvertFrom-Json` natively, so `jq` is not required on Windows.

**Script references:**
- Bash: `check_jq()` function in `scripts/precheck.sh`
- PowerShell: Not applicable

---

### 8. Docker

| Detail | Description |
|--------|-------------|
| **What it checks** | Docker is installed and the daemon is running |
| **Why it matters** | May be needed for container image builds |
| **Severity** | 🟡 **Warning** — does not block deployment |
| **Special behavior** | In **Codespaces** and **Dev Containers**, Docker is managed automatically — the check is relaxed |
| **Fix** | Install Docker Desktop: https://www.docker.com/products/docker-desktop/ |

**Script references:**
- Bash: `check_docker()` function in `scripts/precheck.sh`
- PowerShell: `Test-Docker` function in `scripts/precheck.ps1`

---

### 9. Azure Subscription Validation

| Detail | Description |
|--------|-------------|
| **What it checks** | Active Azure subscription exists with state = **Enabled** |
| **Why it matters** | A disabled or expired subscription will cause all resource provisioning to fail |
| **Severity** | 🔴 **Critical** — blocks deployment |
| **Fix** | Ensure your subscription is active in the [Azure Portal](https://portal.azure.com/#blade/Microsoft_Azure_Billing/SubscriptionsBlade) |

**Script references:**
- Bash: `check_azure_subscription()` function in `scripts/precheck.sh`
- PowerShell: `Test-AzureSubscription` function in `scripts/precheck.ps1`

---

### 10. azd Environment Variables

| Detail | Description |
|--------|-------------|
| **What it checks** | Key azd environment variables are set to valid values |
| **Why it matters** | Invalid regions or deployment types cause Bicep parameter validation failures during provisioning |
| **Severity** | 🔴 **Critical** (if set to invalid value) / ℹ️ **Info** (if not set — will be prompted) |

#### Variables Validated

| Variable | Valid Values | Fix Command |
|----------|-------------|-------------|
| `AZURE_LOCATION` | `australiaeast`, `centralus`, `eastasia`, `eastus2`, `japaneast`, `northeurope`, `southeastasia`, `uksouth` | `azd env set AZURE_LOCATION '<region>'` |
| `AZURE_ENV_OPENAI_LOCATION` | `australiaeast`, `eastus2`, `francecentral`, `japaneast`, `norwayeast`, `swedencentral`, `uksouth`, `westus` | `azd env set AZURE_ENV_OPENAI_LOCATION '<region>'` |
| `AZURE_ENV_MODEL_DEPLOYMENT_TYPE` | `Standard`, `GlobalStandard` | `azd env set AZURE_ENV_MODEL_DEPLOYMENT_TYPE 'GlobalStandard'` |
| `AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE` | `Standard`, `GlobalStandard` | `azd env set AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE 'GlobalStandard'` |
| `AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE` | `Standard`, `GlobalStandard` | `azd env set AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE 'GlobalStandard'` |

> **Note:** The allowed region lists come from `infra/main.bicep` parameter constraints. If these change in the Bicep file, the precheck scripts should be updated to match.

**Script references:**
- Bash: `check_azd_env()` function in `scripts/precheck.sh`
- PowerShell: `Test-AzdEnvironment` function in `scripts/precheck.ps1`

---

### 11. Deployment Hook Scripts

| Detail | Description |
|--------|-------------|
| **What it checks** | All scripts referenced by deployment hooks (prepackage, postdeploy) exist on disk |
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

**Script references:**
- Bash: `check_hook_scripts()` function in `scripts/precheck.sh`
- PowerShell: `Test-HookScripts` function in `scripts/precheck.ps1`

---

### 12. Azure OpenAI Model Quota

| Detail | Description |
|--------|-------------|
| **What it checks** | Sufficient Azure OpenAI token quota is available in the configured AI service region |
| **Why it matters** | Insufficient quota causes model deployment failures during provisioning |
| **Severity** | 🔴 **Critical** — blocks deployment if quota is insufficient |
| **Prerequisites** | Runs only if: Azure CLI is logged in, `jq` is available (bash), and `AZURE_ENV_OPENAI_LOCATION` is set |

#### Default Models Checked

| Model | Required Capacity | Deployment Type |
|-------|------------------|-----------------|
| `gpt-4.1` | 150 | GlobalStandard |
| `gpt-4.1-mini` | 50 | GlobalStandard |
| `o4-mini` | 50 | GlobalStandard |

**How it works:** Queries `az cognitiveservices usage list` for each model in the configured region and compares available capacity against the required amount.

**Fix:** Request a quota increase at https://aka.ms/oai/stuquotarequest or switch to a different region:
```bash
azd env set AZURE_ENV_OPENAI_LOCATION '<region_with_available_quota>'
```

**Script references:**
- Bash: `check_model_quota()` function in `scripts/precheck.sh`
- PowerShell: `Test-ModelQuota` function in `scripts/precheck.ps1`

---

## Troubleshooting

### The precheck blocks my deployment but I believe the check is wrong

The preprovision hook is configured with `continueOnError: false`. If you need to bypass the prechecks temporarily:

```bash
# Run provisioning directly, skipping hooks
azd provision --no-prompt
```

### Precheck passes but deployment still fails

The prechecks cover the most common failure points but cannot catch every possible issue. If deployment fails after prechecks pass, check:
- Azure resource provider registrations (`Microsoft.CognitiveServices`, `Microsoft.ContainerRegistry`, etc.)
- Azure policy restrictions on your subscription
- Network/firewall restrictions

### How to run the precheck manually

You can run the precheck outside of `azd up` for debugging:

```bash
# Bash / Linux / macOS / Codespaces
bash scripts/precheck.sh

# PowerShell / Windows
pwsh scripts/precheck.ps1
```

### Updating allowed regions

If the allowed regions change in `infra/main.bicep`, update the corresponding arrays in both scripts:

- **Bash** (`scripts/precheck.sh`): `ALLOWED_LOCATIONS` and `ALLOWED_AI_LOCATIONS` arrays near the top
- **PowerShell** (`scripts/precheck.ps1`): `$AllowedLocations` and `$AllowedAILocations` arrays near the top

---

## File Reference

| File | Description |
|------|-------------|
| `scripts/precheck.sh` | Bash precheck script (Linux/macOS/Codespaces) |
| `scripts/precheck.ps1` | PowerShell precheck script (Windows) |
| `azure.yaml` | Main azd config — contains `preprovision` hook |
| `azure_custom.yaml` | Custom azd config — contains `preprovision` hook |
| `infra/main.bicep` | Source of truth for allowed regions and model parameters |
| `infra/main.parameters.json` | azd environment variable to Bicep parameter mappings |

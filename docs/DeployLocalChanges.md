# Deploy Local Changes to Azure

Two scripts — one for each platform — that build only the Docker images you changed, push them to ACR, and update the live Azure resources.

| Platform | Script |
|---|---|
| Linux / macOS / WSL | `deploy_to_azure.sh` |
| Windows PowerShell | `deploy_to_azure.ps1` |

---

## Prerequisites

| Tool | Purpose |
|---|---|
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | Manage Azure resources |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Build and push images |
| Git | Detect which services changed |

You must be logged in before running:
```bash
az login
```

---

## What It Does (in order)

1. **Checks prerequisites** — Docker, Azure CLI, Git
2. **Discovers Azure resources** — finds the backend/MCP Container Apps and frontend App Service in your resource group
3. **Resolves ACR** — lists ACRs in the resource group and asks which one to use; prompts to create a new one if needed
4. **Detects changed services** — uses `git diff` to find which of `src/backend/`, `src/mcp_server/`, `src/App/` have changed; only those services are built and deployed
5. **Generates an image tag** — auto-generates `YYYYMMDD-HHMMSS-<git-sha>` or uses your custom tag
6. **Builds & pushes images** — `docker build` + `docker push` to ACR for each changed service
7. **Updates Azure resources** — updates the Container App / App Service to the new image tag
8. **Prints a summary** with rollback commands

---

## Quick Start

```bash
# bash (Linux/macOS/WSL)
bash deploy_to_azure.sh -g <resource-group>

# PowerShell (Windows)
.\deploy_to_azure.ps1 -ResourceGroup <resource-group>
```

The script will:
- Auto-detect which services you changed via git
- Ask which ACR to use (or offer to create one)
- Ask for confirmation before deploying if no changes are detected

---

## All Options

### Bash

```bash
./deploy_to_azure.sh -g <resource-group> [options]

Required:
  -g, --resource-group <name>   Azure Resource Group name

Options:
  --acr <name>                  Skip the ACR prompt; use this ACR directly
  --services <list>             Skip change detection; deploy only these services
                                  Values: backend, mcp, frontend (comma-separated)
  --tag <tag>                   Use a custom image tag instead of auto-generated
  --dry-run                     Preview all steps without making any changes
  --build-only                  Build and push images, but don't update Azure
  --deploy-only                 Update Azure resources only (images must exist)
  --skip-role-assignment        Skip AcrPull role assignment (use if roles already exist)
  -h, --help                    Show help
```

### PowerShell

```powershell
.\deploy_to_azure.ps1 -ResourceGroup <name> [options]

Required:
  -ResourceGroup <name>         Azure Resource Group name

Options:
  -Acr <name>                   Skip the ACR prompt; use this ACR directly
  -Services <list>              Skip change detection; deploy only these services
                                  Values: "backend,mcp,frontend"
  -Tag <tag>                    Use a custom image tag instead of auto-generated
  -DryRun                       Preview all steps without making any changes
  -BuildOnly                    Build and push images, but don't update Azure
  -DeployOnly                   Update Azure resources only (images must exist)
  -SkipRoleAssignment           Skip AcrPull role assignment (use if roles already exist)
```

---

## Examples

```bash
# Deploy only what changed (auto-detected)
bash deploy_to_azure.sh -g rg-macae-dev

# Deploy only the frontend
bash deploy_to_azure.sh -g rg-macae-dev --services frontend

# Deploy backend and MCP with a specific ACR
bash deploy_to_azure.sh -g rg-macae-dev --services backend,mcp --acr myregistry

# Preview without making changes
bash deploy_to_azure.sh -g rg-macae-dev --dry-run

# Build images only (no Azure update)
bash deploy_to_azure.sh -g rg-macae-dev --build-only

# Update Azure only (images already pushed)
bash deploy_to_azure.sh -g rg-macae-dev --deploy-only --tag 20260506-120000-abc1234

# Skip AcrPull role assignment (roles already exist)
bash deploy_to_azure.sh -g rg-macae-dev --skip-role-assignment
```

```powershell
# Deploy only what changed
.\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev

# Deploy only backend
.\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev -Services "backend"

# Dry run
.\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev -DryRun

# Skip AcrPull role assignment (roles already exist)
.\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev -SkipRoleAssignment
```

---

## Change Detection Logic

When `--services` is not specified, the script runs `git diff` to determine what to build:

| Files changed in | Service built |
|---|---|
| `src/backend/` | backend |
| `src/mcp_server/` | mcp |
| `src/App/` | frontend |

It checks only **uncommitted changes** (staged and unstaged vs the last commit, i.e. `git diff HEAD`). Commits that are already committed but not yet pushed are intentionally excluded to avoid false positives from unrelated branch work.

If no changes are detected in any service directory, the script asks:
```
No changes detected. Deploy all services anyway? [y/N]:
```

---

## ACR Selection

If `--acr` / `-Acr` is not provided, the script **always prompts first**:

```
Enter ACR name to use (or press Enter to see available ACRs / create new):
```

- **Type a name** → validates and uses that ACR directly
- **Press Enter** → discovers ACRs in the resource group:
  - If one or more ACRs are found, the first one is selected automatically
  - If none are found, a new Basic ACR is created in the same resource group

In all cases, `AcrPull` is assigned to the managed identities of each service.

---

## How Azure Authentication Works

The scripts use **managed identity** (not admin credentials or passwords):

- Each Container App and App Service has a user-assigned managed identity
- The script assigns the `AcrPull` role to those identities on the ACR
- `az containerapp registry set --identity <id>` wires the identity to the registry config

This means no passwords are stored anywhere.

If the role assignment step fails (e.g. your account lacks `Microsoft.Authorization/roleAssignments/write`), ask a subscription Owner to grant `User Access Administrator` on the resource group. Once roles are already in place you can skip this step on subsequent runs with `--skip-role-assignment` / `-SkipRoleAssignment`.

---

## Rollback

At the end of each run, the summary prints ready-to-run rollback commands, e.g.:

```bash
az containerapp update --name ca-macae --resource-group rg-macae-dev --image myacr.azurecr.io/macaebackend:20260505-120000-abc1234
```

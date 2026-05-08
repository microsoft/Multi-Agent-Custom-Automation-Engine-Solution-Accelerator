# Automated Local Development Setup

Two scripts — one for each platform — that automate the entire local development setup: Azure authentication, `.env` generation, Python/Node dependency installation, RBAC role assignment, and VS Code configuration.

| Platform | Script |
|---|---|
| Linux / macOS / WSL / Git Bash | `setup_local_dev.sh` |
| Windows PowerShell | `setup_local_dev.ps1` |

---

## Prerequisites

| Tool | Purpose |
|---|---|
| [Python 3.12+](https://www.python.org/downloads/) | Backend and frontend virtual environments |
| [Node.js 18+](https://nodejs.org/) | Frontend build |
| [uv](https://github.com/astral-sh/uv) | Fast Python package management (backend & MCP) |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | Fetch Azure config and assign RBAC roles |
| [Git](https://git-scm.com/) | Source control |

You must be logged in before running (the script will prompt if you are not):

```bash
az login
```

---

## What It Does (in order)

1. **Checks prerequisites** — Python 3.12+, Node.js, npm, uv, Azure CLI, Git
2. **Azure authentication** — logs you in if needed, confirms the active subscription
3. **Fetches Azure configuration** — reads deployment outputs or queries resources individually to build `src/backend/.env`
4. **Assigns RBAC roles** — grants your user account the roles needed to run the app locally:
   - Cosmos DB Built-in Data Contributor
   - Azure AI User, Azure AI Developer, Cognitive Services OpenAI User
   - Search Index Data Contributor
   - Storage Blob Data Contributor
5. **Sets up Backend** (`src/backend`) — creates a `.venv` with `uv`, installs all dependencies
6. **Sets up MCP Server** (`src/mcp_server`) — same as backend
7. **Sets up Frontend** (`src/App`) — creates a `.venv`, installs Python deps, runs `npm install` and `npm run build`
8. **Configures VS Code** — writes `.vscode/extensions.json` and `settings.json` (skip with `--skip-vscode`)
9. **Prints a start summary** with the exact commands to run each service

---

## Quick Start

```bash
# bash (Linux / macOS / WSL / Git Bash)
bash setup_local_dev.sh --resource-group <resource-group>

# PowerShell (Windows)
.\setup_local_dev.ps1 -ResourceGroup <resource-group>
```

The script will:
- Fetch all Azure settings and write `src/backend/.env` automatically
- Create Python virtual environments and install all dependencies
- Assign your account the required Azure roles

---

## All Options

### Bash

```bash
bash setup_local_dev.sh [options]

Options:
  --resource-group, -g <name>   Azure Resource Group (auto-detected from .azure/ if omitted)
  --subscription, -s <id>       Azure Subscription ID (uses current az account if omitted)
  --assign-rbac                 Assign Azure RBAC roles to your user account
  --skip-vscode                 Skip writing .vscode/ settings files
  --skip-prereqs                Skip prerequisite checks
  -h, --help                    Show help
```

### PowerShell

```powershell
.\setup_local_dev.ps1 [options]

Options:
  -ResourceGroup <name>         Azure Resource Group (auto-detected from .azure/ if omitted)
  -Subscription <id>            Azure Subscription ID (uses current az account if omitted)
  -AssignRbac                   Assign Azure RBAC roles to your user account
  -SkipVSCode                   Skip writing .vscode/ settings files
  -SkipPrereqs                  Skip prerequisite checks
```

---

## Examples

```bash
# Fetch config from Azure and set up everything
bash setup_local_dev.sh --resource-group rg-macae-dev

# Also assign RBAC roles (required on first setup)
bash setup_local_dev.sh --resource-group rg-macae-dev --assign-rbac

# Use a specific subscription
bash setup_local_dev.sh --resource-group rg-macae-dev --subscription 00000000-0000-0000-0000-000000000000

# Skip VS Code settings (e.g. using a different editor)
bash setup_local_dev.sh --resource-group rg-macae-dev --skip-vscode

# Skip prerequisite checks (useful in CI or if tools are on a non-standard PATH)
bash setup_local_dev.sh --resource-group rg-macae-dev --skip-prereqs
```

```powershell
# Fetch config from Azure and set up everything
.\setup_local_dev.ps1 -ResourceGroup rg-macae-dev

# Also assign RBAC roles (required on first setup)
.\setup_local_dev.ps1 -ResourceGroup rg-macae-dev -AssignRbac

# Use a specific subscription
.\setup_local_dev.ps1 -ResourceGroup rg-macae-dev -Subscription 00000000-0000-0000-0000-000000000000

# Skip VS Code settings
.\setup_local_dev.ps1 -ResourceGroup rg-macae-dev -SkipVSCode
```

---

## Auto-Detection (no `--resource-group`)

If you ran `azd up` to deploy, the scripts will automatically find the `.azure/<env>/.env` file and use it — no flags needed:

```bash
bash setup_local_dev.sh        # reads .azure/<env>/.env written by azd up
.\setup_local_dev.ps1          # same
```

If no `.azure/` folder exists and no `--resource-group` is provided, the script will prompt you to enter the resource group name interactively.

---

## RBAC Roles Assigned

The `--assign-rbac` / `-AssignRbac` flag grants your user account the following roles:

| Role | Resource | Purpose |
|---|---|---|
| Cosmos DB Built-in Data Contributor | Cosmos DB account | Read/write conversation history |
| Azure AI User | AI Foundry project | Call AI Foundry APIs |
| Azure AI Developer | AI Foundry project | Deploy and manage agents |
| Cognitive Services OpenAI User | AI Foundry project | Call OpenAI endpoints |
| Search Index Data Contributor | Azure AI Search | Read/write search indexes |
| Storage Blob Data Contributor | Storage account | Read/write blob storage |

> **Note:** RBAC changes can take 5–10 minutes to propagate before the app can use them.

---

## After Setup

Once the script finishes, start the three services in separate terminals:

```bash
# Terminal 1 — Backend (port 8000)
cd src/backend
source .venv/Scripts/activate   # Windows Git Bash
# source .venv/bin/activate     # Linux / macOS
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — MCP Server (port 9000)
cd src/mcp_server
source .venv/Scripts/activate
python mcp_server.py

# Terminal 3 — Frontend (port 3000)
cd src/App
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `az login` loop | CLI not installed or PATH issue | Install [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| `.env` values empty | RG has no deployment outputs | Pass `--resource-group` explicitly |
| `uv: command not found` | uv not installed | `pip install uv` or see [uv docs](https://github.com/astral-sh/uv) |
| RBAC errors at runtime | Roles not assigned | Re-run with `--assign-rbac`; wait 10 min |
| `source .venv/Scripts/activate: No such file` | Incomplete venv | Delete `.venv/` folder and re-run the script |
| Frontend npm errors | Node.js version too old | Upgrade to Node.js 18+ |

For more detail, see [TroubleShootingSteps.md](TroubleShootingSteps.md).

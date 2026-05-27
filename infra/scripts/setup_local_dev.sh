#!/usr/bin/env bash
# ==============================================================================
# MACAE - Local Development Setup Script (Linux / macOS / WSL / Git Bash)
# ==============================================================================
# Automates the entire local development setup for the Multi-Agent Custom
# Automation Engine Solution Accelerator.
#
# Usage:
#   bash setup_local_dev.sh [--resource-group <name>] [--subscription <id>] \
#                           [--skip-vscode] [--skip-prereqs]
#
# Examples:
#   bash setup_local_dev.sh                                        # auto-detects from .azure/
#   bash setup_local_dev.sh --resource-group "rg-macae-dev"        # fetch from Azure outputs
#   bash setup_local_dev.sh --resource-group "rg-macae-dev" --skip-prereqs
# ==============================================================================

set -euo pipefail

# ==============================================================================
# Paths
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$REPO_ROOT/src/backend"
MCP_DIR="$REPO_ROOT/src/mcp_server"
FRONTEND_DIR="$REPO_ROOT/src/App"

# ==============================================================================
# Flags (set by parse_args)
# ==============================================================================

RESOURCE_GROUP=""
SUBSCRIPTION=""
SKIP_VSCODE=false
SKIP_PREREQS=false

# ==============================================================================
# Detect Python command (Windows: python/py  |  Linux/Mac: python3)
# ==============================================================================

PYTHON_CMD=""
for _cmd in python3.12 python3 python py; do
    if command -v "$_cmd" &>/dev/null; then
        _ver=$("$_cmd" --version 2>&1 || true)
        if [[ "$_ver" =~ 3\.(1[2-9]|[2-9][0-9]) ]]; then
            PYTHON_CMD="$_cmd"
            break
        fi
    fi
done
# Fallback: use whatever python3/python is available even if version check failed
if [[ -z "$PYTHON_CMD" ]]; then
    for _cmd in python3 python py; do
        if command -v "$_cmd" &>/dev/null; then
            PYTHON_CMD="$_cmd"
            break
        fi
    done
fi

# ==============================================================================
# Colors
# ==============================================================================

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; DIM='\033[2m'

# ==============================================================================
# Helpers
# ==============================================================================

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    {
    echo -e "\n${CYAN}------------------------------------------------------${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}------------------------------------------------------${NC}\n"
}

command_exists() { command -v "$1" &>/dev/null; }

# Activate a .venv regardless of OS
# Windows/Git Bash creates Scripts/activate; Linux/macOS creates bin/activate
activate_venv() {
    if [[ -f ".venv/Scripts/activate" ]]; then
        source .venv/Scripts/activate
    elif [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
    else
        log_error "Cannot find .venv activate script in $(pwd)"
        exit 1
    fi
}

confirm() {
    local prompt="$1"
    local default="${2:-y}"
    if [[ "$default" == "y" ]]; then
        read -rp "$prompt [Y/n]: " response
        response="${response:-y}"
    else
        read -rp "$prompt [y/N]: " response
        response="${response:-n}"
    fi
    [[ "$response" =~ ^[Yy] ]]
}

# ==============================================================================
# Step 0: Parse arguments
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --resource-group|-g) RESOURCE_GROUP="$2"; shift 2 ;;
            --subscription|-s)   SUBSCRIPTION="$2";   shift 2 ;;
            --skip-vscode)       SKIP_VSCODE=true;     shift ;;
            --skip-prereqs)      SKIP_PREREQS=true;    shift ;;
            -h|--help)
                sed -n '3,20p' "${BASH_SOURCE[0]}"
                exit 0
                ;;
            *)
                log_warn "Unknown argument: $1"
                shift
                ;;
        esac
    done
}

# ==============================================================================
# Step 1: Prerequisites
# ==============================================================================

check_prerequisites() {
    log_step "Step 1: Checking Prerequisites"

    if [[ "$SKIP_PREREQS" == "true" ]]; then
        log_info "Skipping prerequisite checks (--skip-prereqs passed)."
        return
    fi

    local missing=()

    # Python 3.12+
    if [[ -n "$PYTHON_CMD" ]]; then
        log_success "Python found: $("$PYTHON_CMD" --version 2>&1)"
    else
        missing+=("python")
    fi

    # Node.js
    if command_exists node; then
        log_success "Node.js found: $(node --version)"
    else
        missing+=("nodejs")
    fi

    # npm (bundled with Node; only warn separately if Node exists without npm)
    if command_exists node && ! command_exists npm; then
        log_warn "npm not found despite Node.js being installed -- try reinstalling Node.js"
        missing+=("nodejs")
    elif command_exists npm; then
        log_success "npm found: $(npm --version)"
    fi

    # uv
    if command_exists uv; then
        log_success "uv found: $(uv --version)"
    else
        missing+=("uv")
    fi

    # Azure CLI
    if command_exists az; then
        log_success "Azure CLI found"
    else
        missing+=("azure-cli")
    fi

    # Git
    if command_exists git; then
        log_success "Git found: $(git --version)"
    else
        missing+=("git")
    fi

    if [[ ${#missing[@]} -eq 0 ]]; then
        log_success "All prerequisites installed!"
        return
    fi

    log_error "Missing prerequisites: ${missing[*]}"
    echo ""
    log_warn "Please install the following before proceeding:"
    echo ""

    local shown_node=false
    for tool in "${missing[@]}"; do
        case "$tool" in
            python)
                echo "  +-- Python 3.12 -----------------------------------------------"
                echo "  |  Download: https://www.python.org/downloads/"
                echo "  |  Linux (Ubuntu/Debian):  sudo apt install python3.12 python3.12-venv"
                echo "  |  macOS (Homebrew):        brew install python@3.12"
                echo "  |  Windows (winget):        winget install Python.Python.3.12"
                echo "  |  Verify: python3.12 --version  (or python --version)"
                echo "  +--------------------------------------------------------------"
                ;;
            nodejs)
                if [[ "$shown_node" == "false" ]]; then
                    shown_node=true
                    echo "  +-- Node.js & npm ---------------------------------------------"
                    echo "  |  Download: https://nodejs.org/ (LTS version)"
                    echo "  |  Linux (Ubuntu/Debian):  sudo apt install nodejs npm"
                    echo "  |  macOS (Homebrew):        brew install node"
                    echo "  |  Windows (winget):        winget install OpenJS.NodeJS.LTS"
                    echo "  |  Verify: node --version && npm --version"
                    echo "  +--------------------------------------------------------------"
                fi
                ;;
            uv)
                echo "  +-- uv (Python package manager) ------------------------------"
                echo "  |  Linux/macOS:  curl -LsSf https://astral.sh/uv/install.sh | sh"
                echo "  |  Windows:      winget install astral-sh.uv"
                echo "  |  pip fallback: pip install uv"
                echo "  |  Docs: https://docs.astral.sh/uv/getting-started/installation/"
                echo "  |  Verify: uv --version"
                echo "  |  Note: Restart your terminal after install."
                echo "  +--------------------------------------------------------------"
                ;;
            azure-cli)
                echo "  +-- Azure CLI -------------------------------------------------"
                echo "  |  Linux (Ubuntu/Debian):  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
                echo "  |  macOS (Homebrew):        brew install azure-cli"
                echo "  |  Windows (winget):        winget install Microsoft.AzureCLI"
                echo "  |  Docs: https://learn.microsoft.com/cli/azure/install-azure-cli"
                echo "  |  Verify: az --version && az login"
                echo "  +--------------------------------------------------------------"
                ;;
            git)
                echo "  +-- Git -------------------------------------------------------"
                echo "  |  Linux (Ubuntu/Debian):  sudo apt install git"
                echo "  |  macOS (Homebrew):        brew install git"
                echo "  |  Windows (winget):        winget install Git.Git"
                echo "  |  Verify: git --version"
                echo "  +--------------------------------------------------------------"
                ;;
        esac
    done

    echo ""
    echo "  For detailed instructions, see:"
    echo "  https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/blob/main/docs/LocalDevelopmentSetup.md"
    echo ""
    log_info "After installing, restart your terminal and re-run this script."
    exit 1
}

# ==============================================================================
# Step 2: Azure Authentication
# ==============================================================================

check_azure_auth() {
    log_step "Step 2: Azure Authentication"

    local account_info
    account_info=$(az account show --output json 2>/dev/null || true)

    if [[ -z "$account_info" ]]; then
        log_warn "Not logged into Azure CLI"
        log_info "Running 'az login'..."
        az login
        account_info=$(az account show --output json)
    fi

    if [[ -n "$SUBSCRIPTION" ]]; then
        log_info "Setting subscription to: $SUBSCRIPTION"
        az account set --subscription "$SUBSCRIPTION"
        account_info=$(az account show --output json)
    fi

    SUBSCRIPTION=$(echo "$account_info" | "$PYTHON_CMD" -c "import sys,json; d=json.load(sys.stdin); print(d['id'])")
    local sub_name
    sub_name=$(echo "$account_info" | "$PYTHON_CMD" -c "import sys,json; d=json.load(sys.stdin); print(d['name'])")

    log_success "Logged in to Azure"
    log_info "  Subscription: $sub_name ($SUBSCRIPTION)"

    read -rp "Is this the correct subscription? [Y/n]: " response
    response="${response:-y}"
    if [[ "$response" =~ ^[Nn] ]]; then
        az account list --output table --query "[].{Name:name, Id:id, State:state}"
        read -rp "Enter subscription ID: " SUBSCRIPTION
        az account set --subscription "$SUBSCRIPTION"
    fi
}

# ==============================================================================
# Step 2b: Azure Role / Permission Check
# ==============================================================================
#
# This script assigns data-plane roles (Cosmos DB, AI services, AI Search,
# Storage Blob) to the signed-in user. That requires the user to have
# permission to write role assignments at subscription scope:
#   - User Access Administrator OR Role Based Access Control Administrator
#     (or Owner)
# Non-fatal warning: group-inherited roles may not always enumerate.
# ==============================================================================

check_azure_roles() {
    log_step "Step 2b: Checking Azure Roles & Permissions"

    local sub_id user_id
    sub_id=$(az account show --query id -o tsv 2>/dev/null || true)
    user_id=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)
    if [[ -z "$sub_id" || -z "$user_id" ]]; then
        log_warn "Could not determine subscription or user identity -- skipping role check."
        return
    fi

    local scope="/subscriptions/$sub_id"
    local roles_raw
    roles_raw=$(az role assignment list --assignee "$user_id" --scope "$scope" \
        --include-inherited --include-groups --query "[].roleDefinitionName" -o tsv 2>/dev/null || true)
    if [[ -z "$roles_raw" ]]; then
        log_warn "Unable to enumerate role assignments at $scope."
        log_warn "Required: 'User Access Administrator' OR 'Role Based Access Control Administrator' (or 'Owner') to assign data-plane roles."
        return
    fi

    local has_role_mgmt=false
    while IFS= read -r r; do
        case "$r" in
            Owner|"User Access Administrator"|"Role Based Access Control Administrator") has_role_mgmt=true ;;
        esac
    done <<< "$roles_raw"

    if $has_role_mgmt; then
        log_success "Role-assignment permission found (Owner/UAA/RBAC Admin)"
    else
        log_warn "Missing 'User Access Administrator' / 'Role Based Access Control Administrator' (or 'Owner')."
        log_warn "The Cosmos DB / AI / Search / Storage Blob role assignments performed by this script may fail."
        log_warn "Ask an admin to pre-assign those roles, or grant the missing role on the subscription."
    fi
}

# ==============================================================================
# Step 3: Fetch Configuration
# ==============================================================================

fetch_configuration() {
    log_step "Step 3: Fetching Azure Configuration"

    # PATH 1: Resource group explicitly provided
    if [[ -n "$RESOURCE_GROUP" ]]; then
        log_info "Resource group provided. Fetching config from Azure deployment outputs..."
        fetch_from_resource_group
        return
    fi

    # PATH 2: Look for .azure/<env>/.env written by 'azd up'
    log_info "No --resource-group provided. Looking for existing config in .azure/ folder..."

    local azd_dir="$REPO_ROOT/.azure"
    local azd_env_file=""
    local detected_env_name=""

    # Try config.json defaultEnvironment first
    local config_json="$azd_dir/config.json"
    if [[ -f "$config_json" ]]; then
        local default_env
        default_env=$("$PYTHON_CMD" -c "
import json
try:
    d = json.load(open('$config_json'))
    print(d.get('defaultEnvironment',''))
except:
    print('')
" 2>/dev/null || true)
        if [[ -n "$default_env" && -f "$azd_dir/$default_env/.env" ]]; then
            azd_env_file="$azd_dir/$default_env/.env"
            detected_env_name="$default_env"
        fi
    fi

    # Fallback: most recently modified .env
    if [[ -z "$azd_env_file" && -d "$azd_dir" ]]; then
        local latest_env
        latest_env=$(find "$azd_dir" -name ".env" -maxdepth 3 2>/dev/null \
                     | xargs ls -t 2>/dev/null | head -1 || true)
        if [[ -n "$latest_env" && -f "$latest_env" ]]; then
            azd_env_file="$latest_env"
            detected_env_name=$(basename "$(dirname "$latest_env")")
        fi
    fi

    if [[ -n "$azd_env_file" ]]; then
        log_success "Found deployment config '$detected_env_name': $azd_env_file"
        local raw_values
        raw_values=$(cat "$azd_env_file")

        # Extract resource group so RBAC step works
        local rg_line
        rg_line=$(echo "$raw_values" | grep -E '^AZURE_RESOURCE_GROUP=' | head -1 || true)
        if [[ -n "$rg_line" ]]; then
            RESOURCE_GROUP="${rg_line#*=}"
            RESOURCE_GROUP="${RESOURCE_GROUP//\"/}"
            RESOURCE_GROUP="${RESOURCE_GROUP//\'/}"
            RESOURCE_GROUP="${RESOURCE_GROUP//$'\r'/}"
            log_info "  Resource Group: $RESOURCE_GROUP"
        fi

        generate_env_file "$raw_values"
        return
    fi

    # PATH 3: No .env found — prompt for RG
    echo ""
    log_warn "No .azure/ config found and no --resource-group provided."
    log_info "Please enter your Azure Resource Group name (created during deployment):"
    read -rp "Resource Group name: " RESOURCE_GROUP
    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_error "Resource group name is required."
        log_info "Usage: bash setup_local_dev.sh --resource-group <name>"
        exit 1
    fi
    fetch_from_resource_group
}

fetch_from_resource_group() {
    log_info "Fetching configuration from Resource Group: $RESOURCE_GROUP"

    if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
        log_error "Resource group '$RESOURCE_GROUP' not found"
        exit 1
    fi

    # Strategy 1: Deployment outputs
    local deployment_name
    deployment_name=$(az group show --name "$RESOURCE_GROUP" \
        --query "tags.DeploymentName" -o tsv 2>/dev/null || true)

    if [[ -n "$deployment_name" ]]; then
        log_info "Found deployment '$deployment_name' -- reading outputs..."
        local outputs_json
        outputs_json=$(az deployment group show \
            --resource-group "$RESOURCE_GROUP" \
            --name "$deployment_name" \
            --query "properties.outputs" -o json 2>/dev/null || true)

        if [[ -n "$outputs_json" && "$outputs_json" != "null" ]]; then
            local lines
            lines=$(echo "$outputs_json" | "$PYTHON_CMD" -c "
import json, sys
outputs = json.load(sys.stdin)
for k, v in outputs.items():
    val = v.get('value', '')
    if val:
        print(f'{k.upper()}={val}')
" 2>/dev/null || true)
            if [[ -n "$lines" ]]; then
                local count
                count=$(echo "$lines" | grep -c . || true)
                log_success "Read $count values from deployment outputs."
                generate_env_file "$lines"
                return
            fi
        fi
        log_warn "Deployment outputs empty -- falling back to resource queries."
    else
        log_info "No DeploymentName tag -- querying resources directly."
    fi

    # Strategy 2: Query each resource individually
    log_info "Querying Azure resources..."
    local sub_id tenant_id
    sub_id=$(az account show --query id -o tsv)
    tenant_id=$(az account show --query tenantId -o tsv)

    local cosmos_name ai_services_name ai_project_name search_name storage_name
    local app_insights_key app_insights_conn

    cosmos_name=$(az cosmosdb list --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv 2>/dev/null || true)
    [[ -n "$cosmos_name" ]] && log_success "  CosmosDB        : $cosmos_name" \
                             || log_warn    "  CosmosDB        : not found"

    ai_services_name=$(az cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIServices' || kind=='CognitiveServices'].name | [0]" \
        -o tsv 2>/dev/null || true)
    [[ -n "$ai_services_name" ]] && log_success "  AI Services     : $ai_services_name" \
                                  || log_warn    "  AI Services     : not found"

    ai_project_name=$(az cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIProject'].name | [0]" -o tsv 2>/dev/null || true)
    [[ -n "$ai_project_name" ]] && log_success "  AI Project      : $ai_project_name" \
                                 || log_warn    "  AI Project      : not found (manual config needed)"

    search_name=$(az search service list --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv 2>/dev/null || true)
    [[ -n "$search_name" ]] && log_success "  Search Service  : $search_name" \
                             || log_warn    "  Search Service  : not found"

    app_insights_key=$(az monitor app-insights component list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].instrumentationKey" -o tsv 2>/dev/null || true)
    app_insights_conn=$(az monitor app-insights component list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].connectionString" -o tsv 2>/dev/null || true)
    [[ -n "$app_insights_key" ]] && log_success "  App Insights    : found" \
                                  || log_warn    "  App Insights    : not found"

    storage_name=$(az storage account list --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv 2>/dev/null || true)
    [[ -n "$storage_name" ]] && log_success "  Storage Account : $storage_name" \
                              || log_warn    "  Storage Account : not found"

    local cosmos_endpoint ai_endpoint search_endpoint storage_url project_endpoint
    cosmos_endpoint="${cosmos_name:+https://$cosmos_name.documents.azure.com:443/}"
    ai_endpoint="${ai_services_name:+https://$ai_services_name.openai.azure.com/}"
    search_endpoint="${search_name:+https://$search_name.search.windows.net}"
    storage_url="${storage_name:+https://$storage_name.blob.core.windows.net/}"
    if [[ -n "$ai_services_name" && -n "$ai_project_name" ]]; then
        project_endpoint="https://$ai_services_name.services.ai.azure.com/api/projects/$ai_project_name"
    else
        project_endpoint=""
    fi

    generate_env_file "COSMOSDB_ENDPOINT=$cosmos_endpoint
COSMOSDB_DATABASE=macae
COSMOSDB_CONTAINER=memory
AZURE_OPENAI_ENDPOINT=$ai_endpoint
AZURE_OPENAI_MODEL_NAME=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_RAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=$app_insights_key
APPLICATIONINSIGHTS_CONNECTION_STRING=$app_insights_conn
AZURE_AI_SUBSCRIPTION_ID=$sub_id
AZURE_AI_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_AI_PROJECT_NAME=$ai_project_name
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_AI_SEARCH_CONNECTION_NAME=macae-search-connection
AZURE_AI_SEARCH_ENDPOINT=$search_endpoint
AZURE_TENANT_ID=$tenant_id
AZURE_STORAGE_BLOB_URL=$storage_url
AZURE_AI_PROJECT_ENDPOINT=$project_endpoint
AZURE_AI_AGENT_ENDPOINT=$project_endpoint
REASONING_MODEL_NAME=o4-mini"
}

generate_env_file() {
    local raw_values="$1"
    local env_file="$BACKEND_DIR/.env"
    log_info "Generating .env file at: $env_file"

    declare -A env_vars
    while IFS= read -r line; do
        line="${line%%$'\r'}"
        [[ -z "$line" || "$line" == \#* ]] && continue
        local key="${line%%=*}"
        local value="${line#*=}"
        value="${value%\"}" ; value="${value#\"}"
        value="${value%\'}" ; value="${value#\'}"
        [[ -n "$key" ]] && env_vars["$key"]="$value"
    done <<< "$raw_values"

    env_vars["APP_ENV"]="dev"
    env_vars["BACKEND_API_URL"]="http://localhost:8000"
    env_vars["FRONTEND_SITE_NAME"]="*"
    env_vars["MCP_SERVER_ENDPOINT"]="http://localhost:9000/mcp"
    env_vars["MCP_SERVER_NAME"]="MacaeMcpServer"
    env_vars["MCP_SERVER_DESCRIPTION"]="MCP server with greeting, HR, and planning tools"

    local ts
    ts=$(date "+%Y-%m-%d %H:%M:%S")

    cat > "$env_file" << ENVEOF
# ===================================================================
# MACAE Local Development Configuration
# Generated by setup_local_dev.sh on $ts
# ===================================================================

# --- Local Development Settings (DO NOT CHANGE) ---
APP_ENV=dev
BACKEND_API_URL=http://localhost:8000
FRONTEND_SITE_NAME=*
MCP_SERVER_ENDPOINT=http://localhost:9000/mcp
MCP_SERVER_NAME=MacaeMcpServer
MCP_SERVER_DESCRIPTION="MCP server with greeting, HR, and planning tools"

# --- Azure Authentication ---
AZURE_TENANT_ID=${env_vars[AZURE_TENANT_ID]:-}
AZURE_CLIENT_ID=${env_vars[AZURE_CLIENT_ID]:-}

# --- CosmosDB ---
COSMOSDB_ENDPOINT=${env_vars[COSMOSDB_ENDPOINT]:-}
COSMOSDB_DATABASE=${env_vars[COSMOSDB_DATABASE]:-macae}
COSMOSDB_CONTAINER=${env_vars[COSMOSDB_CONTAINER]:-memory}

# --- Azure OpenAI ---
AZURE_OPENAI_ENDPOINT=${env_vars[AZURE_OPENAI_ENDPOINT]:-}
AZURE_OPENAI_MODEL_NAME=${env_vars[AZURE_OPENAI_MODEL_NAME]:-gpt-4.1-mini}
AZURE_OPENAI_DEPLOYMENT_NAME=${env_vars[AZURE_OPENAI_DEPLOYMENT_NAME]:-gpt-4.1-mini}
AZURE_OPENAI_RAI_DEPLOYMENT_NAME=${env_vars[AZURE_OPENAI_RAI_DEPLOYMENT_NAME]:-gpt-4.1}
AZURE_OPENAI_API_VERSION=${env_vars[AZURE_OPENAI_API_VERSION]:-2024-12-01-preview}
REASONING_MODEL_NAME=${env_vars[REASONING_MODEL_NAME]:-o4-mini}
SUPPORTED_MODELS=${env_vars[SUPPORTED_MODELS]:-["o3","o4-mini","gpt-4.1","gpt-4.1-mini"]}

# --- Azure AI Foundry ---
AZURE_AI_SUBSCRIPTION_ID=${env_vars[AZURE_AI_SUBSCRIPTION_ID]:-}
AZURE_AI_RESOURCE_GROUP=${env_vars[AZURE_AI_RESOURCE_GROUP]:-}
AZURE_AI_PROJECT_NAME=${env_vars[AZURE_AI_PROJECT_NAME]:-}
AZURE_AI_PROJECT_ENDPOINT=${env_vars[AZURE_AI_PROJECT_ENDPOINT]:-}
AZURE_AI_AGENT_ENDPOINT=${env_vars[AZURE_AI_AGENT_ENDPOINT]:-}
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=${env_vars[AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME]:-gpt-4.1-mini}
AZURE_AI_AGENT_API_VERSION=${env_vars[AZURE_AI_AGENT_API_VERSION]:-2025-05-01-preview}
AZURE_AI_AGENT_PROJECT_CONNECTION_STRING=${env_vars[AZURE_AI_AGENT_PROJECT_CONNECTION_STRING]:-}
AZURE_COGNITIVE_SERVICES=${env_vars[AZURE_COGNITIVE_SERVICES]:-https://cognitiveservices.azure.com/.default}

# --- Azure AI Search ---
AZURE_AI_SEARCH_CONNECTION_NAME=${env_vars[AZURE_AI_SEARCH_CONNECTION_NAME]:-}
AZURE_AI_SEARCH_ENDPOINT=${env_vars[AZURE_AI_SEARCH_ENDPOINT]:-}

# --- Application Insights ---
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=${env_vars[APPLICATIONINSIGHTS_INSTRUMENTATION_KEY]:-}
APPLICATIONINSIGHTS_CONNECTION_STRING=${env_vars[APPLICATIONINSIGHTS_CONNECTION_STRING]:-}

# --- Storage ---
AZURE_STORAGE_BLOB_URL=${env_vars[AZURE_STORAGE_BLOB_URL]:-}

# --- Bing ---
AZURE_BING_CONNECTION_NAME=${env_vars[AZURE_BING_CONNECTION_NAME]:-binggrnd}
BING_CONNECTION_NAME=${env_vars[BING_CONNECTION_NAME]:-binggrnd}

# --- Logging ---
AZURE_BASIC_LOGGING_LEVEL=${env_vars[AZURE_BASIC_LOGGING_LEVEL]:-INFO}
AZURE_PACKAGE_LOGGING_LEVEL=${env_vars[AZURE_PACKAGE_LOGGING_LEVEL]:-WARNING}
AZURE_LOGGING_PACKAGES=${env_vars[AZURE_LOGGING_PACKAGES]:-}
ENVEOF

    log_success ".env file generated successfully"

    local required_keys=("COSMOSDB_ENDPOINT" "AZURE_OPENAI_ENDPOINT" "AZURE_AI_SUBSCRIPTION_ID"
                         "AZURE_AI_RESOURCE_GROUP" "AZURE_AI_PROJECT_NAME" "AZURE_AI_AGENT_ENDPOINT")
    local missing_keys=()
    for key in "${required_keys[@]}"; do
        if [[ -z "${env_vars[$key]:-}" ]]; then
            missing_keys+=("$key")
        fi
    done
    if [[ ${#missing_keys[@]} -gt 0 ]]; then
        log_warn "The following required values are empty (edit .env manually):"
        for k in "${missing_keys[@]}"; do log_warn "  - $k"; done
    fi
}

# ==============================================================================
# Step 4: RBAC
# ==============================================================================

FAILED_ROLE_ASSIGNMENTS=()

# Returns 0 if the named role definition exists in the given subscription.
test_role_definition_exists() {
    local role_name="$1" sub_id="$2"
    local def
    def=$(MSYS_NO_PATHCONV=1 az role definition list --name "$role_name" --subscription "$sub_id" --query "[0].id" -o tsv 2>/dev/null || true)
    [[ -n "$def" ]]
}

# Append a failed assignment record: "Role|Assignee|Scope|Reason"
record_role_failure() {
    FAILED_ROLE_ASSIGNMENTS+=("$1|$2|$3|$4")
}

assign_rbac_roles() {
    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_info "No resource group specified, skipping RBAC assignment."
        return
    fi

    log_step "Step 4: Assigning RBAC Roles"

    # Helper: run az command, strip \r, never fail under set -e
    # MSYS_NO_PATHCONV prevents Git Bash from mangling /subscriptions/... paths
    _az_tsv() {
        local result
        result=$(MSYS_NO_PATHCONV=1 az "$@" 2>/dev/null) || true
        echo "${result//$'\r'/}"
    }

    local oid upn sub_id
    oid=$(_az_tsv ad signed-in-user show --query id -o tsv)
    upn=$(_az_tsv ad signed-in-user show --query userPrincipalName -o tsv)
    if [[ -z "$oid" ]]; then
        log_error "Could not get current user info. Skipping RBAC."
        return
    fi
    log_info "Assigning roles for: $upn ($oid)"
    sub_id=$(_az_tsv account show --query id -o tsv)

    # Cosmos DB (uses its own role system, not ARM RBAC)
    local cosmos_name
    cosmos_name=$(_az_tsv cosmosdb list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    if [[ -n "$cosmos_name" ]]; then
        local existing_cosmos
        existing_cosmos=$(_az_tsv cosmosdb sql role assignment list \
            --resource-group "$RESOURCE_GROUP" --account-name "$cosmos_name" \
            --query "[?principalId=='$oid']" -o tsv)
        if [[ -n "$existing_cosmos" ]]; then
            log_success "  Cosmos DB Data Contributor: already assigned"
        else
            log_info "  Assigning Cosmos DB Data Contributor..."
            local cosmos_rc=0
            local cosmos_scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.DocumentDB/databaseAccounts/$cosmos_name"
            MSYS_NO_PATHCONV=1 az cosmosdb sql role assignment create \
                --resource-group "$RESOURCE_GROUP" --account-name "$cosmos_name" \
                --role-definition-name "Cosmos DB Built-in Data Contributor" \
                --principal-id "$oid" \
                --scope "$cosmos_scope" \
                --output none 2>/dev/null || cosmos_rc=$?
            if [[ $cosmos_rc -eq 0 ]]; then
                log_success "    Cosmos DB role assigned"
            else
                log_warn "    Cosmos DB role assignment failed (may need elevated permissions)"
                record_role_failure "Cosmos DB Built-in Data Contributor" "$upn" "$cosmos_scope" "AssignmentFailed"
            fi
        fi
    fi

    # AI Foundry roles — project is a sub-resource under the AI Services account
    local ai_svc ai_proj
    ai_svc=$(_az_tsv cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIServices'].name | [0]" -o tsv)
    if [[ -n "$ai_svc" ]]; then
        ai_proj=$(_az_tsv cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
            --query "[?kind=='AIProject'].name | [0]" -o tsv)
        # If not found as separate resource, look for it as a sub-resource
        if [[ -z "$ai_proj" ]]; then
            ai_proj=$(MSYS_NO_PATHCONV=1 az rest --method get \
                --url "https://management.azure.com/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$ai_svc/projects?api-version=2025-06-01" \
                --query "value[0].name" -o tsv 2>/dev/null) || true
            ai_proj="${ai_proj//$'\r'/}"
            # Strip parent prefix if present (e.g. "parent/proj-name" -> "proj-name")
            ai_proj="${ai_proj##*/}"
        fi
    fi
    if [[ -n "$ai_svc" && -n "$ai_proj" ]]; then
        local scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$ai_svc/projects/$ai_proj"
        for role in "Azure AI User" "Azure AI Developer" "Cognitive Services OpenAI User"; do
            local existing
            existing=$(_az_tsv role assignment list --assignee "$oid" --role "$role" --scope "$scope" --query "[0].id" -o tsv)
            if [[ -n "$existing" ]]; then
                log_success "  $role: already assigned"
                continue
            fi
            # Verify the role definition exists in this subscription before trying to assign.
            # Older subscriptions / sovereign clouds may not have newer AI Foundry roles.
            if ! test_role_definition_exists "$role" "$sub_id"; then
                log_warn "  $role: role definition NOT FOUND in subscription '$sub_id'"
                log_warn "    Likely cause: Microsoft.CognitiveServices RP not registered, or AI Foundry role not yet available in this cloud."
                record_role_failure "$role" "$upn" "$scope" "RoleDefinitionNotFound"
                continue
            fi
            log_info "  Assigning '$role'..."
            local role_rc=0
            MSYS_NO_PATHCONV=1 az role assignment create --assignee "$upn" --role "$role" --scope "$scope" --output none 2>/dev/null || role_rc=$?
            if [[ $role_rc -eq 0 ]]; then
                log_success "    $role assigned"
            else
                log_warn "    $role assignment failed"
                record_role_failure "$role" "$upn" "$scope" "AssignmentFailed"
            fi
        done
    else
        log_warn "  No AI Foundry project found in $RESOURCE_GROUP -- skipping AI role assignments"
    fi

    # Search
    local search_name
    search_name=$(_az_tsv search service list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    if [[ -n "$search_name" ]]; then
        local scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$search_name"
        local existing
        existing=$(_az_tsv role assignment list --assignee "$oid" --role "Search Index Data Contributor" --scope "$scope" --query "[0].id" -o tsv)
        if [[ -n "$existing" ]]; then
            log_success "  Search Index Data Contributor: already assigned"
        else
            log_info "  Assigning Search Index Data Contributor..."
            local search_rc=0
            MSYS_NO_PATHCONV=1 az role assignment create --assignee "$upn" --role "Search Index Data Contributor" --scope "$scope" --output none 2>/dev/null || search_rc=$?
            if [[ $search_rc -eq 0 ]]; then
                log_success "    Search role assigned"
            else
                log_warn "    Search role assignment failed"
                record_role_failure "Search Index Data Contributor" "$upn" "$scope" "AssignmentFailed"
            fi
        fi
    fi

    # Storage
    local storage_name
    storage_name=$(_az_tsv storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
    if [[ -n "$storage_name" ]]; then
        local scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$storage_name"
        local existing
        existing=$(_az_tsv role assignment list --assignee "$oid" --role "Storage Blob Data Contributor" --scope "$scope" --query "[0].id" -o tsv)
        if [[ -n "$existing" ]]; then
            log_success "  Storage Blob Data Contributor: already assigned"
        else
            log_info "  Assigning Storage Blob Data Contributor..."
            local storage_rc=0
            MSYS_NO_PATHCONV=1 az role assignment create --assignee "$upn" --role "Storage Blob Data Contributor" --scope "$scope" --output none 2>/dev/null || storage_rc=$?
            if [[ $storage_rc -eq 0 ]]; then
                log_success "    Storage role assigned"
            else
                log_warn "    Storage role assignment failed"
                record_role_failure "Storage Blob Data Contributor" "$upn" "$scope" "AssignmentFailed"
            fi
        fi
    fi

    log_warn "RBAC changes may take 5-10 minutes to propagate"
}

# ==============================================================================
# Step 5: Backend Setup
# ==============================================================================

setup_backend() {
    log_step "Step 5: Setting up Backend (src/backend)"

    cd "$BACKEND_DIR"

    # Check for activate script, not just the directory (handles broken/incomplete venvs)
    if [[ ! -f ".venv/Scripts/activate" ]] && [[ ! -f ".venv/bin/activate" ]]; then
        [[ -d ".venv" ]] && log_warn "Existing .venv is incomplete, recreating..."
        log_info "Creating virtual environment..."
        uv venv --seed .venv
    else
        log_info "Virtual environment already exists"
    fi

    log_info "Installing dependencies..."
    if ! uv sync --python 3.12 --extra dev; then
        log_warn "uv sync failed; retrying with --refresh..."
        if ! uv sync --python 3.12 --extra dev --refresh; then
            log_error "Backend 'uv sync' failed after retry. Check network/proxy and that Python 3.12 is on PATH, then re-run."
            cd "$REPO_ROOT"
            exit 1
        fi
    fi

    log_success "Backend setup complete"
    cd "$REPO_ROOT"
}

# ==============================================================================
# Step 6: MCP Server Setup
# ==============================================================================

setup_mcp_server() {
    log_step "Step 6: Setting up MCP Server (src/mcp_server)"

    cd "$MCP_DIR"

    # Check for activate script, not just the directory (handles broken/incomplete venvs)
    if [[ ! -f ".venv/Scripts/activate" ]] && [[ ! -f ".venv/bin/activate" ]]; then
        [[ -d ".venv" ]] && log_warn "Existing .venv is incomplete, recreating..."
        log_info "Creating virtual environment..."
        uv venv --seed .venv
    else
        log_info "Virtual environment already exists"
    fi

    log_info "Installing dependencies..."
    if ! uv sync --python 3.12; then
        log_warn "uv sync failed; retrying with --refresh..."
        if ! uv sync --python 3.12 --refresh; then
            log_error "MCP Server 'uv sync' failed after retry. Check network/proxy and that Python 3.12 is on PATH, then re-run."
            cd "$REPO_ROOT"
            exit 1
        fi
    fi

    log_success "MCP Server setup complete"
    cd "$REPO_ROOT"
}

# ==============================================================================
# Step 7: Frontend Setup
# ==============================================================================

setup_frontend() {
    log_step "Step 7: Setting up Frontend (src/App)"

    cd "$FRONTEND_DIR"

    # Check for activate script, not just directory (handles broken/incomplete venvs)
    if [[ ! -f ".venv/Scripts/activate" ]] && [[ ! -f ".venv/bin/activate" ]]; then
        if [[ -d ".venv" ]]; then
            log_warn "Existing .venv is incomplete (no activate script), recreating..."
        else
            log_info "Creating Python virtual environment..."
        fi
        "$PYTHON_CMD" -m venv --clear .venv
    else
        log_info "Python virtual environment already exists"
    fi

    log_info "Installing Python dependencies..."
    activate_venv
    if ! pip install -q -r requirements.txt; then
        deactivate 2>/dev/null || true
        log_error "Frontend 'pip install' failed. Check network/proxy and the Python venv, then re-run."
        cd "$REPO_ROOT"
        exit 1
    fi
    deactivate 2>/dev/null || true

    log_info "Installing npm dependencies..."
    if ! npm install; then
        log_warn "npm install failed; retrying with --legacy-peer-deps..."
        if ! npm install --legacy-peer-deps; then
            log_error "Frontend 'npm install' failed after retry. Check Node.js version (>=18) and your npm registry, then re-run."
            cd "$REPO_ROOT"
            exit 1
        fi
    fi

    log_info "Building frontend..."
    if ! npm run build; then
        log_error "Frontend 'npm run build' failed. Review the build output above and re-run."
        cd "$REPO_ROOT"
        exit 1
    fi

    log_success "Frontend setup complete"
    cd "$REPO_ROOT"
}

# ==============================================================================
# Step 8: VS Code Configuration
# ==============================================================================

setup_vscode() {
    if [[ "$SKIP_VSCODE" == "true" ]]; then return; fi

    log_step "Step 8: Configuring VS Code"

    local vscode_dir="$REPO_ROOT/.vscode"
    mkdir -p "$vscode_dir"

    local extensions_file="$vscode_dir/extensions.json"
    if [[ ! -f "$extensions_file" ]]; then
        cat > "$extensions_file" << 'EXTEOF'
{
    "recommendations": [
        "ms-python.python",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-vscode-remote.remote-wsl",
        "ms-vscode-remote.remote-containers",
        "redhat.vscode-yaml",
        "ms-vscode.azure-account",
        "ms-python.mypy-type-checker"
    ]
}
EXTEOF
        log_success "Created .vscode/extensions.json"
    fi

    local settings_file="$vscode_dir/settings.json"
    if [[ ! -f "$settings_file" ]]; then
        cat > "$settings_file" << 'SETEOF'
{
    "python.defaultInterpreterPath": "${workspaceFolder}/src/backend/.venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.formatting.provider": "black",
    "python.debugging.logLevel": "Debug",
    "debug.inlineValues": "on",
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    },
    "python.analysis.extraPaths": [
        "${workspaceFolder}/src/backend",
        "${workspaceFolder}/src/mcp_server"
    ]
}
SETEOF
        log_success "Created .vscode/settings.json"
    fi
}

# ==============================================================================
# Summary
# ==============================================================================

print_summary() {
    log_step "Setup Complete!"

    echo ""
    echo -e "${GREEN}All services have been configured successfully.${NC}"
    echo ""
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    echo -e "${CYAN}  HOW TO START THE APPLICATION${NC}"
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    echo ""
    echo "  Open 3 separate terminals and start services in this order:"
    echo ""

    echo -e "${YELLOW}  Terminal 1 - Backend (port 8000):${NC}"
    echo "    cd src/backend"
    echo "    Activate virtual environment:"
    echo "      PowerShell : .\.venv\Scripts\Activate.ps1"
    echo "      Git Bash   : source .venv/Scripts/activate"
    echo "      Linux/macOS: source .venv/bin/activate"
    echo "    python app.py"
    echo ""

    echo -e "${YELLOW}  Terminal 2 - MCP Server (port 9000):${NC}"
    echo "    cd src/mcp_server"
    echo "    Activate virtual environment:"
    echo "      PowerShell : .\.venv\Scripts\Activate.ps1"
    echo "      Git Bash   : source .venv/Scripts/activate"
    echo "      Linux/macOS: source .venv/bin/activate"
    echo "    python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 9000"
    echo ""

    echo -e "${YELLOW}  Terminal 3 - Frontend (port 3000):${NC}"
    echo "    cd src/App"
    echo "    Activate virtual environment:"
    echo "      PowerShell : .\.venv\Scripts\Activate.ps1"
    echo "      Git Bash   : source .venv/Scripts/activate"
    echo "      Linux/macOS: source .venv/bin/activate"
    echo "    python frontend_server.py"
    echo ""

    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    echo -e "${CYAN}  SERVICE URLs${NC}"
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    echo -e "${GREEN}  Application UI:  http://localhost:3000${NC}"
    echo -e "${GREEN}  Backend API:     http://localhost:8000${NC}"
    echo -e "${GREEN}  API Docs:        http://localhost:8000/docs${NC}"
    echo -e "${GREEN}  MCP Server:      http://localhost:9000${NC}"
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    echo ""
}

# ==============================================================================
# Main
# ==============================================================================

echo ""
echo -e "${CYAN}+==============================================================+${NC}"
echo -e "${CYAN}|     MACAE - Local Development Setup (Linux/macOS/Bash)      |${NC}"
echo -e "${CYAN}|     Multi-Agent Custom Automation Engine                     |${NC}"
echo -e "${CYAN}+==============================================================+${NC}"
echo ""

parse_args "$@"

if [[ ! -f "$REPO_ROOT/src/backend/app.py" ]]; then
    log_error "This script must be run from the repository root directory"
    exit 1
fi

report_failed_role_assignments() {
    if [[ ${#FAILED_ROLE_ASSIGNMENTS[@]} -eq 0 ]]; then return 0; fi

    local red='\033[31m' yellow='\033[33m' reset='\033[0m'
    echo ""
    echo -e "${red}================================================================${reset}"
    echo -e "${red} !  Setup completed, but ${#FAILED_ROLE_ASSIGNMENTS[@]} required role assignment(s) FAILED${reset}"
    echo -e "${red}    The application will get 403 errors at runtime without these.${reset}"
    echo -e "${red}================================================================${reset}"
    echo ""
    local entry role assignee scope reason
    for entry in "${FAILED_ROLE_ASSIGNMENTS[@]}"; do
        IFS='|' read -r role assignee scope reason <<< "$entry"
        echo -e "  ${yellow}* ${role}${reset}"
        echo "      Reason : $reason"
        echo "      Scope  : $scope"
        if [[ "$reason" == "RoleDefinitionNotFound" ]]; then
            echo "      Fix    : Register the resource provider, or have an admin run:"
            echo "               az provider register -n Microsoft.CognitiveServices --wait"
        else
            echo "      Fix    : Ask an admin with 'User Access Administrator' (or 'Owner') to run:"
            echo "               az role assignment create --assignee \"$assignee\" \\"
            echo "                 --role \"$role\" --scope \"$scope\""
        fi
        echo ""
    done
    echo -e "${yellow}Re-run this script once the roles are in place.${reset}"
    echo ""
    exit 2
}

check_prerequisites
check_azure_auth
check_azure_roles
fetch_configuration
assign_rbac_roles
setup_backend
setup_mcp_server
setup_frontend
setup_vscode
print_summary
report_failed_role_assignments
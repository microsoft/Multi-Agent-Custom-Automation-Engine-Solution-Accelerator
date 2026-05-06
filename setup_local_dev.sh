#!/usr/bin/env bash
# ==============================================================================
# MACAE - Local Development Setup Script
# ==============================================================================
# Automates the entire local development setup for the Multi-Agent Custom
# Automation Engine Solution Accelerator.
#
# Supports fetching Azure config from:
#   1. Existing .env file (already configured)
#   2. Azure Resource Group (discovers resources via az CLI)
#   3. azd deployment outputs (if deployed via azd up)
#
# Usage:
#   ./setup_local_dev.sh [OPTIONS]
#
# Options:
#   -g, --resource-group <name>    Azure Resource Group name
#   -s, --subscription <id>        Azure Subscription ID
#   -e, --env-name <name>          azd environment name
#   --assign-rbac                  Assign RBAC roles to current user (requires permissions)
#   --skip-prereqs                 Skip prerequisite installation
#   --skip-vscode                  Skip VS Code configuration
#   -h, --help                     Show this help message
#
# Examples:
#   ./setup_local_dev.sh -g my-resource-group
#   ./setup_local_dev.sh -e my-azd-env
#   ./setup_local_dev.sh --resource-group rg-macae-dev --assign-rbac
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory (repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/src/backend"
MCP_DIR="$SCRIPT_DIR/src/mcp_server"
FRONTEND_DIR="$SCRIPT_DIR/src/App"

# Default options
RESOURCE_GROUP=""
SUBSCRIPTION=""
AZD_ENV_NAME=""
ASSIGN_RBAC=false
SKIP_PREREQS=false
SKIP_VSCODE=false

# ==============================================================================
# Helper Functions
# ==============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }

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
    [[ "$response" =~ ^[Yy]$ ]]
}

command_exists() { command -v "$1" &>/dev/null; }

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if grep -qi "ubuntu\|debian" /etc/os-release 2>/dev/null; then
            echo "debian"
        elif grep -qi "fedora\|rhel\|centos" /etc/os-release 2>/dev/null; then
            echo "rhel"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -g|--resource-group)
                RESOURCE_GROUP="$2"; shift 2 ;;
            -s|--subscription)
                SUBSCRIPTION="$2"; shift 2 ;;
            -e|--env-name)
                AZD_ENV_NAME="$2"; shift 2 ;;
            --assign-rbac)
                ASSIGN_RBAC=true; shift ;;
            --skip-vscode)
                SKIP_VSCODE=true; shift ;;
            -h|--help)
                show_help; exit 0 ;;
            *)
                log_error "Unknown option: $1"; show_help; exit 1 ;;
        esac
    done
}

show_help() {
    head -35 "${BASH_SOURCE[0]}" | tail -30
}

# ==============================================================================
# Step 1: Prerequisites Check & Installation
# ==============================================================================

check_prerequisites() {
    log_step "Step 1: Checking Prerequisites"

    local missing=()
    local OS
    OS=$(detect_os)

    # Check Python 3.12+
    if command_exists python3.12; then
        log_success "Python 3.12 found: $(python3.12 --version)"
    elif command_exists python3 && python3 -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" 2>/dev/null; then
        log_success "Python 3 found (3.12+): $(python3 --version)"
    else
        missing+=("python3.12")
    fi

    # Check Node.js
    if command_exists node; then
        log_success "Node.js found: $(node --version)"
    else
        missing+=("nodejs")
    fi

    # Check npm
    if command_exists npm; then
        log_success "npm found: $(npm --version)"
    else
        missing+=("npm")
    fi

    # Check uv
    if command_exists uv; then
        log_success "uv found: $(uv --version)"
    else
        missing+=("uv")
    fi

    # Check Azure CLI
    if command_exists az; then
        log_success "Azure CLI found: $(az --version 2>/dev/null | head -1)"
    else
        missing+=("azure-cli")
    fi

    # Check git
    if command_exists git; then
        log_success "Git found: $(git --version)"
    else
        missing+=("git")
    fi

    if [[ ${#missing[@]} -eq 0 ]]; then
        log_success "All prerequisites are installed!"
        return 0
    fi

    log_error "Missing prerequisites: ${missing[*]}"
    echo ""
    log_warn "Please install the following before proceeding:"
    echo ""
    for tool in "${missing[@]}"; do
        case "$tool" in
            python3.12)
                echo "  ┌─ Python 3.12 ─────────────────────────────────────────────────"
                echo "  │  Download: https://www.python.org/downloads/"
                echo "  │  Quick install:"
                echo "  │    macOS:   brew install python@3.12"
                echo "  │    Ubuntu:  sudo apt update && sudo apt install python3.12 python3.12-venv -y"
                echo "  │    RHEL:    sudo dnf install python3.12 python3.12-devel -y"
                echo "  │    Windows: winget install Python.Python.3.12"
                echo "  │  Verify: python3.12 --version  (should show 3.12.x)"
                echo "  └──────────────────────────────────────────────────────────────"
                ;;
            nodejs|npm)
                echo "  ┌─ Node.js & npm ───────────────────────────────────────────────"
                echo "  │  Download: https://nodejs.org/ (LTS version)"
                echo "  │  Quick install:"
                echo "  │    macOS:   brew install node"
                echo "  │    Ubuntu:  sudo apt install nodejs npm -y"
                echo "  │    RHEL:    sudo dnf install nodejs npm -y"
                echo "  │    Windows: winget install OpenJS.NodeJS.LTS"
                echo "  │  Verify: node --version && npm --version"
                echo "  └──────────────────────────────────────────────────────────────"
                ;;
            uv)
                echo "  ┌─ uv (Python package manager) ─────────────────────────────────"
                echo "  │  Quick install:"
                echo "  │    All OS:  curl -LsSf https://astral.sh/uv/install.sh | sh"
                echo "  │    Or:      pip install uv"
                echo "  │    Windows: irm https://astral.sh/uv/install.ps1 | iex"
                echo "  │  Docs: https://docs.astral.sh/uv/getting-started/installation/"
                echo "  │  Verify: uv --version"
                echo "  │  Note: After install, run: source ~/.bashrc (or restart terminal)"
                echo "  └──────────────────────────────────────────────────────────────"
                ;;
            azure-cli)
                echo "  ┌─ Azure CLI ───────────────────────────────────────────────────"
                echo "  │  Quick install:"
                echo "  │    macOS:   brew install azure-cli"
                echo "  │    Ubuntu:  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
                echo "  │    RHEL:    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc"
                echo "  │             sudo dnf install azure-cli -y"
                echo "  │    Windows: winget install Microsoft.AzureCLI"
                echo "  │  Docs: https://learn.microsoft.com/cli/azure/install-azure-cli"
                echo "  │  Verify: az --version"
                echo "  │  After install: az login"
                echo "  └──────────────────────────────────────────────────────────────"
                ;;
            git)
                echo "  ┌─ Git ─────────────────────────────────────────────────────────"
                echo "  │  Download: https://git-scm.com/downloads"
                echo "  │  Quick install:"
                echo "  │    macOS:   brew install git"
                echo "  │    Ubuntu:  sudo apt install git -y"
                echo "  │    RHEL:    sudo dnf install git -y"
                echo "  │    Windows: winget install Git.Git"
                echo "  │  Verify: git --version"
                echo "  └──────────────────────────────────────────────────────────────"
                ;;
        esac
    done
    echo ""
    echo "  For detailed step-by-step instructions, see:"
    echo "  https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/blob/main/docs/LocalDevelopmentSetup.md#step-1-prerequisites---install-required-tools"
    echo ""
    echo "  Also see: docs/NON_DEVCONTAINER_SETUP.md for VS Code extension recommendations."
    echo ""
    log_info "After installing, restart your terminal and re-run this script."
    exit 1
}

# ==============================================================================
# Step 2: Azure Authentication
# ==============================================================================

check_azure_auth() {
    log_step "Step 2: Azure Authentication"

    if ! az account show &>/dev/null; then
        log_warn "Not logged into Azure CLI"
        log_info "Running 'az login'..."
        az login
    fi

    # Set subscription if provided
    if [[ -n "$SUBSCRIPTION" ]]; then
        log_info "Setting subscription to: $SUBSCRIPTION"
        az account set --subscription "$SUBSCRIPTION"
    fi

    local account_info
    account_info=$(az account show --output json)
    local sub_name
    sub_name=$(echo "$account_info" | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])" 2>/dev/null || echo "unknown")
    local sub_id
    sub_id=$(echo "$account_info" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "unknown")

    log_success "Logged in to Azure"
    log_info "  Subscription: $sub_name ($sub_id)"

    if [[ -z "$SUBSCRIPTION" ]]; then
        SUBSCRIPTION="$sub_id"
    fi

    if ! confirm "Is this the correct subscription?" "y"; then
        log_info "Available subscriptions:"
        az account list --output table --query "[].{Name:name, Id:id, State:state}"
        read -rp "Enter subscription ID: " SUBSCRIPTION
        az account set --subscription "$SUBSCRIPTION"
        log_success "Switched to subscription: $SUBSCRIPTION"
    fi
}

# ==============================================================================
# Step 3: Fetch Configuration
# ==============================================================================

fetch_configuration() {
    log_step "Step 3: Fetching Azure Configuration"

    local config_source=""

    # Priority 1: Resource group provided via CLI arg
    if [[ -n "$RESOURCE_GROUP" ]]; then
        config_source="rg"
    # Priority 2: azd env provided via CLI arg
    elif [[ -n "$AZD_ENV_NAME" ]]; then
        config_source="azd"
    # Priority 3: Existing .env with valid values - use silently
    elif [[ -f "$BACKEND_DIR/.env" ]] && grep -q "COSMOSDB_ENDPOINT=https://" "$BACKEND_DIR/.env" 2>/dev/null; then
        log_info "Existing .env file found with valid configuration. Using it."
        config_source="existing"
    fi

    # If still not determined, ask for RG name
    if [[ -z "$config_source" ]]; then
        echo ""
        log_info "No resource group provided and no existing .env found."
        log_info "Please provide your Azure Resource Group name (from your deployment)."
        read -rp "Resource Group name: " RESOURCE_GROUP
        if [[ -z "$RESOURCE_GROUP" ]]; then
            log_error "Resource group name is required."
            log_info "Usage: ./setup_local_dev.sh -g <resource-group-name>"
            exit 1
        fi
        config_source="rg"
    fi

    case "$config_source" in
        azd)    fetch_from_azd ;;
        rg)     fetch_from_resource_group ;;
        existing)
            if [[ -f "$BACKEND_DIR/.env" ]]; then
                log_success "Using existing .env file at $BACKEND_DIR/.env"
            else
                log_warn "No .env file found. Creating from template..."
                cp "$BACKEND_DIR/.env.sample" "$BACKEND_DIR/.env"
                log_warn "Please manually fill in values in: $BACKEND_DIR/.env"
                log_warn "Then re-run this script."
                exit 0
            fi ;;
    esac
}

fetch_from_azd() {
    log_info "Fetching configuration from azd environment: $AZD_ENV_NAME"

    if ! command_exists azd; then
        log_error "azd CLI not found. Install from https://aka.ms/azd"
        exit 1
    fi

    # Get all azd env values
    local azd_values
    azd_values=$(azd env get-values --environment "$AZD_ENV_NAME" 2>/dev/null) || {
        log_error "Failed to get values from azd environment '$AZD_ENV_NAME'"
        log_info "Make sure you've run 'azd up' or 'azd provision' first"
        exit 1
    }

    generate_env_from_values "$azd_values"
    log_success "Configuration fetched from azd environment"
}

fetch_from_resource_group() {
    log_info "Fetching configuration from Resource Group: $RESOURCE_GROUP"

    # Validate RG exists
    if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
        log_error "Resource group '$RESOURCE_GROUP' not found"
        exit 1
    fi

    # Strategy: Find the backend container app and extract its env vars
    log_info "Looking for backend container app..."

    local container_apps
    container_apps=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv 2>/dev/null || true)

    local backend_app=""
    if [[ -n "$container_apps" ]]; then
        # Find the backend app (has COSMOSDB_ENDPOINT env var, not the MCP one)
        while IFS= read -r app_name; do
            if [[ "$app_name" == ca-mcp-* ]]; then
                continue
            fi
            # Check if this app has the backend env vars
            local has_cosmos
            has_cosmos=$(az containerapp show --name "$app_name" --resource-group "$RESOURCE_GROUP" \
                --query "properties.template.containers[0].env[?name=='COSMOSDB_ENDPOINT'].value" -o tsv 2>/dev/null || true)
            if [[ -n "$has_cosmos" ]]; then
                backend_app="$app_name"
                break
            fi
        done <<< "$container_apps"
    fi

    if [[ -n "$backend_app" ]]; then
        log_success "Found backend container app: $backend_app"
        log_info "Extracting environment variables..."
        fetch_env_from_container_app "$backend_app"
    else
        log_warn "No backend container app found. Discovering resources individually..."
        fetch_env_from_resources
    fi

    # Check for private networking
    check_private_networking
}

fetch_env_from_container_app() {
    local app_name="$1"

    # Get all env vars from the container app
    local env_json
    env_json=$(az containerapp show --name "$app_name" --resource-group "$RESOURCE_GROUP" \
        --query "properties.template.containers[0].env" -o json 2>/dev/null)

    if [[ -z "$env_json" || "$env_json" == "null" ]]; then
        log_error "Could not read environment variables from container app"
        exit 1
    fi

    # Parse env vars into key=value format
    local env_values
    env_values=$(echo "$env_json" | python3 -c "
import sys, json
envs = json.load(sys.stdin)
for e in envs:
    name = e.get('name', '')
    value = e.get('value', '')
    if name and value:
        print(f'{name}={value}')
" 2>/dev/null)

    generate_env_from_values "$env_values"
    log_success "Environment variables extracted from container app"
}

fetch_env_from_resources() {
    # Fallback: discover resources individually
    log_info "Discovering Azure resources in resource group..."

    local sub_id
    sub_id=$(az account show --query id -o tsv)
    local tenant_id
    tenant_id=$(az account show --query tenantId -o tsv)

    # CosmosDB
    local cosmos_name cosmos_endpoint
    cosmos_name=$(az cosmosdb list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)
    if [[ -n "$cosmos_name" ]]; then
        cosmos_endpoint="https://${cosmos_name}.documents.azure.com:443/"
        log_success "  CosmosDB: $cosmos_name"
    else
        log_warn "  CosmosDB: not found"
        cosmos_endpoint=""
    fi

    # AI Services (Cognitive Services)
    local ai_services_name ai_endpoint
    ai_services_name=$(az cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIServices' || kind=='CognitiveServices'].name | [0]" -o tsv 2>/dev/null || true)
    if [[ -n "$ai_services_name" ]]; then
        ai_endpoint="https://${ai_services_name}.openai.azure.com/"
        log_success "  AI Services: $ai_services_name"
    else
        log_warn "  AI Services: not found"
        ai_endpoint=""
    fi

    # AI Foundry Project
    local ai_project_name ai_project_endpoint
    ai_project_name=$(az cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIProject'].name | [0]" -o tsv 2>/dev/null || true)
    if [[ -n "$ai_project_name" && -n "$ai_services_name" ]]; then
        ai_project_endpoint="https://${ai_services_name}.services.ai.azure.com/api/projects/${ai_project_name}"
        log_success "  AI Project: $ai_project_name"
    else
        # Try alternate endpoint format
        ai_project_endpoint=""
        log_warn "  AI Project: not found (will need manual configuration)"
    fi

    # Search Service
    local search_name search_endpoint
    search_name=$(az search service list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)
    if [[ -n "$search_name" ]]; then
        search_endpoint="https://${search_name}.search.windows.net"
        log_success "  Search Service: $search_name"
    else
        log_warn "  Search Service: not found"
        search_endpoint=""
    fi

    # Application Insights
    local appinsights_key appinsights_connstr
    appinsights_key=$(az monitor app-insights component list --resource-group "$RESOURCE_GROUP" \
        --query "[0].instrumentationKey" -o tsv 2>/dev/null || true)
    appinsights_connstr=$(az monitor app-insights component list --resource-group "$RESOURCE_GROUP" \
        --query "[0].connectionString" -o tsv 2>/dev/null || true)
    if [[ -n "$appinsights_key" ]]; then
        log_success "  Application Insights: found"
    else
        log_warn "  Application Insights: not found (will use empty value)"
    fi

    # Storage Account
    local storage_name storage_blob_url
    storage_name=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)
    if [[ -n "$storage_name" ]]; then
        storage_blob_url="https://${storage_name}.blob.core.windows.net/"
        log_success "  Storage Account: $storage_name"
    else
        log_warn "  Storage Account: not found"
        storage_blob_url=""
    fi

    # Build env values
    local env_values
    env_values="COSMOSDB_ENDPOINT=${cosmos_endpoint}
COSMOSDB_DATABASE=macae
COSMOSDB_CONTAINER=memory
AZURE_OPENAI_ENDPOINT=${ai_endpoint}
AZURE_OPENAI_MODEL_NAME=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_RAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=${appinsights_key:-}
APPLICATIONINSIGHTS_CONNECTION_STRING=${appinsights_connstr:-}
AZURE_AI_SUBSCRIPTION_ID=${sub_id}
AZURE_AI_RESOURCE_GROUP=${RESOURCE_GROUP}
AZURE_AI_PROJECT_NAME=${ai_project_name:-}
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_AI_SEARCH_CONNECTION_NAME=macae-search-connection
AZURE_AI_SEARCH_ENDPOINT=${search_endpoint:-}
AZURE_COGNITIVE_SERVICES=https://cognitiveservices.azure.com/.default
AZURE_BING_CONNECTION_NAME=binggrnd
BING_CONNECTION_NAME=binggrnd
REASONING_MODEL_NAME=o4-mini
AZURE_TENANT_ID=${tenant_id}
AZURE_CLIENT_ID=
SUPPORTED_MODELS=[\"o3\",\"o4-mini\",\"gpt-4.1\",\"gpt-4.1-mini\"]
AZURE_STORAGE_BLOB_URL=${storage_blob_url:-}
AZURE_AI_PROJECT_ENDPOINT=${ai_project_endpoint:-}
AZURE_AI_AGENT_ENDPOINT=${ai_project_endpoint:-}
AZURE_AI_AGENT_API_VERSION=2025-05-01-preview
AZURE_AI_AGENT_PROJECT_CONNECTION_STRING=${ai_services_name:-}.services.ai.azure.com;${sub_id};${RESOURCE_GROUP};${ai_project_name:-}"

    generate_env_from_values "$env_values"
}

generate_env_from_values() {
    local raw_values="$1"
    local env_file="$BACKEND_DIR/.env"

    log_info "Generating .env file at: $env_file"

    # Start with the fetched values, then override local dev settings
    # Parse values into associative array
    declare -A env_vars

    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" == \#* ]] && continue
        # Remove surrounding quotes from values
        local key="${line%%=*}"
        local value="${line#*=}"
        # Strip quotes
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        if [[ -n "$key" ]]; then
            env_vars["$key"]="$value"
        fi
    done <<< "$raw_values"

    # Apply local development overrides
    env_vars["APP_ENV"]="dev"
    env_vars["BACKEND_API_URL"]="http://localhost:8000"
    env_vars["FRONTEND_SITE_NAME"]="*"
    env_vars["MCP_SERVER_ENDPOINT"]="http://localhost:9000/mcp"
    env_vars["MCP_SERVER_NAME"]="MacaeMcpServer"
    env_vars["MCP_SERVER_DESCRIPTION"]="MCP server with greeting, HR, and planning tools"

    # Write the .env file
    {
        echo "# ==================================================================="
        echo "# MACAE Local Development Configuration"
        echo "# Generated by setup_local_dev.sh on $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# ==================================================================="
        echo ""
        echo "# --- Local Development Settings (DO NOT CHANGE) ---"
        echo "APP_ENV=dev"
        echo "BACKEND_API_URL=http://localhost:8000"
        echo "FRONTEND_SITE_NAME=*"
        echo "MCP_SERVER_ENDPOINT=http://localhost:9000/mcp"
        echo "MCP_SERVER_NAME=MacaeMcpServer"
        echo 'MCP_SERVER_DESCRIPTION="MCP server with greeting, HR, and planning tools"'
        echo ""
        echo "# --- Azure Authentication ---"
        echo "AZURE_TENANT_ID=${env_vars[AZURE_TENANT_ID]:-}"
        echo "AZURE_CLIENT_ID=${env_vars[AZURE_CLIENT_ID]:-}"
        echo ""
        echo "# --- CosmosDB ---"
        echo "COSMOSDB_ENDPOINT=${env_vars[COSMOSDB_ENDPOINT]:-}"
        echo "COSMOSDB_DATABASE=${env_vars[COSMOSDB_DATABASE]:-macae}"
        echo "COSMOSDB_CONTAINER=${env_vars[COSMOSDB_CONTAINER]:-memory}"
        echo ""
        echo "# --- Azure OpenAI ---"
        echo "AZURE_OPENAI_ENDPOINT=${env_vars[AZURE_OPENAI_ENDPOINT]:-}"
        echo "AZURE_OPENAI_MODEL_NAME=${env_vars[AZURE_OPENAI_MODEL_NAME]:-gpt-4.1-mini}"
        echo "AZURE_OPENAI_DEPLOYMENT_NAME=${env_vars[AZURE_OPENAI_DEPLOYMENT_NAME]:-gpt-4.1-mini}"
        echo "AZURE_OPENAI_RAI_DEPLOYMENT_NAME=${env_vars[AZURE_OPENAI_RAI_DEPLOYMENT_NAME]:-gpt-4.1}"
        echo "AZURE_OPENAI_API_VERSION=${env_vars[AZURE_OPENAI_API_VERSION]:-2024-12-01-preview}"
        echo "REASONING_MODEL_NAME=${env_vars[REASONING_MODEL_NAME]:-o4-mini}"
        echo "SUPPORTED_MODELS=${env_vars[SUPPORTED_MODELS]:-'[\"o3\",\"o4-mini\",\"gpt-4.1\",\"gpt-4.1-mini\"]'}"
        echo ""
        echo "# --- Azure AI Foundry ---"
        echo "AZURE_AI_SUBSCRIPTION_ID=${env_vars[AZURE_AI_SUBSCRIPTION_ID]:-}"
        echo "AZURE_AI_RESOURCE_GROUP=${env_vars[AZURE_AI_RESOURCE_GROUP]:-}"
        echo "AZURE_AI_PROJECT_NAME=${env_vars[AZURE_AI_PROJECT_NAME]:-}"
        echo "AZURE_AI_PROJECT_ENDPOINT=${env_vars[AZURE_AI_PROJECT_ENDPOINT]:-}"
        echo "AZURE_AI_AGENT_ENDPOINT=${env_vars[AZURE_AI_AGENT_ENDPOINT]:-}"
        echo "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=${env_vars[AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME]:-gpt-4.1-mini}"
        echo "AZURE_AI_AGENT_API_VERSION=${env_vars[AZURE_AI_AGENT_API_VERSION]:-2025-05-01-preview}"
        echo "AZURE_AI_AGENT_PROJECT_CONNECTION_STRING=${env_vars[AZURE_AI_AGENT_PROJECT_CONNECTION_STRING]:-}"
        echo "AZURE_COGNITIVE_SERVICES=${env_vars[AZURE_COGNITIVE_SERVICES]:-https://cognitiveservices.azure.com/.default}"
        echo ""
        echo "# --- Azure AI Search ---"
        echo "AZURE_AI_SEARCH_CONNECTION_NAME=${env_vars[AZURE_AI_SEARCH_CONNECTION_NAME]:-}"
        echo "AZURE_AI_SEARCH_ENDPOINT=${env_vars[AZURE_AI_SEARCH_ENDPOINT]:-}"
        echo ""
        echo "# --- Application Insights ---"
        echo "APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=${env_vars[APPLICATIONINSIGHTS_INSTRUMENTATION_KEY]:-}"
        echo "APPLICATIONINSIGHTS_CONNECTION_STRING=${env_vars[APPLICATIONINSIGHTS_CONNECTION_STRING]:-}"
        echo ""
        echo "# --- Storage ---"
        echo "AZURE_STORAGE_BLOB_URL=${env_vars[AZURE_STORAGE_BLOB_URL]:-}"
        echo ""
        echo "# --- Bing ---"
        echo "AZURE_BING_CONNECTION_NAME=${env_vars[AZURE_BING_CONNECTION_NAME]:-binggrnd}"
        echo "BING_CONNECTION_NAME=${env_vars[BING_CONNECTION_NAME]:-binggrnd}"
        echo ""
        echo "# --- Logging ---"
        echo "AZURE_BASIC_LOGGING_LEVEL=${env_vars[AZURE_BASIC_LOGGING_LEVEL]:-INFO}"
        echo "AZURE_PACKAGE_LOGGING_LEVEL=${env_vars[AZURE_PACKAGE_LOGGING_LEVEL]:-WARNING}"
        echo "AZURE_LOGGING_PACKAGES=${env_vars[AZURE_LOGGING_PACKAGES]:-}"
    } > "$env_file"

    log_success ".env file generated successfully"

    # Validate required keys
    local required_keys=("COSMOSDB_ENDPOINT" "AZURE_OPENAI_ENDPOINT" "AZURE_AI_SUBSCRIPTION_ID" "AZURE_AI_RESOURCE_GROUP" "AZURE_AI_PROJECT_NAME" "AZURE_AI_AGENT_ENDPOINT")
    local missing_keys=()
    for key in "${required_keys[@]}"; do
        local val="${env_vars[$key]:-}"
        if [[ -z "$val" ]]; then
            missing_keys+=("$key")
        fi
    done

    if [[ ${#missing_keys[@]} -gt 0 ]]; then
        log_warn "The following required values are empty (edit .env manually):"
        for k in "${missing_keys[@]}"; do
            log_warn "  - $k"
        done
    fi
}

check_private_networking() {
    # Check if resources have private endpoints / disabled public access
    log_info "Checking network accessibility..."

    local cosmos_name
    cosmos_name=$(az cosmosdb list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)

    if [[ -n "$cosmos_name" ]]; then
        local public_access
        public_access=$(az cosmosdb show --name "$cosmos_name" --resource-group "$RESOURCE_GROUP" \
            --query "publicNetworkAccess" -o tsv 2>/dev/null || true)
        if [[ "$public_access" == "Disabled" ]]; then
            echo ""
            log_warn "⚠️  PRIVATE NETWORKING DETECTED"
            log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_warn "CosmosDB has public network access DISABLED."
            log_warn "Local development may fail with connectivity errors."
            log_warn ""
            log_warn "Options:"
            log_warn "  1. Use a jumpbox/VM inside the VNet"
            log_warn "  2. Connect via VPN to the VNet"
            log_warn "  3. Temporarily enable public access on resources"
            log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            if ! confirm "Continue setup anyway?" "y"; then
                exit 0
            fi
        fi
    fi
}

# ==============================================================================
# Step 4: RBAC Assignment (Optional)
# ==============================================================================

assign_rbac_roles() {
    # Always assign RBAC when resource group is known (needed for local dev access)
    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_info "No resource group specified, skipping RBAC assignment."
        return 0
    fi

    log_step "Step 4: Assigning RBAC Roles"

    local user_object_id user_upn
    user_object_id=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)
    user_upn=$(az ad signed-in-user show --query userPrincipalName -o tsv 2>/dev/null || true)

    if [[ -z "$user_object_id" || -z "$user_upn" ]]; then
        log_error "Could not get current user info. Skipping RBAC."
        return 0
    fi

    log_info "Assigning roles for: $user_upn ($user_object_id)"

    local sub_id
    sub_id=$(az account show --query id -o tsv)

    # Cosmos DB (uses its own role system, not ARM RBAC)
    local cosmos_name
    cosmos_name=$(az cosmosdb list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)
    if [[ -n "$cosmos_name" ]]; then
        # Check if role already assigned
        local existing_cosmos
        existing_cosmos=$(az cosmosdb sql role assignment list \
            --resource-group "$RESOURCE_GROUP" --account-name "$cosmos_name" \
            --query "[?principalId=='$user_object_id'].id" -o tsv 2>/dev/null || true)
        if [[ -n "$existing_cosmos" ]]; then
            log_success "  Cosmos DB Data Contributor: already assigned ✓"
        else
            log_info "  Assigning Cosmos DB Built-in Data Contributor..."
            az cosmosdb sql role assignment create \
                --resource-group "$RESOURCE_GROUP" \
                --account-name "$cosmos_name" \
                --role-definition-name "Cosmos DB Built-in Data Contributor" \
                --principal-id "$user_object_id" \
                --scope "/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.DocumentDB/databaseAccounts/$cosmos_name" \
                2>/dev/null && log_success "    Cosmos DB role assigned" || log_warn "    Cosmos DB role assignment failed (may need elevated permissions)"
        fi
    fi

    # AI Foundry / Cognitive Services
    local ai_services_name
    ai_services_name=$(az cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIServices' || kind=='CognitiveServices'].name | [0]" -o tsv 2>/dev/null || true)
    local ai_project_name
    ai_project_name=$(az cognitiveservices account list --resource-group "$RESOURCE_GROUP" \
        --query "[?kind=='AIProject'].name | [0]" -o tsv 2>/dev/null || true)

    if [[ -n "$ai_services_name" && -n "$ai_project_name" ]]; then
        local scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/$ai_services_name/projects/$ai_project_name"

        for role in "Azure AI User" "Azure AI Developer" "Cognitive Services OpenAI User"; do
            local existing
            existing=$(az role assignment list --assignee "$user_object_id" --role "$role" --scope "$scope" \
                --query "[0].id" -o tsv 2>/dev/null || true)
            if [[ -n "$existing" ]]; then
                log_success "  $role: already assigned ✓"
            else
                log_info "  Assigning '$role'..."
                az role assignment create --assignee "$user_upn" --role "$role" --scope "$scope" \
                    2>/dev/null && log_success "    $role assigned" || log_warn "    $role assignment failed"
            fi
        done
    fi

    # Search Service
    local search_name
    search_name=$(az search service list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)
    if [[ -n "$search_name" ]]; then
        local scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/$search_name"
        local existing
        existing=$(az role assignment list --assignee "$user_object_id" --role "Search Index Data Contributor" --scope "$scope" \
            --query "[0].id" -o tsv 2>/dev/null || true)
        if [[ -n "$existing" ]]; then
            log_success "  Search Index Data Contributor: already assigned ✓"
        else
            log_info "  Assigning Search Index Data Contributor..."
            az role assignment create --assignee "$user_upn" --role "Search Index Data Contributor" --scope "$scope" \
                2>/dev/null && log_success "    Search role assigned" || log_warn "    Search role assignment failed"
        fi
    fi

    # Storage Account
    local storage_name
    storage_name=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)
    if [[ -n "$storage_name" ]]; then
        local scope="/subscriptions/$sub_id/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$storage_name"
        local existing
        existing=$(az role assignment list --assignee "$user_object_id" --role "Storage Blob Data Contributor" --scope "$scope" \
            --query "[0].id" -o tsv 2>/dev/null || true)
        if [[ -n "$existing" ]]; then
            log_success "  Storage Blob Data Contributor: already assigned ✓"
        else
            log_info "  Assigning Storage Blob Data Contributor..."
            az role assignment create --assignee "$user_upn" --role "Storage Blob Data Contributor" --scope "$scope" \
                2>/dev/null && log_success "    Storage role assigned" || log_warn "    Storage role assignment failed"
        fi
    fi

    log_success "RBAC assignment complete"
    log_warn "Note: New role assignments may take 5-10 minutes to propagate"
}

# ==============================================================================
# Step 5: Backend Setup
# ==============================================================================

setup_backend() {
    log_step "Step 5: Setting up Backend (src/backend)"

    cd "$BACKEND_DIR"

    # Handle existing .venv that may be locked
    if [[ -d ".venv" ]]; then
        if ! touch ".venv/.lock-test" 2>/dev/null; then
            log_warn ".venv is locked by another process (likely VS Code Python extension)."
            log_info "Attempting to auto-fix by killing locking Python processes..."

            VENV_ABS=$(cd .venv && pwd)
            # Find and kill python processes running from this venv
            LOCKING_PIDS=$(lsof +D "$VENV_ABS" 2>/dev/null | awk 'NR>1 {print $2}' | sort -u)
            if [[ -n "$LOCKING_PIDS" ]]; then
                for pid in $LOCKING_PIDS; do
                    log_info "  Killing PID $pid"
                    kill -9 "$pid" 2>/dev/null || true
                done
                sleep 2
            fi

            # Retry deletion
            if rm -rf ".venv" 2>/dev/null; then
                log_info "Removed locked .venv successfully."
            else
                log_warn "Still cannot remove .venv after killing processes."
                log_warn "Close VS Code completely and re-run the script."
                exit 1
            fi
        else
            rm -f ".venv/.lock-test"
            log_info "Existing virtual environment found, reusing it."
        fi
    fi

    # Create virtual environment if not exists
    if [[ ! -d ".venv" ]]; then
        log_info "Creating virtual environment..."
        uv venv .venv
    fi

    # Install dependencies
    log_info "Installing dependencies..."
    uv sync --python 3.12 --extra dev

    log_success "Backend setup complete"
    cd "$SCRIPT_DIR"
}

# ==============================================================================
# Step 6: MCP Server Setup
# ==============================================================================

setup_mcp_server() {
    log_step "Step 6: Setting up MCP Server (src/mcp_server)"

    cd "$MCP_DIR"

    # Create virtual environment
    if [[ ! -d ".venv" ]]; then
        log_info "Creating virtual environment..."
        uv venv .venv
    else
        log_info "Virtual environment already exists"
    fi

    # Install dependencies
    log_info "Installing dependencies..."
    uv sync --python 3.12

    log_success "MCP Server setup complete"
    cd "$SCRIPT_DIR"
}

# ==============================================================================
# Step 7: Frontend Setup
# ==============================================================================

setup_frontend() {
    log_step "Step 7: Setting up Frontend (src/App)"

    cd "$FRONTEND_DIR"

    # Python venv for frontend server
    if [[ ! -d ".venv" ]]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv .venv
    else
        log_info "Python virtual environment already exists"
    fi

    # Install Python dependencies
    log_info "Installing Python dependencies..."
    source .venv/bin/activate 2>/dev/null || . .venv/bin/activate
    pip install -q -r requirements.txt
    deactivate 2>/dev/null || true

    # Install Node.js dependencies
    if [[ ! -d "node_modules" ]]; then
        log_info "Installing npm dependencies..."
        npm install
    else
        log_info "node_modules already exists, running npm install to update..."
        npm install
    fi

    # Build the frontend
    log_info "Building frontend..."
    npm run build

    log_success "Frontend setup complete"
    cd "$SCRIPT_DIR"
}

# ==============================================================================
# Step 8: VS Code Configuration
# ==============================================================================

setup_vscode() {
    if [[ "$SKIP_VSCODE" == true ]]; then
        return 0
    fi

    log_step "Step 8: Configuring VS Code"

    mkdir -p "$SCRIPT_DIR/.vscode"

    # extensions.json
    if [[ ! -f "$SCRIPT_DIR/.vscode/extensions.json" ]]; then
        cat > "$SCRIPT_DIR/.vscode/extensions.json" << 'EOF'
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
EOF
        log_success "Created .vscode/extensions.json"
    else
        log_info ".vscode/extensions.json already exists"
    fi

    # settings.json
    if [[ ! -f "$SCRIPT_DIR/.vscode/settings.json" ]]; then
        cat > "$SCRIPT_DIR/.vscode/settings.json" << 'EOF'
{
    "python.defaultInterpreterPath": "${workspaceFolder}/src/backend/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.debugging.logLevel": "Debug",
    "debug.terminal.clearBeforeReusing": true,
    "debug.onTaskErrors": "showErrors",
    "debug.showBreakpointsInOverviewRuler": true,
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
EOF
        log_success "Created .vscode/settings.json"
    else
        log_info ".vscode/settings.json already exists"
    fi

    log_success "VS Code configuration complete"
}

# ==============================================================================
# Step 9: Summary & Run Instructions
# ==============================================================================

print_summary() {
    log_step "Setup Complete! 🎉"

    echo -e "${GREEN}All services have been set up successfully.${NC}"
    echo ""
    echo -e "${CYAN}To start the application, open 3 separate terminal windows:${NC}"
    echo ""
    echo -e "  ${YELLOW}Terminal 1 - Backend (port 8000):${NC}"
    echo "    cd src/backend"
    echo "    source .venv/bin/activate"
    echo "    python app.py"
    echo ""
    echo -e "  ${YELLOW}Terminal 2 - MCP Server (port 9000):${NC}"
    echo "    cd src/mcp_server"
    echo "    source .venv/bin/activate"
    echo "    python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 9000"
    echo ""
    echo -e "  ${YELLOW}Terminal 3 - Frontend (port 3000):${NC}"
    echo "    cd src/App"
    echo "    source .venv/bin/activate"
    echo "    python frontend_server.py"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}Application URL:${NC} http://localhost:3000"
    echo -e "  ${GREEN}Backend API:${NC}    http://localhost:8000"
    echo -e "  ${GREEN}API Docs:${NC}       http://localhost:8000/docs"
    echo -e "  ${GREEN}MCP Server:${NC}     http://localhost:9000"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ "$ASSIGN_RBAC" == true ]]; then
        log_warn "RBAC roles were assigned. Wait 5-10 minutes for propagation before testing."
    fi

    # Quick-start helper script
    create_start_script
}

create_start_script() {
    local start_script="$SCRIPT_DIR/start_all_services.sh"

    cat > "$start_script" << 'EOF'
#!/usr/bin/env bash
# Quick-start script: launches all 3 MACAE services in background
# Use: ./start_all_services.sh
# Stop: ./start_all_services.sh stop

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

stop_services() {
    echo -e "${YELLOW}Stopping MACAE services...${NC}"
    for pidfile in "$SCRIPT_DIR"/.macae_*.pid; do
        if [[ -f "$pidfile" ]]; then
            local pid
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                echo -e "${GREEN}Stopped PID $pid${NC}"
            fi
            rm -f "$pidfile"
        fi
    done
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

if [[ "${1:-}" == "stop" ]]; then
    stop_services
fi

echo -e "${GREEN}Starting MACAE services...${NC}"

# Backend
cd "$SCRIPT_DIR/src/backend"
source .venv/bin/activate
python app.py &
echo $! > "$SCRIPT_DIR/.macae_backend.pid"
echo -e "  ${GREEN}Backend${NC} started (PID: $!)"
deactivate 2>/dev/null || true

# MCP Server
cd "$SCRIPT_DIR/src/mcp_server"
source .venv/bin/activate
python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 9000 &
echo $! > "$SCRIPT_DIR/.macae_mcp.pid"
echo -e "  ${GREEN}MCP Server${NC} started (PID: $!)"
deactivate 2>/dev/null || true

# Frontend
cd "$SCRIPT_DIR/src/App"
source .venv/bin/activate
python frontend_server.py &
echo $! > "$SCRIPT_DIR/.macae_frontend.pid"
echo -e "  ${GREEN}Frontend${NC} started (PID: $!)"
deactivate 2>/dev/null || true

cd "$SCRIPT_DIR"

echo ""
echo -e "${GREEN}All services running!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  MCP:      http://localhost:9000"
echo -e "  Frontend: http://localhost:3000"
echo ""
echo -e "To stop: ${YELLOW}./start_all_services.sh stop${NC}"
EOF

    chmod +x "$start_script"
    log_success "Created start_all_services.sh (quick-start helper)"
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     MACAE - Local Development Setup                        ║"
    echo "║     Multi-Agent Custom Automation Engine                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    parse_args "$@"

    # Verify we're in the repo root
    if [[ ! -f "$SCRIPT_DIR/src/backend/app.py" ]]; then
        log_error "This script must be run from the repository root directory"
        log_error "Expected to find: src/backend/app.py"
        exit 1
    fi

    check_prerequisites
    check_azure_auth
    fetch_configuration
    assign_rbac_roles
    setup_backend
    setup_mcp_server
    setup_frontend
    setup_vscode
    print_summary
}

main "$@"

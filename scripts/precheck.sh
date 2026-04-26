#!/usr/bin/env bash
# =============================================================================
# Deployment Pre-Check Script (Bash/Posix)
# =============================================================================
# This script runs as a preprovision hook during 'azd up' to validate that
# all prerequisites are met before provisioning begins.
#
# It checks:
#   1. Environment detection (Local, Codespace, Dev Container)
#   2. Required CLI tools and versions (azd, az, bicep, python, npm, node, jq)
#   3. Azure authentication (logged in, subscription accessible)
#   4. azd environment variables (AZURE_LOCATION, AZURE_ENV_OPENAI_LOCATION)
#   5. Allowed Azure region validation
#   6. Hook script existence (prepackage, postdeploy scripts)
#   7. Azure OpenAI model quota availability
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed (details printed)
# =============================================================================

set -o pipefail

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── State ────────────────────────────────────────────────────────────────────
ERRORS=()
WARNINGS=()
ENVIRONMENT="Local"

# ── Allowed regions (from main.bicep) ────────────────────────────────────────
ALLOWED_LOCATIONS=("australiaeast" "centralus" "eastasia" "eastus2" "japaneast" "northeurope" "southeastasia" "uksouth")
ALLOWED_AI_LOCATIONS=("australiaeast" "eastus2" "francecentral" "japaneast" "norwayeast" "swedencentral" "uksouth" "westus")

# ── Helper functions ─────────────────────────────────────────────────────────

add_error() {
  ERRORS+=("$1")
}

add_warning() {
  WARNINGS+=("$1")
}

print_header() {
  printf "\n${YELLOW}===============================================================${NC}\n"
  printf "${GREEN} %s${NC}\n" "$1"
  printf "${YELLOW}===============================================================${NC}\n\n"
}

print_section() {
  printf "${CYAN}── %s ──${NC}\n" "$1"
}

print_ok() {
  printf "  ${GREEN}✅ %s${NC}\n" "$1"
}

print_fail() {
  printf "  ${RED}❌ %s${NC}\n" "$1"
}

print_warn() {
  printf "  ${YELLOW}⚠️  %s${NC}\n" "$1"
}

print_info() {
  printf "  ${BLUE}ℹ️  %s${NC}\n" "$1"
}

# Compare semver: returns 0 if $1 >= $2
version_gte() {
  local v1="$1" v2="$2"
  # Sort versions and check if the first is the smaller one
  if [ "$(printf '%s\n%s' "$v1" "$v2" | sort -V | head -n1)" = "$v2" ]; then
    return 0
  else
    return 1
  fi
}

# ── Detect environment ───────────────────────────────────────────────────────

detect_environment() {
  print_section "Environment Detection"

  if [ -n "${CODESPACES:-}" ] || [ "${CLOUDENV_ENVIRONMENT_ID:-}" != "" ]; then
    ENVIRONMENT="Codespace"
    print_ok "Running in GitHub Codespaces"
  elif [ -n "${REMOTE_CONTAINERS:-}" ] || [ -f "/.dockerenv" ] || [ -n "${DEVCONTAINER:-}" ] || grep -q "devcontainer" /proc/1/cgroup 2>/dev/null; then
    ENVIRONMENT="DevContainer"
    print_ok "Running in Dev Container"
  else
    ENVIRONMENT="Local"
    print_ok "Running in Local environment"
  fi
  printf "\n"
}

# ── Check CLI tools ──────────────────────────────────────────────────────────

check_tool_exists() {
  local tool="$1"
  local display_name="${2:-$1}"
  local required="${3:-true}"

  if command -v "$tool" &>/dev/null; then
    return 0
  else
    if [ "$required" = "true" ]; then
      add_error "$display_name is not installed. Please install it before deploying."
      print_fail "$display_name is not installed"
    else
      add_warning "$display_name is not installed. Some features may not work."
      print_warn "$display_name is not installed (optional)"
    fi
    return 1
  fi
}

check_azd() {
  print_section "Azure Developer CLI (azd)"

  if ! check_tool_exists "azd" "Azure Developer CLI (azd)"; then
    add_error "Install azd: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd"
    return
  fi

  local azd_version
  azd_version=$(azd version --output json 2>/dev/null | grep -oP '"azd\.version"\s*:\s*"\K[^"]+' 2>/dev/null || azd version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)

  if [ -n "$azd_version" ]; then
    if version_gte "$azd_version" "1.18.0"; then
      print_ok "azd version $azd_version (>= 1.18.0 required)"
    else
      add_error "azd version $azd_version is too old. Version >= 1.18.0 is required. Update: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd"
      print_fail "azd version $azd_version is below the minimum required 1.18.0"
    fi
  else
    print_warn "Could not determine azd version"
    add_warning "Could not determine azd version. Ensure >= 1.18.0."
  fi
  printf "\n"
}

check_azure_cli() {
  print_section "Azure CLI (az)"

  if ! check_tool_exists "az" "Azure CLI (az)"; then
    add_error "Install Azure CLI: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    return
  fi

  local az_version
  az_version=$(az version --output json 2>/dev/null | grep -oP '"azure-cli"\s*:\s*"\K[^"]+' 2>/dev/null || az --version 2>/dev/null | head -1 | grep -oP '\d+\.\d+\.\d+')

  if [ -n "$az_version" ]; then
    print_ok "Azure CLI version $az_version"
  fi

  # Check login status
  if az account show &>/dev/null; then
    local account_name
    account_name=$(az account show --query "name" -o tsv 2>/dev/null)
    local sub_id
    sub_id=$(az account show --query "id" -o tsv 2>/dev/null)
    print_ok "Logged in to Azure (subscription: $account_name)"
  else
    add_error "Not logged in to Azure CLI. Run 'az login' to authenticate."
    print_fail "Not logged in to Azure CLI"
  fi
  printf "\n"
}

check_bicep() {
  print_section "Bicep CLI"

  local bicep_version
  bicep_version=$(az bicep version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)

  if [ -n "$bicep_version" ]; then
    if version_gte "$bicep_version" "0.33.0"; then
      print_ok "Bicep version $bicep_version (>= 0.33.0 required)"
    else
      add_error "Bicep version $bicep_version is too old. Version >= 0.33.0 is required. Run 'az bicep upgrade' to update."
      print_fail "Bicep version $bicep_version is below the minimum required 0.33.0"
    fi
  else
    # Try installing bicep
    print_warn "Bicep not found or version could not be determined. Attempting install..."
    if az bicep install &>/dev/null; then
      bicep_version=$(az bicep version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
      if [ -n "$bicep_version" ]; then
        print_ok "Bicep installed: version $bicep_version"
      fi
    else
      add_error "Bicep CLI is not installed and auto-install failed. Run 'az bicep install' manually."
      print_fail "Bicep CLI is not available"
    fi
  fi
  printf "\n"
}

check_python() {
  print_section "Python"

  local python_cmd=""
  if command -v python3 &>/dev/null; then
    python_cmd="python3"
  elif command -v python &>/dev/null; then
    python_cmd="python"
  fi

  if [ -n "$python_cmd" ]; then
    local py_version
    py_version=$($python_cmd --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
    print_ok "Python $py_version ($python_cmd)"
  else
    add_error "Python is not installed. Python 3.x is required for backend and frontend services."
    print_fail "Python is not installed"
  fi

  # Check pip
  if command -v pip &>/dev/null || command -v pip3 &>/dev/null; then
    print_ok "pip is available"
  else
    add_warning "pip is not available. It may be needed for frontend packaging."
    print_warn "pip is not available"
  fi
  printf "\n"
}

check_node() {
  print_section "Node.js & npm"

  if check_tool_exists "node" "Node.js"; then
    local node_version
    node_version=$(node --version 2>/dev/null)
    print_ok "Node.js $node_version"
  fi

  if check_tool_exists "npm" "npm"; then
    local npm_version
    npm_version=$(npm --version 2>/dev/null)
    print_ok "npm $npm_version"
  fi
  printf "\n"
}

check_jq() {
  print_section "jq (JSON processor)"

  if check_tool_exists "jq" "jq" "true"; then
    local jq_version
    jq_version=$(jq --version 2>/dev/null)
    print_ok "jq $jq_version"
  else
    add_error "jq is required for quota validation scripts. Install: https://jqlang.github.io/jq/download/"
  fi
  printf "\n"
}

check_docker() {
  print_section "Docker"

  # Docker is managed in Codespace/DevContainer, only critical for local
  if [ "$ENVIRONMENT" = "Local" ]; then
    if check_tool_exists "docker" "Docker" "false"; then
      if docker info &>/dev/null; then
        print_ok "Docker is running"
      else
        add_warning "Docker is installed but the daemon is not running. It may be needed for container builds."
        print_warn "Docker daemon is not running"
      fi
    fi
  else
    if command -v docker &>/dev/null; then
      print_ok "Docker is available (managed by $ENVIRONMENT)"
    else
      print_info "Docker check skipped ($ENVIRONMENT environment)"
    fi
  fi
  printf "\n"
}

# ── Check azd environment variables ─────────────────────────────────────────

check_azd_env() {
  print_section "azd Environment Variables"

  local has_env=false

  # Check if azd env exists
  if azd env list &>/dev/null; then
    local env_name
    env_name=$(azd env list --output json 2>/dev/null | grep -oP '"Name"\s*:\s*"\K[^"]+' | head -1)
    if [ -z "$env_name" ]; then
      env_name=$(azd env get-values 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"' 2>/dev/null)
    fi

    if [ -n "$env_name" ]; then
      print_ok "azd environment is configured"
      has_env=true
    fi
  fi

  if [ "$has_env" = false ]; then
    add_warning "No azd environment detected. 'azd up' will prompt you to create one."
    print_warn "No azd environment detected (will be created during 'azd up')"
    printf "\n"
    return
  fi

  # Validate AZURE_LOCATION
  local azure_location
  azure_location=$(azd env get-value AZURE_LOCATION 2>/dev/null || echo "")

  if [ -n "$azure_location" ]; then
    local location_lower
    location_lower=$(echo "$azure_location" | tr '[:upper:]' '[:lower:]')
    local location_valid=false
    for loc in "${ALLOWED_LOCATIONS[@]}"; do
      if [ "$location_lower" = "$loc" ]; then
        location_valid=true
        break
      fi
    done

    if [ "$location_valid" = true ]; then
      print_ok "AZURE_LOCATION=$azure_location (valid)"
    else
      add_error "AZURE_LOCATION='$azure_location' is not a supported region. Allowed regions: ${ALLOWED_LOCATIONS[*]}. Fix: azd env set AZURE_LOCATION '<valid_region>'"
      print_fail "AZURE_LOCATION='$azure_location' is not in the allowed list"
    fi
  else
    print_info "AZURE_LOCATION is not set (will be prompted during 'azd up')"
  fi

  # Validate AZURE_ENV_OPENAI_LOCATION
  local openai_location
  openai_location=$(azd env get-value AZURE_ENV_OPENAI_LOCATION 2>/dev/null || echo "")

  if [ -n "$openai_location" ]; then
    local ai_loc_lower
    ai_loc_lower=$(echo "$openai_location" | tr '[:upper:]' '[:lower:]')
    local ai_location_valid=false
    for loc in "${ALLOWED_AI_LOCATIONS[@]}"; do
      if [ "$ai_loc_lower" = "$loc" ]; then
        ai_location_valid=true
        break
      fi
    done

    if [ "$ai_location_valid" = true ]; then
      print_ok "AZURE_ENV_OPENAI_LOCATION=$openai_location (valid)"
    else
      add_error "AZURE_ENV_OPENAI_LOCATION='$openai_location' is not a supported Azure AI region. Allowed regions: ${ALLOWED_AI_LOCATIONS[*]}. Fix: azd env set AZURE_ENV_OPENAI_LOCATION '<valid_region>'"
      print_fail "AZURE_ENV_OPENAI_LOCATION='$openai_location' is not in the allowed list"
    fi
  else
    print_info "AZURE_ENV_OPENAI_LOCATION is not set (will use default or be prompted)"
  fi

  # Check optional but important env vars and warn if they look problematic
  local model_deployment_type
  model_deployment_type=$(azd env get-value AZURE_ENV_MODEL_DEPLOYMENT_TYPE 2>/dev/null || echo "")
  if [ -n "$model_deployment_type" ]; then
    if [ "$model_deployment_type" != "Standard" ] && [ "$model_deployment_type" != "GlobalStandard" ]; then
      add_error "AZURE_ENV_MODEL_DEPLOYMENT_TYPE='$model_deployment_type' is invalid. Must be 'Standard' or 'GlobalStandard'. Fix: azd env set AZURE_ENV_MODEL_DEPLOYMENT_TYPE 'GlobalStandard'"
      print_fail "AZURE_ENV_MODEL_DEPLOYMENT_TYPE='$model_deployment_type' is not valid"
    else
      print_ok "AZURE_ENV_MODEL_DEPLOYMENT_TYPE=$model_deployment_type (valid)"
    fi
  fi

  local model_41_deployment_type
  model_41_deployment_type=$(azd env get-value AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE 2>/dev/null || echo "")
  if [ -n "$model_41_deployment_type" ]; then
    if [ "$model_41_deployment_type" != "Standard" ] && [ "$model_41_deployment_type" != "GlobalStandard" ]; then
      add_error "AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE='$model_41_deployment_type' is invalid. Must be 'Standard' or 'GlobalStandard'. Fix: azd env set AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE 'GlobalStandard'"
      print_fail "AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE='$model_41_deployment_type' is not valid"
    else
      print_ok "AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE=$model_41_deployment_type (valid)"
    fi
  fi

  local reasoning_deployment_type
  reasoning_deployment_type=$(azd env get-value AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE 2>/dev/null || echo "")
  if [ -n "$reasoning_deployment_type" ]; then
    if [ "$reasoning_deployment_type" != "Standard" ] && [ "$reasoning_deployment_type" != "GlobalStandard" ]; then
      add_error "AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE='$reasoning_deployment_type' is invalid. Must be 'Standard' or 'GlobalStandard'. Fix: azd env set AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE 'GlobalStandard'"
      print_fail "AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE='$reasoning_deployment_type' is not valid"
    else
      print_ok "AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE=$reasoning_deployment_type (valid)"
    fi
  fi
  printf "\n"
}

# ── Check Azure subscription ────────────────────────────────────────────────

check_azure_subscription() {
  print_section "Azure Subscription"

  if ! az account show &>/dev/null; then
    # Already reported in check_azure_cli
    print_fail "Cannot validate subscription (not logged in)"
    printf "\n"
    return
  fi

  local sub_state
  sub_state=$(az account show --query "state" -o tsv 2>/dev/null)
  if [ "$sub_state" = "Enabled" ]; then
    print_ok "Subscription is active (state: Enabled)"
  else
    add_error "Azure subscription state is '$sub_state'. An active (Enabled) subscription is required."
    print_fail "Subscription state: $sub_state (expected: Enabled)"
  fi

  # Check if user has at minimum resource group creation ability
  local sub_id
  sub_id=$(az account show --query "id" -o tsv 2>/dev/null)
  if [ -n "$sub_id" ]; then
    print_ok "Subscription ID: $sub_id"
  fi
  printf "\n"
}

# ── Check hook scripts exist ────────────────────────────────────────────────

check_hook_scripts() {
  print_section "Deployment Hook Scripts"

  local scripts_to_check=(
    "infra/scripts/package_frontend.sh:Frontend prepackage hook (bash)"
    "infra/scripts/package_frontend.ps1:Frontend prepackage hook (PowerShell)"
    "infra/scripts/selecting_team_config_and_data.sh:Post-deploy team config script (bash)"
    "infra/scripts/Selecting-Team-Config-And-Data.ps1:Post-deploy team config script (PowerShell)"
    "infra/scripts/validate_model_quota.sh:Model quota validation (bash)"
    "infra/scripts/validate_model_quota.ps1:Model quota validation (PowerShell)"
    "infra/scripts/validate_model_deployment_quota.sh:Model deployment quota validation (bash)"
    "infra/scripts/validate_model_deployment_quotas.ps1:Model deployment quota validation (PowerShell)"
  )

  for entry in "${scripts_to_check[@]}"; do
    local script_path="${entry%%:*}"
    local description="${entry##*:}"

    if [ -f "$script_path" ]; then
      print_ok "$description exists ($script_path)"
    else
      add_warning "$description not found at $script_path"
      print_warn "$description not found ($script_path)"
    fi
  done
  printf "\n"
}

# ── Check model quota (optional, runs if Azure is authenticated) ─────────

check_model_quota() {
  print_section "Azure OpenAI Model Quota (Optional)"

  # Only run quota check if we have all prerequisites
  if ! az account show &>/dev/null; then
    print_info "Skipping quota check (not logged in to Azure)"
    printf "\n"
    return
  fi

  if ! command -v jq &>/dev/null; then
    print_info "Skipping quota check (jq not installed)"
    printf "\n"
    return
  fi

  local openai_location
  openai_location=$(azd env get-value AZURE_ENV_OPENAI_LOCATION 2>/dev/null || echo "")

  if [ -z "$openai_location" ]; then
    print_info "Skipping quota check (AZURE_ENV_OPENAI_LOCATION not set)"
    printf "\n"
    return
  fi

  local sub_id
  sub_id=$(az account show --query "id" -o tsv 2>/dev/null)

  if [ -z "$sub_id" ]; then
    print_info "Skipping quota check (could not determine subscription ID)"
    printf "\n"
    return
  fi

  print_info "Checking Azure OpenAI model quota in '$openai_location'..."
  print_info "This may take a moment..."

  # Check quota for default models: gpt-4.1-mini (50), gpt-4.1 (150), o4-mini (50)
  local models=("gpt-4.1-mini:50:GlobalStandard" "gpt-4.1:150:GlobalStandard" "o4-mini:50:GlobalStandard")
  local quota_errors=()

  for model_info in "${models[@]}"; do
    local model_name="${model_info%%:*}"
    local remaining="${model_info#*:}"
    local capacity="${remaining%%:*}"
    local deployment_type="${remaining##*:}"
    local model_type="OpenAI.$deployment_type.$model_name"

    local model_data
    model_data=$(az cognitiveservices usage list --location "$openai_location" --query "[?name.value=='$model_type']" --output json 2>/dev/null)

    if [ -n "$model_data" ] && [ "$model_data" != "[]" ]; then
      local current_value
      current_value=$(echo "$model_data" | jq -r '.[0].currentValue // 0' | cut -d'.' -f1)
      local limit
      limit=$(echo "$model_data" | jq -r '.[0].limit // 0' | cut -d'.' -f1)
      local available=$((limit - current_value))

      if [ "$available" -ge "$capacity" ]; then
        print_ok "$model_name: $available available (need $capacity) in $openai_location"
      else
        quota_errors+=("$model_name: only $available available but $capacity required in $openai_location")
        print_fail "$model_name: insufficient quota ($available available, $capacity required)"
      fi
    else
      print_warn "$model_name: could not retrieve quota info for $openai_location"
    fi
  done

  if [ ${#quota_errors[@]} -gt 0 ]; then
    add_error "Insufficient Azure OpenAI model quota. Details:"
    for qe in "${quota_errors[@]}"; do
      add_error "  - $qe"
    done
    add_error "Request quota increase: https://aka.ms/oai/stuquotarequest or try a different region: azd env set AZURE_ENV_OPENAI_LOCATION '<region>'"
  fi
  printf "\n"
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  print_header "DEPLOYMENT PRE-CHECK RUNNER"

  printf "${BOLD}Running deployment pre-checks to ensure a smooth deployment...${NC}\n\n"

  detect_environment
  check_azd
  check_azure_cli
  check_bicep
  check_python
  check_node
  check_jq
  check_docker
  check_azure_subscription
  check_azd_env
  check_hook_scripts
  check_model_quota

  # ── Summary ──────────────────────────────────────────────────────────────

  printf "\n"
  print_header "PRE-CHECK SUMMARY"

  printf "  ${BOLD}Environment:${NC} $ENVIRONMENT\n\n"

  if [ ${#WARNINGS[@]} -gt 0 ]; then
    printf "  ${YELLOW}${BOLD}Warnings (${#WARNINGS[@]}):${NC}\n"
    for warning in "${WARNINGS[@]}"; do
      printf "    ${YELLOW}⚠️  %s${NC}\n" "$warning"
    done
    printf "\n"
  fi

  if [ ${#ERRORS[@]} -gt 0 ]; then
    printf "  ${RED}${BOLD}Errors (${#ERRORS[@]}):${NC}\n"
    printf "  ${RED}The following issues must be resolved before deployment can proceed:${NC}\n\n"
    local idx=1
    for error in "${ERRORS[@]}"; do
      printf "    ${RED}%d. %s${NC}\n" "$idx" "$error"
      ((idx++))
    done
    printf "\n"
    printf "  ${RED}${BOLD}❌ Pre-checks FAILED. Please fix the above errors and retry 'azd up'.${NC}\n\n"
    exit 1
  else
    printf "  ${GREEN}${BOLD}✅ All pre-checks PASSED. Deployment can proceed.${NC}\n\n"
    exit 0
  fi
}

main "$@"

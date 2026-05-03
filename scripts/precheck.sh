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

  # Docker is required in Codespace/DevContainer environments where containers
  # back the dev workflow. On Local (host) machines we skip the check because
  # Docker is not needed for 'azd up' itself.
  if [ "$ENVIRONMENT" = "Local" ]; then
    print_info "Docker check skipped (Local environment)"
  else
    if command -v docker &>/dev/null; then
      if docker info &>/dev/null; then
        print_ok "Docker is running (managed by $ENVIRONMENT)"
      else
        add_warning "Docker is installed but the daemon is not running in $ENVIRONMENT. It may be needed for container builds."
        print_warn "Docker daemon is not running"
      fi
    else
      add_warning "Docker is not installed in $ENVIRONMENT. It may be needed for container builds."
      print_warn "Docker is not installed"
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

# ── Check tenant match (TroubleShootingSteps: CrossTenantDeploymentNotPermitted)
# Catches two foot-guns:
#   1. Subscription tenantId != homeTenantId (cross-tenant subscription).
#   2. Signed-in user is a Guest in the subscription's tenant.
check_tenant_match() {
  print_section "Azure Tenant Match"

  if ! az account show &>/dev/null; then
    print_info "Skipping tenant match check (not logged in to Azure)"
    printf "\n"
    return
  fi

  local tenant_id home_tenant_id
  tenant_id=$(az account show --query "tenantId" -o tsv 2>/dev/null)
  home_tenant_id=$(az account show --query "homeTenantId" -o tsv 2>/dev/null)

  if [ -n "$tenant_id" ] && [ -n "$home_tenant_id" ] && [ "$tenant_id" != "$home_tenant_id" ]; then
    print_warn "Subscription tenant ($tenant_id) differs from its home tenant ($home_tenant_id)."
    print_info "  This is a cross-tenant subscription and may trigger 'CrossTenantDeploymentNotPermitted'."
    add_warning "Subscription is cross-tenant (tenantId != homeTenantId). Deployment may fail with CrossTenantDeploymentNotPermitted."
  else
    print_ok "Subscription tenant matches its home tenant ($tenant_id)"
  fi

  local user_type
  user_type=$(az ad signed-in-user show --query userType -o tsv 2>/dev/null || true)

  # Graph returns userType=null for many native Member accounts; only an
  # explicit "Guest" string indicates an external/guest identity.
  if [ "$user_type" = "Guest" ]; then
    local upn
    upn=$(az account show --query "user.name" -o tsv 2>/dev/null)
    print_warn "Signed-in user '$upn' is a Guest in tenant $tenant_id."
    print_info "  Guest accounts often lack directory permissions required by 'azd up' (role assignments, app registrations)."
    add_warning "Signed-in user is a Guest in the subscription's tenant; deployment may fail on role assignment or app-registration steps."
  else
    print_ok "Signed-in user is a Member of tenant $tenant_id"
  fi

  printf "\n"
}

# ── Check subscription role assignments (DeploymentGuide §1.1) ──────────────
# Roles required to deploy this solution end-to-end. Owner satisfies all.
# Informational (warnings only) because callers may rely on inherited
# Management Group assignments not visible at subscription scope.

check_azure_roles() {
  print_section "Azure RBAC Roles (DeploymentGuide §1.1)"

  if ! az account show &>/dev/null; then
    print_info "Skipping role check (not logged in to Azure)"
    printf "\n"
    return
  fi

  local sub_id
  sub_id=$(az account show --query "id" -o tsv 2>/dev/null)

  # Resolve caller object id (user, SPN, or managed identity)
  local caller_oid
  caller_oid=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)
  if [ -z "$caller_oid" ]; then
    caller_oid=$(az account show --query "user.name" -o tsv 2>/dev/null || true)
  fi

  if [ -z "$caller_oid" ]; then
    print_warn "Could not determine signed-in identity object id; skipping role enumeration."
    add_warning "Unable to verify subscription RBAC roles (could not resolve signed-in identity)."
    printf "\n"
    return
  fi

  local scope="/subscriptions/$sub_id"
  local roles_json
  roles_json=$(az role assignment list --assignee "$caller_oid" --scope "$scope" --include-inherited --include-groups --output json 2>/dev/null || true)

  if [ -z "$roles_json" ] || [ "$roles_json" = "[]" ]; then
    print_warn "Could not list role assignments for the signed-in identity at subscription scope."
    print_info "If 'azd up' fails with authorization errors, request 'Contributor' + 'User Access Administrator' (or 'Owner') on subscription $sub_id."
    add_warning "Unable to verify subscription RBAC roles (insufficient permission or no assignments found)."
    printf "\n"
    return
  fi

  local role_names
  if command -v jq &>/dev/null; then
    role_names=$(echo "$roles_json" | jq -r '.[].roleDefinitionName')
  else
    # Crude fallback parse
    role_names=$(echo "$roles_json" | grep -oE '"roleDefinitionName"\s*:\s*"[^"]+"' | sed -E 's/.*"([^"]+)"$/\1/')
  fi

  local has_owner=false has_contributor=false has_access_admin=false
  while IFS= read -r r; do
    [ -z "$r" ] && continue
    case "$r" in
      "Owner") has_owner=true ;;
      "Contributor") has_contributor=true ;;
      "User Access Administrator"|"Role Based Access Control Administrator") has_access_admin=true ;;
    esac
  done <<< "$role_names"

  if [ "$has_owner" = true ]; then
    print_ok "'Owner' role assigned (covers all required permissions)"
  else
    if [ "$has_contributor" = true ]; then
      print_ok "'Contributor' assigned (Create and manage Azure resources)"
    else
      print_warn "'Contributor' not found (Create and manage Azure resources)"
    fi
    if [ "$has_access_admin" = true ]; then
      print_ok "'User Access Administrator' or 'Role Based Access Control Administrator' assigned"
    else
      print_warn "Neither 'User Access Administrator' nor 'Role Based Access Control Administrator' found (Manage RBAC)"
    fi

    if [ "$has_contributor" != true ] || [ "$has_access_admin" != true ]; then
      add_warning "Signed-in identity is missing one or more required roles at subscription scope ($sub_id). Required: 'Contributor' + ('User Access Administrator' or 'Role Based Access Control Administrator'), or 'Owner'."
      print_info "Request the missing roles or have an Owner run 'azd up'. See DeploymentGuide §1.1."
    fi
  fi
  printf "\n"
}

# ── Check App Registration creation permission (DeploymentGuide §1.1) ──────

APP_CREATOR_ROLES=("Global Administrator" "Application Administrator" "Application Developer" "Cloud Application Administrator")

check_app_registration_permission() {
  print_section "App Registration Permission (DeploymentGuide §1.1)"

  if ! az account show &>/dev/null; then
    print_info "Skipping app registration check (not logged in to Azure)"
    printf "\n"
    return
  fi

  # Skip for service principals / managed identities
  local user_type user_name
  user_type=$(az account show --query "user.type" -o tsv 2>/dev/null || true)
  user_name=$(az account show --query "user.name" -o tsv 2>/dev/null || echo "current user")
  if [ -n "$user_type" ] && [ "$user_type" != "user" ]; then
    print_info "Signed in as '$user_type'; skipping interactive app registration check."
    printf "\n"
    return
  fi

  # Path 1: Caller holds a directory role that explicitly grants app creation.
  local roles_granting=() member_readable=false
  local member_json
  member_json=$(az rest --method GET --url "https://graph.microsoft.com/v1.0/me/memberOf?\$select=id,displayName" --output json 2>/dev/null || true)
  if [ -n "$member_json" ] && command -v jq &>/dev/null; then
    member_readable=true
    while IFS= read -r role_name; do
      [ -z "$role_name" ] && continue
      for granting in "${APP_CREATOR_ROLES[@]}"; do
        if [ "$role_name" = "$granting" ]; then
          roles_granting+=("$role_name")
          break
        fi
      done
    done < <(echo "$member_json" | jq -r '.value[] | select(."@odata.type"=="#microsoft.graph.directoryRole") | .displayName')
  fi

  if [ ${#roles_granting[@]} -gt 0 ]; then
    print_ok "$user_name can create app registrations via directory role: ${roles_granting[*]}"
    printf "\n"
    return
  fi

  # Path 2: Tenant default permission lets every user create app registrations.
  local policy_json allowed_to_create=""
  policy_json=$(az rest --method GET --url "https://graph.microsoft.com/v1.0/policies/authorizationPolicy" --output json 2>/dev/null || true)
  if [ -n "$policy_json" ]; then
    if command -v jq &>/dev/null; then
      allowed_to_create=$(echo "$policy_json" | jq -r '.defaultUserRolePermissions.allowedToCreateApps // empty')
    else
      allowed_to_create=$(echo "$policy_json" | grep -oE '"allowedToCreateApps"\s*:\s*(true|false)' | head -n1 | grep -oE '(true|false)')
    fi
  fi

  if [ "$allowed_to_create" = "true" ]; then
    print_ok "$user_name can create app registrations (granted by tenant default user permissions)"
    printf "\n"
    return
  fi

  if [ "$allowed_to_create" = "false" ]; then
    print_warn "$user_name cannot create app registrations: tenant restricts creation to privileged roles and you do not hold any of: ${APP_CREATOR_ROLES[*]}."
    add_warning "App registration creation may be blocked for $user_name. If 'azd up' fails creating an Entra ID app, request 'Application Developer' (or higher) in the tenant. See DeploymentGuide §1.1."
  else
    if [ "$member_readable" = true ]; then
      print_warn "Could not verify app registration permission for $user_name (no granting directory role assigned and tenant default policy is not readable from this account)."
    else
      print_warn "Could not verify app registration permission for $user_name (insufficient Graph permission to inspect directory roles or tenant policy)."
    fi
    add_warning "Unable to verify app registration creation permission for $user_name. If 'azd up' fails creating an Entra ID app, request 'Application Developer' (or higher) in the tenant. See DeploymentGuide §1.1."
  fi
  printf "\n"
}

# ── Check resource providers are registered (DeploymentGuide §1.2) ──────────

REQUIRED_PROVIDERS=(
  "Microsoft.CognitiveServices"
  "Microsoft.Search"
  "Microsoft.App"
  "Microsoft.ContainerRegistry"
  "Microsoft.DocumentDB"
  "Microsoft.KeyVault"
  "Microsoft.Storage"
  "Microsoft.Web"
  "Microsoft.OperationalInsights"
  "Microsoft.Insights"
  "Microsoft.ManagedIdentity"
)

check_resource_providers() {
  print_section "Azure Resource Providers (DeploymentGuide §1.2)"

  if ! az account show &>/dev/null; then
    print_info "Skipping provider check (not logged in to Azure)"
    printf "\n"
    return
  fi

  local sub_id
  sub_id=$(az account show --query "id" -o tsv 2>/dev/null)
  local unregistered=()

  for ns in "${REQUIRED_PROVIDERS[@]}"; do
    local state
    state=$(az provider show --namespace "$ns" --query "registrationState" -o tsv 2>/dev/null || true)
    if [ "$state" = "Registered" ]; then
      print_ok "$ns is Registered"
    elif [ -n "$state" ]; then
      print_warn "$ns is '$state' (expected 'Registered')"
      unregistered+=("$ns")
    else
      print_warn "$ns: could not determine registration state"
      unregistered+=("$ns")
    fi
  done

  if [ ${#unregistered[@]} -gt 0 ]; then
    add_warning "The following resource providers are not 'Registered' on subscription $sub_id: ${unregistered[*]}. Register with: az provider register --namespace <Namespace>"
    print_info "To register all at once:"
    for ns in "${unregistered[@]}"; do
      printf "    az provider register --namespace %s\n" "$ns"
    done
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

# Path to the canonical bash quota check script (sibling of the PowerShell version)
QUOTA_CHECK_SCRIPT="infra/scripts/quota_check_params.sh"

check_model_quota() {
  print_section "Azure OpenAI Model Quota (Optional)"

  # Only run quota check if we have all prerequisites
  if ! az account show &>/dev/null; then
    print_info "Skipping quota check (not logged in to Azure)"
    printf "\n"
    return
  fi

  if [ ! -f "$QUOTA_CHECK_SCRIPT" ]; then
    print_warn "Quota check script not found at '$QUOTA_CHECK_SCRIPT'. Skipping."
    printf "\n"
    return
  fi

  # If the user has selected a specific region (env var or azd), pass it through.
  local regions_arg=""
  if [ -n "${AZURE_ENV_OPENAI_LOCATION:-}" ]; then
    regions_arg="$AZURE_ENV_OPENAI_LOCATION"
  else
    local azd_value
    azd_value=$(azd env get-value AZURE_ENV_OPENAI_LOCATION 2>/dev/null || true)
    if [ -n "$azd_value" ] && [[ "$azd_value" != ERROR* ]]; then
      regions_arg="$azd_value"
    fi
  fi

  print_info "Running '$QUOTA_CHECK_SCRIPT' (DeploymentGuide §1.3)..."
  if [ -n "$regions_arg" ]; then
    print_info "Targeting selected region: $regions_arg"
  else
    print_info "No region selected. Using script defaults (8 regions, 3 models)."
  fi
  printf "\n"

  # Pre-set AZURE_SUBSCRIPTION_ID so the script never prompts when multiple
  # subscriptions are enabled.
  local active_id
  active_id=$(az account show --query id -o tsv 2>/dev/null | tr -d '[:space:]')

  if [ -n "$regions_arg" ]; then
    AZURE_SUBSCRIPTION_ID="$active_id" bash "$QUOTA_CHECK_SCRIPT" --regions "$regions_arg" || true
  else
    AZURE_SUBSCRIPTION_ID="$active_id" bash "$QUOTA_CHECK_SCRIPT" || true
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
  check_tenant_match
  check_azure_roles
  check_app_registration_permission
  check_resource_providers
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

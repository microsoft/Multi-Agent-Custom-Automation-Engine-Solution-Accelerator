#!/usr/bin/env bash
# ==============================================================================
# MACAE - Deploy Local Code to Azure
# ==============================================================================
#
# Builds Docker images locally, pushes to ACR, and updates
# the deployed Azure resources (Container Apps / App Service).
#
# Usage:
#   ./deploy_to_azure.sh -g <resource-group> [options]
#
# Examples:
#   ./deploy_to_azure.sh -g rg-macae-dev                          # Deploy all services
#   ./deploy_to_azure.sh -g rg-macae-dev --services backend,mcp   # Deploy specific services
#   ./deploy_to_azure.sh -g rg-macae-dev --acr myacr              # Use specific ACR
#   ./deploy_to_azure.sh -g rg-macae-dev --dry-run                # Preview what would happen
# ==============================================================================

set -euo pipefail

# On Windows Git Bash (MSYS/MinGW), paths starting with / get converted to Windows
# paths when passed to native .exe programs. This breaks ARM resource IDs like
# /subscriptions/... but we NEED normal conversion for docker build context paths.
# Solution: wrap 'az' with MSYS_NO_PATHCONV=1 so only az calls skip conversion.
# See: https://github.com/Azure/azure-cli/issues/13009
az() { MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" command az "$@"; }

# Convert a path to Windows-native format for tools like docker.exe that need it.
# On non-MSYS systems (Linux/macOS) this is a no-op.
_winpath() {
    if command -v cygpath &>/dev/null; then
        cygpath -w "$1"
    else
        echo "$1"
    fi
}

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESOURCE_GROUP=""
ACR_INPUT=""
SERVICES=""
CUSTOM_TAG=""
DRY_RUN=false
BUILD_ONLY=false
DEPLOY_ONLY=false
SKIP_ROLE_ASSIGNMENT=false

# Image names (matching infra conventions)
BACKEND_IMAGE_NAME="macaebackend"
MCP_IMAGE_NAME="macaemcp"
FRONTEND_IMAGE_NAME="macaefrontend"

# Service paths
BACKEND_DIR="$REPO_ROOT/src/backend"
MCP_DIR="$REPO_ROOT/src/mcp_server"
FRONTEND_DIR="$REPO_ROOT/src/App"

# ==============================================================================
# Logging
# ==============================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[i]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
log_error()   { echo -e "${RED}[✗]${NC} $*"; }
log_step()    { echo -e "\n${CYAN}━━━ $* ━━━${NC}\n"; }

# Retry an az command up to 3 times on transient network errors
az_retry() {
    local attempt=1 out rc delay
    while [[ $attempt -le 4 ]]; do
        out=$(az "$@" 2>&1) && rc=0 || rc=$?
        if [[ $rc -eq 0 ]]; then echo "$out"; return 0; fi
        if echo "$out" | grep -qiE "OperationInProgress|ContainerAppOperation"; then
            delay=30
            log_warn "Azure operation in progress (attempt $attempt/4), retrying in ${delay}s..." >&2
        elif echo "$out" | grep -qiE "RemoteDisconnected|Connection aborted|timed out|ECONNRESET|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish"; then
            delay=15
            log_warn "Transient network error (attempt $attempt/4), retrying in ${delay}s..." >&2
        else
            echo "$out"; return $rc
        fi
        sleep $delay; (( attempt++ ))
    done
    echo "$out"; return $rc
}

# ==============================================================================
# Argument Parsing
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -g|--resource-group)
                RESOURCE_GROUP="$2"; shift 2 ;;
            --acr)
                ACR_INPUT="$2"; shift 2 ;;
            --services)
                SERVICES="$2"; shift 2 ;;
            --tag)
                CUSTOM_TAG="$2"; shift 2 ;;
            --dry-run)
                DRY_RUN=true; shift ;;
            --build-only)
                BUILD_ONLY=true; shift ;;
            --deploy-only)
                DEPLOY_ONLY=true; shift ;;
            --skip-role-assignment)
                SKIP_ROLE_ASSIGNMENT=true; shift ;;
            -h|--help)
                show_help; exit 0 ;;
            *)
                log_error "Unknown option: $1"; show_help; exit 1 ;;
        esac
    done
}

show_help() {
    cat <<EOF
MACAE - Deploy Local Code to Azure

Usage: ./deploy_to_azure.sh -g <resource-group> [options]

Required:
  -g, --resource-group <name>   Azure Resource Group name

Options:
  --acr <name>                  ACR name or login server (auto-discovers if not set)
  --services <list>             Comma-separated: backend,mcp,frontend (default: all)
  --tag <tag>                   Custom image tag (default: auto-generated)
  --dry-run                     Preview what would happen without making changes
  --build-only                  Build and push images only, don't update Azure resources
  --deploy-only                 Update Azure resources only (images must already exist)
  --skip-role-assignment        Skip AcrPull role assignment (use if roles already exist)
  -h, --help                    Show this help message

Examples:
  ./deploy_to_azure.sh -g rg-macae-dev
  ./deploy_to_azure.sh -g rg-macae-dev --services backend
  ./deploy_to_azure.sh -g rg-macae-dev --acr myregistry --tag v1.0
  ./deploy_to_azure.sh -g rg-macae-dev --dry-run
EOF
}

# ==============================================================================
# Prerequisites
# ==============================================================================

check_prerequisites() {
    log_step "Step 1: Checking Prerequisites"

    local missing=()

    if command -v az &>/dev/null; then
        log_success "Azure CLI found"
    else
        missing+=("azure-cli")
    fi

    if command -v docker &>/dev/null; then
        if docker info &>/dev/null; then
            log_success "Docker found and running"
        else
            log_error "Docker found but daemon not running. Please start Docker Desktop."
            exit 1
        fi
    else
        missing+=("docker")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing prerequisites: ${missing[*]}"
        echo ""
        for tool in "${missing[@]}"; do
            case "$tool" in
                azure-cli)
                    echo "  ┌─ Azure CLI ───────────────────────────────────────────────────"
                    echo "  │  Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
                    echo "  │  Verify: az --version"
                    echo "  └──────────────────────────────────────────────────────────────"
                    ;;
                docker)
                    echo "  ┌─ Docker Desktop ──────────────────────────────────────────────"
                    echo "  │  Install: https://www.docker.com/products/docker-desktop"
                    echo "  │  Verify: docker --version"
                    echo "  └──────────────────────────────────────────────────────────────"
                    ;;
            esac
        done
        exit 1
    fi

    # Check Azure login
    if ! az account show &>/dev/null; then
        log_warn "Not logged into Azure CLI. Running 'az login'..."
        az login
    fi
    log_success "Logged into Azure CLI"
}

# ==============================================================================
# Step 1b: Azure Role / Permission Check
# ==============================================================================
#
# Per docs/DeploymentGuide.md, the deploying account needs:
#   - Contributor (or Owner) on the subscription -- to update resources
#   - User Access Administrator OR Role Based Access Control Administrator
#     (or Owner) -- to assign the AcrPull role to managed identities
# This check is non-fatal: group-inherited roles may not always enumerate.
# ==============================================================================

check_azure_roles() {
    log_step "Step 1b: Checking Azure Roles & Permissions"

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
        log_warn "Required: Contributor + (User Access Administrator OR Role Based Access Control Administrator), or Owner."
        return
    fi

    local has_res_mgmt=false has_role_mgmt=false
    while IFS= read -r r; do
        case "$r" in
            Owner) has_res_mgmt=true; has_role_mgmt=true ;;
            Contributor) has_res_mgmt=true ;;
            "User Access Administrator"|"Role Based Access Control Administrator") has_role_mgmt=true ;;
        esac
    done <<< "$roles_raw"

    if $has_res_mgmt; then log_success "Resource management role found (Owner/Contributor)"
    else log_warn "Missing 'Contributor' (or 'Owner') at subscription scope -- Azure resource updates may fail."; fi

    if $has_role_mgmt; then log_success "Role-assignment permission found (Owner/UAA/RBAC Admin)"
    else log_warn "Missing 'User Access Administrator' / 'Role Based Access Control Administrator' (or 'Owner') -- AcrPull role assignment may fail. Pass --skip-role-assignment if roles are already in place."; fi
}

# ==============================================================================
# Step 2: Validate Resource Group & Discover Resources
# ==============================================================================

validate_and_discover() {
    log_step "Step 2: Discovering Azure Resources"

    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_error "Resource group is required. Use: -g <resource-group-name>"
        exit 1
    fi

    if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
        log_error "Resource group '$RESOURCE_GROUP' not found."
        exit 1
    fi
    log_success "Resource group: $RESOURCE_GROUP"

    # Discover backend container app
    local ca_list
    ca_list=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv 2>/dev/null || true)

    BACKEND_CA=""
    MCP_CA=""

    if [[ -n "$ca_list" ]]; then
        while IFS= read -r app; do
            app=$(echo "$app" | tr -d '\r')
            if [[ "$app" == ca-mcp-* ]]; then
                MCP_CA="$app"
            elif [[ "$app" == ca-* ]]; then
                BACKEND_CA="$app"
            fi
        done <<< "$ca_list"
    fi

    if [[ -n "$BACKEND_CA" ]]; then
        log_success "Backend Container App: $BACKEND_CA"
    else
        log_warn "Backend Container App: not found in RG"
    fi

    if [[ -n "$MCP_CA" ]]; then
        log_success "MCP Container App: $MCP_CA"
    else
        log_warn "MCP Container App: not found in RG"
    fi

    # Discover frontend web app
    FRONTEND_APP=""
    FRONTEND_APP=$(az webapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null | tr -d '\r' || true)

    if [[ -n "$FRONTEND_APP" ]]; then
        log_success "Frontend Web App: $FRONTEND_APP"
    else
        log_warn "Frontend Web App: not found in RG"
    fi

    # Capture current images for rollback
    if [[ -n "$BACKEND_CA" ]]; then
        OLD_BACKEND_IMAGE=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
            --query "properties.template.containers[0].image" -o tsv 2>/dev/null | tr -d '\r' || echo "unknown")
        log_info "Current backend image: $OLD_BACKEND_IMAGE"
    fi

    if [[ -n "$MCP_CA" ]]; then
        OLD_MCP_IMAGE=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
            --query "properties.template.containers[0].image" -o tsv 2>/dev/null | tr -d '\r' || echo "unknown")
        log_info "Current MCP image: $OLD_MCP_IMAGE"
    fi

    if [[ -n "$FRONTEND_APP" ]]; then
        OLD_FRONTEND_IMAGE=$(az webapp config show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" \
            --query "linuxFxVersion" -o tsv 2>/dev/null | tr -d '\r' || echo "unknown")
        log_info "Current frontend image: $OLD_FRONTEND_IMAGE"
    fi
}

# ==============================================================================
# Step 3: Resolve ACR
# ==============================================================================

# Resolve ACR resource ID reliably:
# 1. Try with --resource-group (fastest, most reliable for RG-scoped ACRs)
# 2. Try global lookup (for ACRs in a different RG)
# 3. Build from known parts as fallback (handles post-create propagation delay)
_get_acr_id() {
    local name="$1"
    local rg="${2:-$RESOURCE_GROUP}"
    local id
    id=$(az acr show --name "$name" --resource-group "$rg" --query "id" -o tsv 2>/dev/null | tr -d '\r' || true)
    if [[ -z "$id" ]]; then
        id=$(az acr show --name "$name" --query "id" -o tsv 2>/dev/null | tr -d '\r' || true)
    fi
    if [[ -z "$id" ]]; then
        local sub_id
        sub_id=$(az account show --query id -o tsv 2>/dev/null | tr -d '\r')
        id="/subscriptions/$sub_id/resourceGroups/$rg/providers/Microsoft.ContainerRegistry/registries/$name"
    fi
    echo "$id"
}

resolve_acr() {
    log_step "Step 3: Resolving Container Registry"

    if [[ -n "$ACR_INPUT" ]]; then
        # User provided ACR via --acr flag — normalize to name and login server
        local input="${ACR_INPUT%.azurecr.io}"
        ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[?name=='$input'].name | [0]" -o tsv 2>/dev/null | tr -d '\r' || true)
        if [[ -z "$ACR_NAME" ]]; then
            ACR_NAME=$(az acr show --name "$input" --query "name" -o tsv 2>/dev/null | tr -d '\r' || true)
        fi
        if [[ -z "$ACR_NAME" ]]; then
            log_error "ACR '$ACR_INPUT' not found or not accessible."
            exit 1
        fi
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv 2>/dev/null | tr -d '\r' || az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query "loginServer" -o tsv | tr -d '\r')
        ACR_ID=$(_get_acr_id "$ACR_NAME")
        log_success "Using specified ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"
        assign_acr_pull_roles
        return
    fi

    # Always ask first — no pre-discovery
    echo ""
    read -rp "Enter ACR name to use (or press Enter to see available ACRs / create new): " user_acr

    if [[ -n "$user_acr" ]]; then
        local input="${user_acr%.azurecr.io}"
        ACR_NAME=$(az acr show --name "$input" --query "name" -o tsv 2>/dev/null | tr -d '\r' || true)
        if [[ -z "$ACR_NAME" ]]; then
            log_error "ACR '$user_acr' not found or not accessible."
            exit 1
        fi
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query "loginServer" -o tsv 2>/dev/null | tr -d '\r' || az acr show --name "$ACR_NAME" --query "loginServer" -o tsv | tr -d '\r')
        ACR_ID=$(_get_acr_id "$ACR_NAME")
        log_success "Using ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"
        assign_acr_pull_roles
        return
    fi

    # Empty input — discover what's in the RG and auto-select or auto-create
    log_info "Looking for ACR(s) in resource group '$RESOURCE_GROUP'..."
    local found_acrs
    found_acrs=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv 2>/dev/null | tr -d '\r' || true)

    local chosen_acr
    chosen_acr=$(echo "$found_acrs" | head -1 | tr -d '[:space:]')

    if [[ -n "$chosen_acr" ]]; then
        ACR_NAME="$chosen_acr"
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query "loginServer" -o tsv | tr -d '\r')
        ACR_ID=$(_get_acr_id "$ACR_NAME")
        log_success "Found and using ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"
        assign_acr_pull_roles
    else
        # Create new ACR in the same RG
        local suffix
        suffix=$(echo "$RESOURCE_GROUP" | sed 's/[^a-zA-Z0-9]//g' | tail -c 15)
        local new_acr_name="acr${suffix}$(date +%s | tail -c 6)"
        new_acr_name=$(echo "$new_acr_name" | tr '[:upper:]' '[:lower:]' | head -c 50)

        log_info "Creating ACR: $new_acr_name in $RESOURCE_GROUP..."
        az acr create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$new_acr_name" \
            --sku Basic \
            --admin-enabled false \
            --output none

        ACR_NAME="$new_acr_name"
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query "loginServer" -o tsv | tr -d '\r')
        ACR_ID=$(_get_acr_id "$ACR_NAME")
        log_success "Created ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"
        assign_acr_pull_roles
    fi
}

# ==============================================================================
# ACR Pull Role Assignment
# ==============================================================================

_assign_one_role() {
    # _assign_one_role <identity> <label>
    # Returns 0 on success/already-assigned, 1 on failure
    local identity="${1//$'\r'/}" label="$2"
    local acr_scope="${ACR_ID//$'\r'/}"
    local existing
    existing=$(az role assignment list --assignee "$identity" --role "$_acr_pull_role" --scope "$acr_scope" --query "[0].id" -o tsv 2>/dev/null | tr -d '\r' || true)
    if [[ -z "$existing" ]]; then
        local create_output
        if create_output=$(az role assignment create --assignee "$identity" --role "$_acr_pull_role" --scope "$acr_scope" --output none 2>&1); then
            log_success "  AcrPull assigned to $label identity"
        else
            log_error "  Failed to assign AcrPull to $label identity"
            log_error "  Azure: $create_output"
            return 1
        fi
    else
        log_info "  AcrPull already assigned to $label identity ✓"
    fi
    return 0
}

assign_acr_pull_roles() {
    if [[ "$SKIP_ROLE_ASSIGNMENT" == true ]]; then
        log_info "Skipping AcrPull role assignment (--skip-role-assignment set)."
        return 0
    fi

    log_info "Assigning AcrPull role to service identities..."

    # Defensive strip: Windows az CLI can embed \r in captured values
    ACR_ID="${ACR_ID//$'\r'/}"

    if [[ -z "$ACR_ID" ]]; then
        log_error "ACR resource ID is empty — cannot assign roles. Aborting."
        exit 1
    fi

    _acr_pull_role="7f951dda-4ed3-4680-a7ca-43fe172d538d"  # AcrPull built-in role ID
    local any_failed=false

    # Backend Container App identity
    if [[ -n "$BACKEND_CA" ]]; then
        local backend_identity
        backend_identity=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
            --query "identity.principalId" -o tsv 2>/dev/null | tr -d '\r' || true)
        if [[ -z "$backend_identity" || "$backend_identity" == "null" ]]; then
            backend_identity=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
                --query "identity.userAssignedIdentities.*.principalId | [0]" -o tsv 2>/dev/null | tr -d '\r' || true)
        fi
        if [[ -n "$backend_identity" && "$backend_identity" != "null" ]]; then
            _assign_one_role "$backend_identity" "backend" || any_failed=true
        else
            log_warn "  No identity found on backend Container App — cannot assign AcrPull"
            any_failed=true
        fi
    fi

    # MCP Container App identity
    if [[ -n "$MCP_CA" ]]; then
        local mcp_identity
        mcp_identity=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
            --query "identity.principalId" -o tsv 2>/dev/null | tr -d '\r' || true)
        if [[ -z "$mcp_identity" || "$mcp_identity" == "null" ]]; then
            mcp_identity=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
                --query "identity.userAssignedIdentities.*.principalId | [0]" -o tsv 2>/dev/null | tr -d '\r' || true)
        fi
        if [[ -n "$mcp_identity" && "$mcp_identity" != "null" ]]; then
            _assign_one_role "$mcp_identity" "MCP" || any_failed=true
        else
            log_warn "  No identity found on MCP Container App — cannot assign AcrPull"
            any_failed=true
        fi
    fi

    # Frontend Web App identity
    if [[ -n "$FRONTEND_APP" ]]; then
        local frontend_identity
        frontend_identity=$(az webapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" \
            --query "identity.principalId" -o tsv 2>/dev/null | tr -d '\r' || true)
        if [[ -z "$frontend_identity" || "$frontend_identity" == "null" ]]; then
            frontend_identity=$(az webapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" \
                --query "identity.userAssignedIdentities.*.principalId | [0]" -o tsv 2>/dev/null | tr -d '\r' || true)
        fi
        if [[ -n "$frontend_identity" && "$frontend_identity" != "null" ]]; then
            frontend_identity="${frontend_identity//$'\r'/}"
            local acr_scope="${ACR_ID//$'\r'/}"
            local existing
            existing=$(az role assignment list --assignee "$frontend_identity" --role "$_acr_pull_role" --scope "$acr_scope" --query "[0].id" -o tsv 2>/dev/null | tr -d '\r' || true)
            if [[ -z "$existing" ]]; then
                local frontend_create_output
                if frontend_create_output=$(az role assignment create --assignee "$frontend_identity" --role "$_acr_pull_role" --scope "$acr_scope" --output none 2>&1); then
                    log_success "  AcrPull assigned to frontend identity"
                else
                    log_error "  Failed to assign AcrPull to frontend identity"
                    log_error "  Azure: $frontend_create_output"
                    any_failed=true
                fi
            else
                log_info "  AcrPull already assigned to frontend identity ✓"
            fi
        else
            log_warn "  No identity found on frontend Web App — cannot assign AcrPull"
            any_failed=true
        fi
    fi

    if [[ "$any_failed" == true ]]; then
        echo ""
        log_error "One or more AcrPull role assignments failed."
        log_error "The container(s) will NOT be able to pull images from $ACR_LOGIN_SERVER."
        log_error ""
        log_error "This usually means your account lacks 'Microsoft.Authorization/roleAssignments/write'."
        log_error "Ask your subscription Owner to grant you 'User Access Administrator' on the RG,"
        log_error "or run:  az role assignment create --assignee <your-object-id> --role 'Owner' --scope /subscriptions/<sub-id>"
        log_error ""
        log_error "If AcrPull roles are already assigned, re-run with: --skip-role-assignment"
        exit 1
    fi
}

# ==============================================================================
# Step 4: Determine Services to Deploy
# ==============================================================================

determine_services() {
    log_step "Step 4: Determining Services to Deploy"

    DEPLOY_BACKEND=false
    DEPLOY_MCP=false
    DEPLOY_FRONTEND=false

    if [[ -n "$SERVICES" ]]; then
        IFS=',' read -ra svc_list <<< "$SERVICES"
        for svc in "${svc_list[@]}"; do
            svc=$(echo "$svc" | tr -d ' ' | tr '[:upper:]' '[:lower:]')
            case "$svc" in
                backend)  DEPLOY_BACKEND=true ;;
                mcp)      DEPLOY_MCP=true ;;
                frontend) DEPLOY_FRONTEND=true ;;
                *)        log_warn "Unknown service: $svc (valid: backend, mcp, frontend)" ;;
            esac
        done
    else
        log_info "No --services specified — deploying all services"
        DEPLOY_BACKEND=true
        DEPLOY_MCP=true
        DEPLOY_FRONTEND=true
    fi

    echo "  Services to deploy:"
    [[ "$DEPLOY_BACKEND" == true ]]  && echo "    ✓ Backend"  || echo "    ○ Backend (skipped)"
    [[ "$DEPLOY_MCP" == true ]]      && echo "    ✓ MCP Server" || echo "    ○ MCP Server (skipped)"
    [[ "$DEPLOY_FRONTEND" == true ]] && echo "    ✓ Frontend" || echo "    ○ Frontend (skipped)"
}

# ==============================================================================
# Step 5: Generate Image Tag
# ==============================================================================

generate_tag() {
    log_step "Step 5: Generating Image Tag"

    if [[ -n "$CUSTOM_TAG" ]]; then
        IMAGE_TAG="$CUSTOM_TAG"
    else
        local timestamp
        timestamp=$(date +%Y%m%d-%H%M%S)
        IMAGE_TAG="$timestamp"
    fi

    log_success "Image tag: $IMAGE_TAG"
}

# ==============================================================================
# Step 6: Build & Push Images
# ==============================================================================

build_and_push() {
    log_step "Step 6: Building & Pushing Docker Images"

    if [[ "$DEPLOY_ONLY" == true ]]; then
        log_info "Skipping build (--deploy-only mode)"
        return
    fi

    log_info "Logging into ACR: $ACR_NAME..."
    if ! az acr login --name "$ACR_NAME"; then
        log_error "ACR login failed for '$ACR_NAME'."
        log_error "  Likely causes:"
        log_error "    - Your account lacks 'AcrPush' / 'Contributor' on the registry."
        log_error "    - Docker daemon not running."
        log_error "    - Tenant blocks docker-credential helpers (try: az acr login -n $ACR_NAME --expose-token)."
        exit 1
    fi
    log_success "ACR login successful"

    export DOCKER_BUILDKIT=1

    # Track per-service success so a partial failure does not strand the others.
    # Uses parallel arrays so we can iterate in order in the summary.
    BUILD_RESULT_NAMES=()
    BUILD_RESULT_STATUS=()
    _record_build_result() { BUILD_RESULT_NAMES+=("$1"); BUILD_RESULT_STATUS+=("$2"); }

    if [[ "$DEPLOY_BACKEND" == true ]]; then
        local full_image="$ACR_LOGIN_SERVER/$BACKEND_IMAGE_NAME:$IMAGE_TAG"
        log_info "Building backend image: $full_image"
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t $full_image $BACKEND_DIR"
            _record_build_result backend dry-run
        elif ! docker build -t "$full_image" "$(_winpath "$BACKEND_DIR")"; then
            log_error "Backend image build FAILED -- continuing with other services"
            _record_build_result backend build-failed
            DEPLOY_BACKEND=false
        else
            log_success "Backend image built"
            if ! docker push "$full_image"; then
                log_error "Backend image push FAILED -- continuing with other services"
                _record_build_result backend push-failed
                DEPLOY_BACKEND=false
            else
                log_success "Backend image pushed: $full_image"
                _record_build_result backend ok
            fi
        fi
    fi

    if [[ "$DEPLOY_MCP" == true ]]; then
        local full_image="$ACR_LOGIN_SERVER/$MCP_IMAGE_NAME:$IMAGE_TAG"
        log_info "Building MCP image: $full_image"
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t $full_image $MCP_DIR"
            _record_build_result mcp dry-run
        elif ! docker build -t "$full_image" "$(_winpath "$MCP_DIR")"; then
            log_error "MCP image build FAILED -- continuing with other services"
            _record_build_result mcp build-failed
            DEPLOY_MCP=false
        else
            log_success "MCP image built"
            if ! docker push "$full_image"; then
                log_error "MCP image push FAILED -- continuing with other services"
                _record_build_result mcp push-failed
                DEPLOY_MCP=false
            else
                log_success "MCP image pushed: $full_image"
                _record_build_result mcp ok
            fi
        fi
    fi

    if [[ "$DEPLOY_FRONTEND" == true ]]; then
        local full_image="$ACR_LOGIN_SERVER/$FRONTEND_IMAGE_NAME:$IMAGE_TAG"
        log_info "Building frontend image: $full_image"
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t $full_image $FRONTEND_DIR"
            _record_build_result frontend dry-run
        elif ! docker build -t "$full_image" "$(_winpath "$FRONTEND_DIR")"; then
            log_error "Frontend image build FAILED -- continuing with other services"
            _record_build_result frontend build-failed
            DEPLOY_FRONTEND=false
        else
            log_success "Frontend image built"
            if ! docker push "$full_image"; then
                log_error "Frontend image push FAILED -- continuing with other services"
                _record_build_result frontend push-failed
                DEPLOY_FRONTEND=false
            else
                log_success "Frontend image pushed: $full_image"
                _record_build_result frontend ok
            fi
        fi
    fi

    # If all selected services failed to build/push, bail before touching Azure resources
    local ok_count=0 i
    for i in "${BUILD_RESULT_STATUS[@]}"; do
        if [[ "$i" == "ok" || "$i" == "dry-run" ]]; then ok_count=$((ok_count + 1)); fi
    done
    if [[ ${#BUILD_RESULT_STATUS[@]} -gt 0 && $ok_count -eq 0 ]]; then
        log_error "All image builds/pushes failed -- aborting before touching Azure resources."
        exit 1
    fi

    if [[ "$BUILD_ONLY" == true ]]; then
        log_success "Build & push complete (--build-only mode, skipping Azure update)"
        return
    fi
}

# ==============================================================================
# Step 7: Configure ACR on Azure Resources (if ACR changed)
# ==============================================================================

configure_acr_on_resources() {
    # For each service: skip if registry + identity already correct, else set with --no-wait
    _set_ca_registry() {
        local ca_name="$1" label="$2"
        local current_server current_identity
        current_server=$(az containerapp show --name "$ca_name" --resource-group "$RESOURCE_GROUP" \
            --query "properties.configuration.registries[0].server" -o tsv 2>/dev/null | tr -d '\r' || true)
        current_identity=$(az containerapp show --name "$ca_name" --resource-group "$RESOURCE_GROUP" \
            --query "properties.configuration.registries[0].identity" -o tsv 2>/dev/null | tr -d '\r' || true)
        if [[ "$current_server" == "$ACR_LOGIN_SERVER" && -n "$current_identity" && "$current_identity" != "null" ]]; then
            log_success "$label: ACR registry already configured — skipping"
            return 0
        fi
        local identity_id
        identity_id=$(az containerapp show --name "$ca_name" --resource-group "$RESOURCE_GROUP" \
            --query "identity.userAssignedIdentities | keys(@) | [0]" -o tsv 2>/dev/null | tr -d '\r' || true)
        local identity_arg="system"
        [[ -n "$identity_id" && "$identity_id" != "null" ]] && identity_arg="$identity_id"
        log_info "Configuring $label registry → $ACR_LOGIN_SERVER..."
        local reg_out reg_rc
        reg_out=$(az_retry containerapp registry set \
                --name "$ca_name" \
                --resource-group "$RESOURCE_GROUP" \
                --server "$ACR_LOGIN_SERVER" \
                --identity "$identity_arg" \
                --output none 2>&1) && reg_rc=0 || reg_rc=$?
        if [[ $reg_rc -eq 0 ]]; then
            log_success "$label registry configured"
        elif echo "$reg_out" | grep -qiE "operation expired|OperationInProgress|ContainerAppOperation|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish|RemoteDisconnected|Connection aborted"; then
            log_warn "$label registry config accepted but status polling failed (network/timeout). The app will pull correctly once the revision is ready."
        else
            log_error "$label registry set FAILED — $reg_out"
            return 1
        fi
    }

    if [[ "$DEPLOY_BACKEND" == true && -n "$BACKEND_CA" ]]; then
        [[ "$DRY_RUN" == true ]] \
            && log_info "[DRY RUN] Would configure backend registry" \
            || _set_ca_registry "$BACKEND_CA" "Backend"
    fi

    if [[ "$DEPLOY_MCP" == true && -n "$MCP_CA" ]]; then
        [[ "$DRY_RUN" == true ]] \
            && log_info "[DRY RUN] Would configure MCP registry" \
            || _set_ca_registry "$MCP_CA" "MCP"
    fi

    if [[ "$DEPLOY_FRONTEND" == true && -n "$FRONTEND_APP" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would update frontend App Service registry config"
        else
            log_info "Updating frontend App Service registry config..."
            if az webapp config appsettings set \
                    --name "$FRONTEND_APP" \
                    --resource-group "$RESOURCE_GROUP" \
                    --settings DOCKER_REGISTRY_SERVER_URL="https://$ACR_LOGIN_SERVER" \
                    --output none && \
               az webapp config set \
                    --name "$FRONTEND_APP" \
                    --resource-group "$RESOURCE_GROUP" \
                    --generic-configurations '{"acrUseManagedIdentityCreds": true}' \
                    --output none; then
                log_success "Frontend registry config updated"
            else
                log_error "Frontend registry config FAILED — image pull may fail."
                return 1
            fi
        fi
    fi
}

# ==============================================================================
# Step 8: Update Azure Resources
# ==============================================================================

update_azure_resources() {
    log_step "Step 7: Updating Azure Resources"

    if [[ "$BUILD_ONLY" == true ]]; then
        return
    fi

    # Configure ACR on resources if needed
    configure_acr_on_resources

    # Update Backend Container App
    if [[ "$DEPLOY_BACKEND" == true ]]; then
        if [[ -z "$BACKEND_CA" ]]; then
            log_warn "No backend Container App found — skipping backend deployment"
        else
            local full_image="$ACR_LOGIN_SERVER/$BACKEND_IMAGE_NAME:$IMAGE_TAG"
            log_info "Updating backend: $BACKEND_CA → $full_image"
            if [[ "$DRY_RUN" == true ]]; then
                log_info "[DRY RUN] Would run: az containerapp update --name $BACKEND_CA --resource-group $RESOURCE_GROUP --image $full_image"
            else
                local upd_out upd_rc
                upd_out=$(az_retry containerapp update \
                    --name "$BACKEND_CA" \
                    --resource-group "$RESOURCE_GROUP" \
                    --image "$full_image" \
                    --output none 2>&1) && upd_rc=0 || upd_rc=$?
                if [[ $upd_rc -eq 0 ]]; then
                    log_success "Backend updated successfully"
                elif echo "$upd_out" | grep -qiE "operation expired|OperationInProgress|ContainerAppOperation|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish|RemoteDisconnected|Connection aborted"; then
                    log_warn "Backend image update accepted but status polling failed (network/timeout). Azure will complete provisioning shortly."
                else
                    log_error "Backend update failed: $upd_out"; return 1
                fi
            fi
        fi
    fi

    # Update MCP Container App
    if [[ "$DEPLOY_MCP" == true ]]; then
        if [[ -z "$MCP_CA" ]]; then
            log_warn "No MCP Container App found — skipping MCP deployment"
        else
            local full_image="$ACR_LOGIN_SERVER/$MCP_IMAGE_NAME:$IMAGE_TAG"
            log_info "Updating MCP: $MCP_CA → $full_image"
            if [[ "$DRY_RUN" == true ]]; then
                log_info "[DRY RUN] Would run: az containerapp update --name $MCP_CA --resource-group $RESOURCE_GROUP --image $full_image"
            else
                local upd_out upd_rc
                upd_out=$(az_retry containerapp update \
                    --name "$MCP_CA" \
                    --resource-group "$RESOURCE_GROUP" \
                    --image "$full_image" \
                    --output none 2>&1) && upd_rc=0 || upd_rc=$?
                if [[ $upd_rc -eq 0 ]]; then
                    log_success "MCP updated successfully"
                elif echo "$upd_out" | grep -qiE "operation expired|OperationInProgress|ContainerAppOperation|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish|RemoteDisconnected|Connection aborted"; then
                    log_warn "MCP image update accepted but status polling failed (network/timeout). Azure will complete provisioning shortly."
                else
                    log_error "MCP update failed: $upd_out"; return 1
                fi
            fi
        fi
    fi

    # Update Frontend App Service
    if [[ "$DEPLOY_FRONTEND" == true ]]; then
        if [[ -z "$FRONTEND_APP" ]]; then
            log_warn "No Frontend Web App found — skipping frontend deployment"
        else
            local full_image="$ACR_LOGIN_SERVER/$FRONTEND_IMAGE_NAME:$IMAGE_TAG"
            log_info "Updating frontend: $FRONTEND_APP → $full_image"
            if [[ "$DRY_RUN" == true ]]; then
                log_info "[DRY RUN] Would run: az webapp config container set + restart"
            else
                az webapp config container set \
                    --name "$FRONTEND_APP" \
                    --resource-group "$RESOURCE_GROUP" \
                    --container-image-name "$full_image" \
                    --container-registry-url "https://$ACR_LOGIN_SERVER" \
                    --output none

                log_info "Restarting frontend App Service..."
                az webapp restart \
                    --name "$FRONTEND_APP" \
                    --resource-group "$RESOURCE_GROUP" \
                    --output none
                log_success "Frontend updated and restarted"
            fi
        fi
    fi
}

# ==============================================================================
# Summary & Rollback Info
# ==============================================================================

print_summary() {
    log_step "Deployment Summary"

    echo "  Resource Group:  $RESOURCE_GROUP"
    echo "  ACR:             $ACR_LOGIN_SERVER"
    echo "  Image Tag:       $IMAGE_TAG"
    echo ""

    if [[ ${#BUILD_RESULT_NAMES[@]:-0} -gt 0 ]]; then
        echo "  Build results:"
        local i name status glyph
        for i in "${!BUILD_RESULT_NAMES[@]}"; do
            name="${BUILD_RESULT_NAMES[$i]}"
            status="${BUILD_RESULT_STATUS[$i]}"
            if [[ "$status" == "ok" || "$status" == "dry-run" ]]; then glyph="[OK]  "; else glyph="[FAIL]"; fi
            printf "    %s %-9s %s\n" "$glyph" "$name" "$status"
        done
        echo ""
    fi

    if [[ "$DEPLOY_BACKEND" == true && -n "$BACKEND_CA" ]]; then
        echo "  Backend:         $ACR_LOGIN_SERVER/$BACKEND_IMAGE_NAME:$IMAGE_TAG"
    fi
    if [[ "$DEPLOY_MCP" == true && -n "$MCP_CA" ]]; then
        echo "  MCP:             $ACR_LOGIN_SERVER/$MCP_IMAGE_NAME:$IMAGE_TAG"
    fi
    if [[ "$DEPLOY_FRONTEND" == true && -n "$FRONTEND_APP" ]]; then
        echo "  Frontend:        $ACR_LOGIN_SERVER/$FRONTEND_IMAGE_NAME:$IMAGE_TAG"
    fi

    echo ""
    echo "  ┌─ Rollback Commands (if needed) ───────────────────────────────"
    echo "  │  NOTE: When rolling back to images from a different registry"
    echo "  │  (e.g. biabcontainerreg.azurecr.io public defaults), the Web App"
    echo "  │  also needs acrUseManagedIdentityCreds disabled and the"
    echo "  │  DOCKER_REGISTRY_SERVER_URL updated, otherwise the pull will"
    echo "  │  fail with ACRTokenRetrievalFailure. Container Apps fall back"
    echo "  │  to anonymous pull automatically for public registries."
    echo "  └──────────────────────────────────────────────────────────────"
    echo ""
    echo "  Copy/paste the commands below (one per line):"
    echo ""

    if [[ "$DEPLOY_BACKEND" == true && -n "$BACKEND_CA" && -n "${OLD_BACKEND_IMAGE:-}" ]]; then
        echo "  # Backend rollback"
        echo "  az containerapp update --name $BACKEND_CA --resource-group $RESOURCE_GROUP --image $OLD_BACKEND_IMAGE"
        echo ""
    fi
    if [[ "$DEPLOY_MCP" == true && -n "$MCP_CA" && -n "${OLD_MCP_IMAGE:-}" ]]; then
        echo "  # MCP rollback"
        echo "  az containerapp update --name $MCP_CA --resource-group $RESOURCE_GROUP --image $OLD_MCP_IMAGE"
        echo ""
    fi
    if [[ "$DEPLOY_FRONTEND" == true && -n "$FRONTEND_APP" && -n "${OLD_FRONTEND_IMAGE:-}" ]]; then
        local old_img="${OLD_FRONTEND_IMAGE#DOCKER|}"
        local old_registry="${old_img%%/*}"
        echo "  # Frontend rollback (run all 4 lines)"
        echo "  az webapp config set --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --generic-configurations '{\"acrUseManagedIdentityCreds\": false}'"
        echo "  az webapp config appsettings set --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --settings DOCKER_REGISTRY_SERVER_URL=https://$old_registry"
        echo "  az webapp config container set --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --container-image-name $old_img"
        echo "  az webapp restart --name $FRONTEND_APP --resource-group $RESOURCE_GROUP"
        echo ""
    fi

    if [[ "$DRY_RUN" == true ]]; then
        echo ""
        log_warn "This was a DRY RUN — no changes were made."
    else
        echo ""
        log_success "Deployment complete!"
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        MACAE - Deploy Local Code to Azure                   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    parse_args "$@"
    check_prerequisites
    check_azure_roles
    validate_and_discover
    resolve_acr
    determine_services
    generate_tag
    build_and_push
    update_azure_resources
    print_summary
}

main "$@"

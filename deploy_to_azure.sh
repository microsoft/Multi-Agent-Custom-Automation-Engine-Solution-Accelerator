#!/usr/bin/env bash
# ==============================================================================
# MACAE - Deploy Local Code to Azure
# ==============================================================================
#
# Builds Docker images for changed services, pushes to ACR, and updates
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

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCE_GROUP=""
ACR_INPUT=""
SERVICES=""
CUSTOM_TAG=""
DRY_RUN=false
BUILD_ONLY=false
DEPLOY_ONLY=false

# Image names (matching infra conventions)
BACKEND_IMAGE_NAME="macaebackend"
MCP_IMAGE_NAME="macaemcp"
FRONTEND_IMAGE_NAME="macaefrontend"

# Service paths
BACKEND_DIR="$SCRIPT_DIR/src/backend"
MCP_DIR="$SCRIPT_DIR/src/mcp_server"
FRONTEND_DIR="$SCRIPT_DIR/src/App"

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

    if command -v docker &>/dev/null; then
        log_success "Docker found: $(docker --version)"
    else
        missing+=("docker")
    fi

    if command -v az &>/dev/null; then
        log_success "Azure CLI found"
    else
        missing+=("azure-cli")
    fi

    if command -v git &>/dev/null; then
        log_success "Git found"
    else
        missing+=("git")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing prerequisites: ${missing[*]}"
        echo ""
        for tool in "${missing[@]}"; do
            case "$tool" in
                docker)
                    echo "  ┌─ Docker ──────────────────────────────────────────────────────"
                    echo "  │  Download: https://docs.docker.com/get-docker/"
                    echo "  │  Windows: Docker Desktop from https://www.docker.com/products/docker-desktop"
                    echo "  │  Verify: docker --version"
                    echo "  └──────────────────────────────────────────────────────────────"
                    ;;
                azure-cli)
                    echo "  ┌─ Azure CLI ───────────────────────────────────────────────────"
                    echo "  │  Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
                    echo "  │  Verify: az --version"
                    echo "  └──────────────────────────────────────────────────────────────"
                    ;;
                git)
                    echo "  ┌─ Git ─────────────────────────────────────────────────────────"
                    echo "  │  Install: https://git-scm.com/downloads"
                    echo "  │  Verify: git --version"
                    echo "  └──────────────────────────────────────────────────────────────"
                    ;;
            esac
        done
        exit 1
    fi

    # Check Docker daemon is running
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running. Please start Docker Desktop and retry."
        exit 1
    fi
    log_success "Docker daemon is running"

    # Check Azure login
    if ! az account show &>/dev/null; then
        log_warn "Not logged into Azure CLI. Running 'az login'..."
        az login
    fi
    log_success "Logged into Azure CLI"
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
    FRONTEND_APP=$(az webapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)

    if [[ -n "$FRONTEND_APP" ]]; then
        log_success "Frontend Web App: $FRONTEND_APP"
    else
        log_warn "Frontend Web App: not found in RG"
    fi

    # Capture current images for rollback
    if [[ -n "$BACKEND_CA" ]]; then
        OLD_BACKEND_IMAGE=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
            --query "properties.template.containers[0].image" -o tsv 2>/dev/null || echo "unknown")
        log_info "Current backend image: $OLD_BACKEND_IMAGE"
    fi

    if [[ -n "$MCP_CA" ]]; then
        OLD_MCP_IMAGE=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
            --query "properties.template.containers[0].image" -o tsv 2>/dev/null || echo "unknown")
        log_info "Current MCP image: $OLD_MCP_IMAGE"
    fi

    if [[ -n "$FRONTEND_APP" ]]; then
        OLD_FRONTEND_IMAGE=$(az webapp config show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" \
            --query "linuxFxVersion" -o tsv 2>/dev/null || echo "unknown")
        log_info "Current frontend image: $OLD_FRONTEND_IMAGE"
    fi
}

# ==============================================================================
# Step 3: Resolve ACR
# ==============================================================================

resolve_acr() {
    log_step "Step 3: Resolving Container Registry"

    if [[ -n "$ACR_INPUT" ]]; then
        # User provided ACR — normalize to name and login server
        local input="${ACR_INPUT%.azurecr.io}"  # strip suffix if provided
        ACR_NAME=$(az acr show --name "$input" --query "name" -o tsv 2>/dev/null || true)
        if [[ -z "$ACR_NAME" ]]; then
            log_error "ACR '$ACR_INPUT' not found or not accessible."
            exit 1
        fi
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv)
        ACR_ID=$(az acr show --name "$ACR_NAME" --query "id" -o tsv)
        log_success "Using specified ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"
        return
    fi

    # Try to discover ACR in the RG
    log_info "Looking for ACR in resource group..."
    ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)

    if [[ -n "$ACR_NAME" ]]; then
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv)
        ACR_ID=$(az acr show --name "$ACR_NAME" --query "id" -o tsv)
        log_success "Found ACR in RG: $ACR_NAME ($ACR_LOGIN_SERVER)"
        return
    fi

    # No ACR found — ask user
    log_warn "No ACR found in resource group '$RESOURCE_GROUP'."
    echo ""
    read -rp "Do you have an existing ACR? Enter its name (or press Enter to create one): " user_acr

    if [[ -n "$user_acr" ]]; then
        local input="${user_acr%.azurecr.io}"
        ACR_NAME=$(az acr show --name "$input" --query "name" -o tsv 2>/dev/null || true)
        if [[ -z "$ACR_NAME" ]]; then
            log_error "ACR '$user_acr' not found."
            exit 1
        fi
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv)
        ACR_ID=$(az acr show --name "$ACR_NAME" --query "id" -o tsv)
        log_success "Using ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"
    else
        # Create new ACR
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
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv)
        ACR_ID=$(az acr show --name "$ACR_NAME" --query "id" -o tsv)
        log_success "Created ACR: $ACR_NAME ($ACR_LOGIN_SERVER)"

        # Assign AcrPull to resource identities
        assign_acr_pull_roles
    fi
}

# ==============================================================================
# ACR Pull Role Assignment
# ==============================================================================

assign_acr_pull_roles() {
    log_info "Assigning AcrPull role to service identities..."

    local acr_pull_role="7f951dda-4ed3-4680-a7ca-43fe172d538d"  # AcrPull built-in role ID

    # Backend Container App identity
    if [[ -n "$BACKEND_CA" ]]; then
        local backend_identity
        backend_identity=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
            --query "identity.principalId" -o tsv 2>/dev/null || true)
        if [[ -n "$backend_identity" && "$backend_identity" != "null" ]]; then
            local existing
            existing=$(az role assignment list --assignee "$backend_identity" --role "$acr_pull_role" --scope "$ACR_ID" --query "[0].id" -o tsv 2>/dev/null || true)
            if [[ -z "$existing" ]]; then
                az role assignment create --assignee "$backend_identity" --role "$acr_pull_role" --scope "$ACR_ID" --output none 2>/dev/null || true
                log_success "  AcrPull assigned to backend identity"
            else
                log_info "  AcrPull already assigned to backend identity ✓"
            fi
        fi
    fi

    # MCP Container App identity
    if [[ -n "$MCP_CA" ]]; then
        local mcp_identity
        mcp_identity=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
            --query "identity.principalId" -o tsv 2>/dev/null || true)
        if [[ -n "$mcp_identity" && "$mcp_identity" != "null" ]]; then
            local existing
            existing=$(az role assignment list --assignee "$mcp_identity" --role "$acr_pull_role" --scope "$ACR_ID" --query "[0].id" -o tsv 2>/dev/null || true)
            if [[ -z "$existing" ]]; then
                az role assignment create --assignee "$mcp_identity" --role "$acr_pull_role" --scope "$ACR_ID" --output none 2>/dev/null || true
                log_success "  AcrPull assigned to MCP identity"
            else
                log_info "  AcrPull already assigned to MCP identity ✓"
            fi
        fi
    fi

    # Frontend Web App identity
    if [[ -n "$FRONTEND_APP" ]]; then
        local frontend_identity
        frontend_identity=$(az webapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" \
            --query "identity.principalId" -o tsv 2>/dev/null || true)
        if [[ -n "$frontend_identity" && "$frontend_identity" != "null" ]]; then
            local existing
            existing=$(az role assignment list --assignee "$frontend_identity" --role "$acr_pull_role" --scope "$ACR_ID" --query "[0].id" -o tsv 2>/dev/null || true)
            if [[ -z "$existing" ]]; then
                az role assignment create --assignee "$frontend_identity" --role "$acr_pull_role" --scope "$ACR_ID" --output none 2>/dev/null || true
                log_success "  AcrPull assigned to frontend identity"
            else
                log_info "  AcrPull already assigned to frontend identity ✓"
            fi
        fi
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
        # Explicit service selection
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
        # Default: deploy all services
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
        local git_sha
        git_sha=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "unknown")
        IMAGE_TAG="${timestamp}-${git_sha}"
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

    # Login to ACR
    log_info "Logging into ACR: $ACR_NAME..."
    az acr login --name "$ACR_NAME"
    log_success "ACR login successful"

    export DOCKER_BUILDKIT=1

    if [[ "$DEPLOY_BACKEND" == true ]]; then
        local full_image="$ACR_LOGIN_SERVER/$BACKEND_IMAGE_NAME:$IMAGE_TAG"
        log_info "Building backend image: $full_image"
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t $full_image $BACKEND_DIR"
        else
            docker build -t "$full_image" "$BACKEND_DIR"
            log_success "Backend image built"
            docker push "$full_image"
            log_success "Backend image pushed: $full_image"
        fi
    fi

    if [[ "$DEPLOY_MCP" == true ]]; then
        local full_image="$ACR_LOGIN_SERVER/$MCP_IMAGE_NAME:$IMAGE_TAG"
        log_info "Building MCP image: $full_image"
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t $full_image $MCP_DIR"
        else
            docker build -t "$full_image" "$MCP_DIR"
            log_success "MCP image built"
            docker push "$full_image"
            log_success "MCP image pushed: $full_image"
        fi
    fi

    if [[ "$DEPLOY_FRONTEND" == true ]]; then
        local full_image="$ACR_LOGIN_SERVER/$FRONTEND_IMAGE_NAME:$IMAGE_TAG"
        log_info "Building frontend image: $full_image"
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t $full_image $FRONTEND_DIR"
        else
            docker build -t "$full_image" "$FRONTEND_DIR"
            log_success "Frontend image built"
            docker push "$full_image"
            log_success "Frontend image pushed: $full_image"
        fi
    fi

    if [[ "$BUILD_ONLY" == true ]]; then
        log_success "Build & push complete (--build-only mode, skipping Azure update)"
    fi
}

# ==============================================================================
# Step 7: Configure ACR on Azure Resources (if ACR changed)
# ==============================================================================

configure_acr_on_resources() {
    # Check if we need to update ACR configuration on the resources
    # This is needed when the ACR is different from what's currently configured

    if [[ "$DEPLOY_BACKEND" == true && -n "$BACKEND_CA" ]]; then
        local current_registry
        current_registry=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
            --query "properties.configuration.registries[0].server" -o tsv 2>/dev/null || true)

        if [[ -n "$current_registry" && "$current_registry" != "$ACR_LOGIN_SERVER" ]]; then
            log_info "Updating backend Container App registry to $ACR_LOGIN_SERVER..."
            if [[ "$DRY_RUN" != true ]]; then
                # Get managed identity for registry pull
                local identity_id
                identity_id=$(az containerapp show --name "$BACKEND_CA" --resource-group "$RESOURCE_GROUP" \
                    --query "identity.userAssignedIdentities | keys(@) | [0]" -o tsv 2>/dev/null || true)

                if [[ -n "$identity_id" && "$identity_id" != "null" ]]; then
                    az containerapp registry set \
                        --name "$BACKEND_CA" \
                        --resource-group "$RESOURCE_GROUP" \
                        --server "$ACR_LOGIN_SERVER" \
                        --identity "$identity_id" \
                        --output none 2>/dev/null || true
                else
                    az containerapp registry set \
                        --name "$BACKEND_CA" \
                        --resource-group "$RESOURCE_GROUP" \
                        --server "$ACR_LOGIN_SERVER" \
                        --identity system \
                        --output none 2>/dev/null || true
                fi
                log_success "Backend registry updated"
            fi
        fi
    fi

    if [[ "$DEPLOY_MCP" == true && -n "$MCP_CA" ]]; then
        local current_registry
        current_registry=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
            --query "properties.configuration.registries[0].server" -o tsv 2>/dev/null || true)

        if [[ -n "$current_registry" && "$current_registry" != "$ACR_LOGIN_SERVER" ]]; then
            log_info "Updating MCP Container App registry to $ACR_LOGIN_SERVER..."
            if [[ "$DRY_RUN" != true ]]; then
                local identity_id
                identity_id=$(az containerapp show --name "$MCP_CA" --resource-group "$RESOURCE_GROUP" \
                    --query "identity.userAssignedIdentities | keys(@) | [0]" -o tsv 2>/dev/null || true)

                if [[ -n "$identity_id" && "$identity_id" != "null" ]]; then
                    az containerapp registry set \
                        --name "$MCP_CA" \
                        --resource-group "$RESOURCE_GROUP" \
                        --server "$ACR_LOGIN_SERVER" \
                        --identity "$identity_id" \
                        --output none 2>/dev/null || true
                else
                    az containerapp registry set \
                        --name "$MCP_CA" \
                        --resource-group "$RESOURCE_GROUP" \
                        --server "$ACR_LOGIN_SERVER" \
                        --identity system \
                        --output none 2>/dev/null || true
                fi
                log_success "MCP registry updated"
            fi
        fi
    fi

    if [[ "$DEPLOY_FRONTEND" == true && -n "$FRONTEND_APP" ]]; then
        log_info "Updating frontend App Service registry config..."
        if [[ "$DRY_RUN" != true ]]; then
            az webapp config appsettings set \
                --name "$FRONTEND_APP" \
                --resource-group "$RESOURCE_GROUP" \
                --settings DOCKER_REGISTRY_SERVER_URL="https://$ACR_LOGIN_SERVER" \
                --output none 2>/dev/null || true

            # Enable managed identity for ACR pull
            az webapp config set \
                --name "$FRONTEND_APP" \
                --resource-group "$RESOURCE_GROUP" \
                --generic-configurations '{"acrUseManagedIdentityCreds": true}' \
                --output none 2>/dev/null || true
            log_success "Frontend registry config updated"
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
                az containerapp update \
                    --name "$BACKEND_CA" \
                    --resource-group "$RESOURCE_GROUP" \
                    --image "$full_image" \
                    --output none
                log_success "Backend updated successfully"
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
                az containerapp update \
                    --name "$MCP_CA" \
                    --resource-group "$RESOURCE_GROUP" \
                    --image "$full_image" \
                    --output none
                log_success "MCP updated successfully"
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

    if [[ "$DEPLOY_BACKEND" == true && -n "$BACKEND_CA" && -n "${OLD_BACKEND_IMAGE:-}" ]]; then
        echo "  │  Backend:  az containerapp update --name $BACKEND_CA --resource-group $RESOURCE_GROUP --image $OLD_BACKEND_IMAGE"
    fi
    if [[ "$DEPLOY_MCP" == true && -n "$MCP_CA" && -n "${OLD_MCP_IMAGE:-}" ]]; then
        echo "  │  MCP:      az containerapp update --name $MCP_CA --resource-group $RESOURCE_GROUP --image $OLD_MCP_IMAGE"
    fi
    if [[ "$DEPLOY_FRONTEND" == true && -n "$FRONTEND_APP" && -n "${OLD_FRONTEND_IMAGE:-}" ]]; then
        local old_img="${OLD_FRONTEND_IMAGE#DOCKER|}"
        echo "  │  Frontend: az webapp config container set --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --container-image-name $old_img"
    fi
    echo "  └──────────────────────────────────────────────────────────────"

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
    validate_and_discover
    resolve_acr
    determine_services
    generate_tag
    build_and_push
    update_azure_resources
    print_summary
}

main "$@"

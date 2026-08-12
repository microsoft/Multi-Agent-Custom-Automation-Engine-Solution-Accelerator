#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Builds the backend, frontend and MCP container images and pushes them to
# the Azure Container Registry (ACR) provisioned by the solution, then updates
# the Container Apps and the frontend Web App to use the freshly pushed images.
#
# Intended to run as an `azd` postprovision hook. Reads provisioning outputs
# via `azd env get-values`.
#
# Usage:
#   bash build_and_push_images.sh [RESOURCE_GROUP_NAME]
#
#   If RESOURCE_GROUP_NAME is provided, the script queries Azure directly to
#   discover resources (ACR, Container Apps, Web App) in that RG.
#   If omitted, it reads values from `azd env get-values` / environment vars.
#
# Environment variables (all optional):
#   AZURE_ENV_BUILD_MODE        remote | local          (default: remote)
#   AZURE_ENV_IMAGE_TAG         tag applied to images   (default: latest)
#   AZURE_ENV_SKIP_IMAGE_BUILD  true to skip entirely
# ---------------------------------------------------------------------------
set -euo pipefail

section() {
    printf '\n'
    printf '=%.0s' {1..70}
    printf '\n%s\n' "$1"
    printf '=%.0s' {1..70}
    printf '\n'
}

require() {
    local name="$1"
    local value="$2"
    if [ -z "${value}" ]; then
        echo "ERROR: required value '${name}' is missing." >&2
        echo "       Ensure provisioning finished and the outputs are in azd env." >&2
        exit 1
    fi
}

update_container_app_image_and_port() {
    local app_name="$1"
    local container_name="$2"
    local image="$3"
    local target_port="$4"
    local registry_server="$5"
    local config_file

    config_file="$(mktemp)"

    if ! az containerapp show \
        --name "${app_name}" \
        --resource-group "${RESOURCE_GROUP}" \
        --output json |
        jq \
            --arg app_name "${app_name}" \
            --arg container_name "${container_name}" \
            --arg image "${image}" \
            --arg registry_server "${registry_server}" \
            --argjson target_port "${target_port}" \
            'if any(.properties.template.containers[]?; .name == $container_name) then
                 .
             else
                 error("Container \($container_name) was not found in Container App \($app_name)")
             end
             | (.identity.userAssignedIdentities | keys[0]) as $identity_resource_id
             | if $identity_resource_id == null then error("Container App does not have a user-assigned identity for ACR image pulls") else . end
             | (.properties.template.containers[] | select(.name == $container_name).image) = $image
             | .properties.configuration.ingress.targetPort = $target_port
             | .properties.configuration.registries = [{
                 server: $registry_server,
                 identity: $identity_resource_id
               }]' \
            > "${config_file}"; then
        rm -f "${config_file}"
        return 1
    fi

    if ! az containerapp update \
        --name "${app_name}" \
        --resource-group "${RESOURCE_GROUP}" \
        --yaml "${config_file}" \
        --output none; then
        rm -f "${config_file}"
        return 1
    fi

    rm -f "${config_file}"
}

if [ "${AZURE_ENV_SKIP_IMAGE_BUILD:-}" = "true" ]; then
    echo "AZURE_ENV_SKIP_IMAGE_BUILD=true. Skipping container image build & push."
    exit 0
fi

# --- Determine configuration source -----------------------------------------
ARG_RESOURCE_GROUP="${1:-}"

if [ -n "${ARG_RESOURCE_GROUP}" ]; then
    section "Discovering resources from resource group: ${ARG_RESOURCE_GROUP}"

    if ! command -v az >/dev/null 2>&1; then
        echo "ERROR: 'az' CLI is required when specifying a resource group argument." >&2
        exit 1
    fi

    RESOURCE_GROUP="${ARG_RESOURCE_GROUP}"

    # Discover ACR (tr -d '\r' strips Windows carriage returns in Git Bash)
    ACR_NAME="$(az acr list --resource-group "${RESOURCE_GROUP}" --query "[0].name" -o tsv 2>/dev/null | tr -d '\r' || true)"
    ACR_ENDPOINT="$(az acr list --resource-group "${RESOURCE_GROUP}" --query "[0].loginServer" -o tsv 2>/dev/null | tr -d '\r' || true)"

    # Discover Container Apps
    CA_LIST="$(az containerapp list --resource-group "${RESOURCE_GROUP}" --query "[].name" -o tsv 2>/dev/null | tr -d '\r' || true)"
    BACKEND_CA=""
    MCP_CA=""
    while IFS= read -r ca_name; do
        [ -z "${ca_name}" ] && continue
        ca_lower="$(echo "${ca_name}" | tr '[:upper:]' '[:lower:]')"
        if [[ "${ca_lower}" == *"mcp"* ]]; then
            MCP_CA="${ca_name}"
        else
            BACKEND_CA="${ca_name}"
        fi
    done <<< "${CA_LIST}"

    # Discover Frontend Web App
    FRONTEND_APP="$(az webapp list --resource-group "${RESOURCE_GROUP}" --query "[0].name" -o tsv 2>/dev/null | tr -d '\r' || true)"

    # Use defaults or env overrides for image names
    BACKEND_IMAGE="${BACKEND_IMAGE_NAME:-macaebackend}"
    FRONTEND_IMAGE="${FRONTEND_IMAGE_NAME:-macaefrontend}"
    MCP_IMAGE="${MCP_IMAGE_NAME:-macaemcp}"
    FRONTEND_PORT="${FRONTEND_WEBSITES_PORT:-3000}"
    BUILD_MODE="${AZURE_ENV_BUILD_MODE:-remote}"
    IMAGE_TAG="${AZURE_ENV_IMAGE_TAG:-latest}"

    echo "Discovered resources:"
    echo "  ACR:            ${ACR_NAME:-<not found>} (${ACR_ENDPOINT:-<not found>})"
    echo "  Backend CA:     ${BACKEND_CA:-<not found>}"
    echo "  MCP CA:         ${MCP_CA:-<not found>}"
    echo "  Frontend App:   ${FRONTEND_APP:-<not found>}"
else
    section "Reading azd environment values"

    # Load azd outputs into the current shell without overriding vars already set.
    if command -v azd >/dev/null 2>&1; then
        while IFS='=' read -r key value; do
            [ -z "${key}" ] && continue
            # Strip surrounding quotes
            value="${value%\"}"
            value="${value#\"}"
            if [ -z "${!key:-}" ]; then
                export "${key}=${value}"
            fi
        done < <(azd env get-values 2>/dev/null | tr -d '\r' || true)
    else
        echo "WARN: 'azd' not found on PATH; relying on environment variables only." >&2
    fi

    ACR_NAME="${AZURE_CONTAINER_REGISTRY_NAME:-}"
    ACR_ENDPOINT="${AZURE_CONTAINER_REGISTRY_ENDPOINT:-}"
    RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
    BACKEND_CA="${BACKEND_CONTAINER_APP_NAME:-}"
    MCP_CA="${MCP_CONTAINER_APP_NAME:-}"
    FRONTEND_APP="${FRONTEND_WEB_APP_NAME:-}"
    BACKEND_IMAGE="${BACKEND_IMAGE_NAME:-macaebackend}"
    FRONTEND_IMAGE="${FRONTEND_IMAGE_NAME:-macaefrontend}"
    MCP_IMAGE="${MCP_IMAGE_NAME:-macaemcp}"
    FRONTEND_PORT="${FRONTEND_WEBSITES_PORT:-3000}"
    BUILD_MODE="${AZURE_ENV_BUILD_MODE:-remote}"
    IMAGE_TAG="${AZURE_ENV_IMAGE_TAG:-latest}"
fi

require AZURE_CONTAINER_REGISTRY_NAME     "${ACR_NAME}"
require AZURE_CONTAINER_REGISTRY_ENDPOINT "${ACR_ENDPOINT}"
require AZURE_RESOURCE_GROUP              "${RESOURCE_GROUP}"
require BACKEND_CONTAINER_APP_NAME        "${BACKEND_CA}"
require MCP_CONTAINER_APP_NAME            "${MCP_CA}"
require FRONTEND_WEB_APP_NAME             "${FRONTEND_APP}"

case "${BUILD_MODE}" in
    local|remote) ;;
    *) echo "ERROR: AZURE_ENV_BUILD_MODE must be 'local' or 'remote' (got '${BUILD_MODE}')." >&2; exit 1;;
esac

echo "ACR:                ${ACR_NAME} (${ACR_ENDPOINT})"
echo "Resource group:     ${RESOURCE_GROUP}"
echo "Backend CA:         ${BACKEND_CA}   -> ${BACKEND_IMAGE}:${IMAGE_TAG}"
echo "MCP CA:             ${MCP_CA}       -> ${MCP_IMAGE}:${IMAGE_TAG}"
echo "Frontend Web App:   ${FRONTEND_APP} -> ${FRONTEND_IMAGE}:${IMAGE_TAG}"
echo "Build mode:         ${BUILD_MODE}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SRC_ROOT="${REPO_ROOT}/src"

declare -a IMAGE_NAMES=("${BACKEND_IMAGE}" "${FRONTEND_IMAGE}" "${MCP_IMAGE}")
declare -a IMAGE_CTXS=("${SRC_ROOT}/backend" "${SRC_ROOT}/App" "${SRC_ROOT}/mcp_server")

for ctx in "${IMAGE_CTXS[@]}"; do
    if [ ! -f "${ctx}/Dockerfile" ]; then
        echo "ERROR: Dockerfile not found at ${ctx}/Dockerfile" >&2
        exit 1
    fi
done

# --- WAF: temporarily relax ACR restrictions for build/push, restored on exit ---
DEPLOYMENT_TYPE="$(az group show --name "${RESOURCE_GROUP}" --query "tags.Type" -o tsv 2>/dev/null | tr -d '\r' || true)"

restore_acr_waf() {
    if [ "${DEPLOYMENT_TYPE}" = "WAF" ]; then
        echo ""
        echo "Restoring WAF ACR configuration..."
        az acr update --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --default-action Deny --output none || true
        az acr update --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --public-network-enabled false --output none || true
        az acr update --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --allow-exports false --output none || true
        echo "ACR configuration restored."
    fi
}

if [ "${DEPLOYMENT_TYPE}" = "WAF" ]; then
    section "WAF deployment detected - temporarily relaxing ACR restrictions"
    trap restore_acr_waf EXIT
    az acr update --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --allow-exports true --output none
    az acr update --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --public-network-enabled true --output none
    az acr update --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --default-action Allow --output none
    echo "ACR restrictions temporarily relaxed."
fi

section "Building and pushing images (${BUILD_MODE})"

for i in "${!IMAGE_NAMES[@]}"; do
    name="${IMAGE_NAMES[$i]}"
    ctx="${IMAGE_CTXS[$i]}"
    ref="${ACR_ENDPOINT}/${name}:${IMAGE_TAG}"

    echo ""
    echo ">>> ${name}"

    if [ "${BUILD_MODE}" = "local" ]; then
        if ! command -v docker >/dev/null 2>&1; then
            echo "ERROR: BUILD_MODE=local but 'docker' is not on PATH." >&2
            exit 1
        fi
        (cd "${ctx}" && docker build -t "${ref}" -f Dockerfile .)
        az acr login --name "${ACR_NAME}"
        docker push "${ref}"
    else
        (cd "${ctx}" && az acr build \
            --registry "${ACR_NAME}" \
            --image "${name}:${IMAGE_TAG}" \
            --file Dockerfile \
            .)
    fi
done

section "Updating Container Apps and Web App to use new images"

BACKEND_REF="${ACR_ENDPOINT}/${BACKEND_IMAGE}:${IMAGE_TAG}"
MCP_REF="${ACR_ENDPOINT}/${MCP_IMAGE}:${IMAGE_TAG}"
FRONTEND_REF="${ACR_ENDPOINT}/${FRONTEND_IMAGE}:${IMAGE_TAG}"

echo "Updating backend Container App -> ${BACKEND_REF}"
update_container_app_image_and_port "${BACKEND_CA}" "backend" "${BACKEND_REF}" 8000 "${ACR_ENDPOINT}"

echo "Updating MCP Container App -> ${MCP_REF}"
update_container_app_image_and_port "${MCP_CA}" "mcp" "${MCP_REF}" 9000 "${ACR_ENDPOINT}"

echo "Updating Frontend Web App -> ${FRONTEND_REF}"
az webapp config container set \
    --name "${FRONTEND_APP}" \
    --resource-group "${RESOURCE_GROUP}" \
    --container-image-name "${FRONTEND_REF}" \
    --container-registry-url "https://${ACR_ENDPOINT}" \
    --output none

echo "Ensuring WEBSITES_PORT=${FRONTEND_PORT} and DOCKER_REGISTRY_SERVER_URL on Web App"
az webapp config appsettings set \
    --name "${FRONTEND_APP}" \
    --resource-group "${RESOURCE_GROUP}" \
    --settings "WEBSITES_PORT=${FRONTEND_PORT}" "DOCKER_REGISTRY_SERVER_URL=https://${ACR_ENDPOINT}" \
    --output none

section "Image build & push complete"
echo "All images built, pushed to '${ACR_ENDPOINT}' with tag '${IMAGE_TAG}', and services updated."

section "Next step: Upload Team Configurations and index sample data"
echo "Run the following command from the project root to upload the team"
echo "configurations and index the sample data:"
echo ""
echo "   bash infra/scripts/post-provision/post_deploy.sh"
echo ""
#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
#
# configure_auth.sh
# Configures Microsoft Entra ID authentication for MACAE after deployment:
# creates or reuses a single-tenant app registration, configures App Service
# Authentication (Easy Auth) on the frontend App Service, and enables API
# authentication on the backend Container App by setting AUTH_CLIENT_ID.
#
# Run this script AFTER post_deploy.sh has uploaded the team configurations,
# because in WAF deployments post_deploy calls the backend through the
# frontend URL, which requires sign-in once this script has run.
# Re-run it after every 'azd provision' / 'azd up': provisioning resets the
# backend environment variables and the frontend app settings.
#
## Optional Environment Variables (also read from the current azd environment):
# RESOURCE_GROUP_NAME         - Resource group of the deployment
# FRONTEND_WEB_APP_NAME       - Frontend App Service name
# BACKEND_CONTAINER_APP_NAME  - Backend Container App name
# AZURE_AUTH_CLIENT_ID        - Existing app registration client ID to reuse

set -euo pipefail

readonly SECRET_SETTING_NAME="MICROSOFT_PROVIDER_AUTHENTICATION_SECRET"
readonly SCOPE_VALUE="user_impersonation"
# Pre-authorized so post-deployment scripts can run:
# az account get-access-token --resource api://<clientId>
readonly AZURE_CLI_APP_ID="04b07795-8ddb-461a-bbee-02f9e1bf7b46"

RESOURCE_GROUP=""
FRONTEND_APP_NAME=""
BACKEND_CONTAINER_APP_NAME="${BACKEND_CONTAINER_APP_NAME:-}"
CLIENT_ID=""
APP_DISPLAY_NAME=""

usage() {
  echo "Usage: ${0##*/} [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --resource-group <name>         Resource group (default: RESOURCE_GROUP_NAME)"
  echo "  --frontend-app-name <name>      Frontend App Service (default: FRONTEND_WEB_APP_NAME)"
  echo "  --backend-container-app <name>  Backend Container App (default: BACKEND_CONTAINER_APP_NAME)"
  echo "  --client-id <id>                Existing app registration (default: AZURE_AUTH_CLIENT_ID)"
  echo "  --app-display-name <name>       Name for a new app registration"
  echo "  --help, -h                      Show this help message"
  exit 1
}

err() {
  printf "ERROR: %s\n" "$1" >&2
  exit 1
}

info() {
  printf "%s\n" "$1"
}

ok() {
  printf "\033[32m✅ %s\033[0m\n" "$1"
}

# Azure CLI single-value output without Windows carriage returns (Git Bash).
az_tsv() {
  az "$@" --output tsv | tr -d '\r'
}

azd_env_value() {
  local key="$1"
  local value
  command -v azd &>/dev/null || return 0
  value="$(azd env get-value "${key}" 2>/dev/null | tr -d '\r')" || return 0
  if [[ -z "${value}" || "${value}" == *"ERROR:"* || "${value}" == *"not found"* ]]; then
    return 0
  fi
  printf "%s" "${value}"
}

# Resolves a value from an argument, then environment variables, then azd env.
resolve_value() {
  local value="$1"
  shift
  if [[ -n "${value}" ]]; then
    printf "%s" "${value}"
    return 0
  fi
  local key
  for key in "$@"; do
    if [[ -n "${!key:-}" ]]; then
      printf "%s" "${!key}"
      return 0
    fi
    value="$(azd_env_value "${key}")"
    if [[ -n "${value}" ]]; then
      printf "%s" "${value}"
      return 0
    fi
  done
}

new_uuid() {
  if command -v uuidgen &>/dev/null; then
    uuidgen | tr '[:upper:]' '[:lower:]'
    return 0
  fi
  # Random version-4 UUID from /dev/urandom (works in Git Bash, Linux, macOS)
  local hex
  hex="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
  printf "%s-%s-4%s-%x%s-%s\n" \
    "${hex:0:8}" "${hex:8:4}" "${hex:13:3}" \
    "$(( (16#${hex:16:1} & 3) | 8 ))" "${hex:17:3}" "${hex:20:12}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --resource-group|--frontend-app-name|--backend-container-app|--client-id|--app-display-name)
        if [[ -z "${2:-}" || "$2" == --* ]]; then
          echo "Error: $1 requires an argument" >&2
          usage
        fi
        case "$1" in
          --resource-group) RESOURCE_GROUP="$2" ;;
          --frontend-app-name) FRONTEND_APP_NAME="$2" ;;
          --backend-container-app) BACKEND_CONTAINER_APP_NAME="$2" ;;
          --client-id) CLIENT_ID="$2" ;;
          --app-display-name) APP_DISPLAY_NAME="$2" ;;
        esac
        shift 2
        ;;
      --help|-h)
        usage
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        ;;
    esac
  done
}

main() {
  parse_args "$@"

  command -v az &>/dev/null || err "Azure CLI ('az') is required."
  command -v jq &>/dev/null || err "'jq' is required."

  local tenant_id subscription_id
  tenant_id="$(az_tsv account show --query tenantId)"
  subscription_id="$(az_tsv account show --query id)"

  RESOURCE_GROUP="$(resolve_value "${RESOURCE_GROUP}" RESOURCE_GROUP_NAME AZURE_RESOURCE_GROUP)"
  FRONTEND_APP_NAME="$(resolve_value "${FRONTEND_APP_NAME}" FRONTEND_WEB_APP_NAME)"
  BACKEND_CONTAINER_APP_NAME="$(resolve_value "${BACKEND_CONTAINER_APP_NAME}" BACKEND_CONTAINER_APP_NAME)"
  CLIENT_ID="$(resolve_value "${CLIENT_ID}" AZURE_AUTH_CLIENT_ID)"

  [[ -n "${RESOURCE_GROUP}" ]] || err "Missing resource group. Pass --resource-group or run from the azd environment used for the deployment."
  [[ -n "${FRONTEND_APP_NAME}" ]] || err "Missing frontend App Service name. Pass --frontend-app-name."
  [[ -n "${BACKEND_CONTAINER_APP_NAME}" ]] || err "Missing backend Container App name. Pass --backend-container-app."

  # The backend validates the token issuer against its AZURE_TENANT_ID (set by Bicep).
  local backend_tenant_id
  backend_tenant_id="$(az_tsv containerapp show \
    --name "${BACKEND_CONTAINER_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "properties.template.containers[0].env[?name=='AZURE_TENANT_ID'].value | [0]")" \
    || err "Backend Container App '${BACKEND_CONTAINER_APP_NAME}' was not found in '${RESOURCE_GROUP}'."
  if [[ -n "${backend_tenant_id}" && "${backend_tenant_id}" != "${tenant_id}" ]]; then
    err "Signed-in tenant '${tenant_id}' differs from the backend AZURE_TENANT_ID '${backend_tenant_id}'. Run 'az login --tenant ${backend_tenant_id}' and retry."
  fi

  local frontend_host redirect_uri
  frontend_host="$(az_tsv webapp show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${FRONTEND_APP_NAME}" \
    --query defaultHostName)"
  redirect_uri="https://${frontend_host}/.auth/login/aad/callback"

  echo ""
  info "Resource group:   ${RESOURCE_GROUP}"
  info "Frontend:         ${FRONTEND_APP_NAME} (https://${frontend_host})"
  info "Backend:          ${BACKEND_CONTAINER_APP_NAME}"
  info "Tenant:           ${tenant_id}"
  echo ""

  # --- App registration ----------------------------------------------------
  local app_json
  if [[ -n "${CLIENT_ID}" ]]; then
    app_json="$(az ad app show --id "${CLIENT_ID}" --output json)"
    info "Reusing app registration '$(jq -r '.displayName' <<<"${app_json}")' (${CLIENT_ID})."
  else
    if [[ -z "${APP_DISPLAY_NAME}" ]]; then
      local environment_name
      environment_name="$(azd_env_value AZURE_ENV_NAME)"
      if [[ -n "${environment_name}" ]]; then
        APP_DISPLAY_NAME="${environment_name}-macae-auth"
      else
        APP_DISPLAY_NAME="${FRONTEND_APP_NAME}-auth"
      fi
    fi
    info "Creating app registration '${APP_DISPLAY_NAME}'."
    app_json="$(az ad app create \
      --display-name "${APP_DISPLAY_NAME}" \
      --sign-in-audience AzureADMyOrg \
      --enable-id-token-issuance true \
      --web-redirect-uris "${redirect_uri}" \
      --output json)"
    CLIENT_ID="$(jq -r '.appId' <<<"${app_json}")"
  fi

  local app_object_id graph_uri
  app_object_id="$(jq -r '.id' <<<"${app_json}")"
  graph_uri="https://graph.microsoft.com/v1.0/applications/${app_object_id}"

  # Read loops instead of mapfile, which macOS's bundled Bash 3.2 lacks
  local -a redirect_uris=() identifier_uris=()
  local uri
  while IFS= read -r uri; do
    redirect_uris+=("${uri}")
  done < <(jq -r --arg u "${redirect_uri}" \
    '[(.web.redirectUris // [])[], $u] | unique[]' <<<"${app_json}")
  az ad app update --id "${CLIENT_ID}" \
    --enable-id-token-issuance true \
    --web-redirect-uris "${redirect_uris[@]}" \
    --output none

  while IFS= read -r uri; do
    identifier_uris+=("${uri}")
  done < <(jq -r --arg u "api://${CLIENT_ID}" \
    '[(.identifierUris // [])[], $u] | unique[]' <<<"${app_json}")
  az ad app update --id "${CLIENT_ID}" \
    --identifier-uris "${identifier_uris[@]}" \
    --output none

  # Expose api://<clientId>/user_impersonation (v2 access tokens)
  local scope_id scopes_body
  scope_id="$(jq -r --arg v "${SCOPE_VALUE}" \
    'first((.api.oauth2PermissionScopes // [])[] | select(.value == $v) | .id) // empty' <<<"${app_json}")"
  if [[ -z "${scope_id}" ]]; then
    scope_id="$(new_uuid)"
  fi
  scopes_body="$(jq -c --arg id "${scope_id}" --arg v "${SCOPE_VALUE}" '{
    api: {
      requestedAccessTokenVersion: 2,
      oauth2PermissionScopes: (
        (.api.oauth2PermissionScopes // [])
        | if any(.[]; .value == $v) then . else . + [{
            adminConsentDescription: "Access the MACAE API on behalf of the signed-in user.",
            adminConsentDisplayName: "Access the MACAE API",
            id: $id,
            isEnabled: true,
            type: "User",
            userConsentDescription: "Allow this application to access the MACAE API on your behalf.",
            userConsentDisplayName: "Access the MACAE API",
            value: $v
          }] end
      )
    }
  }' <<<"${app_json}")"
  az rest --method patch --uri "${graph_uri}" \
    --headers "Content-Type=application/json" \
    --body "${scopes_body}" --output none

  # A pre-authorization can only reference a scope that already exists, so it is a separate update.
  # Keep any permissions Azure CLI is already pre-authorized for and add the MACAE scope.
  local preauth_body
  preauth_body="$(jq -c --arg cli "${AZURE_CLI_APP_ID}" --arg id "${scope_id}" '
    (.api.preAuthorizedApplications // []) as $apps
    | (first($apps[] | select(.appId == $cli) | .delegatedPermissionIds) // []) as $cli_ids
    | {
        api: {
          preAuthorizedApplications: (
            [$apps[] | select(.appId != $cli)]
            + [{ appId: $cli, delegatedPermissionIds: (($cli_ids + [$id]) | unique) }]
          )
        }
      }' <<<"${app_json}")"
  az rest --method patch --uri "${graph_uri}" \
    --headers "Content-Type=application/json" \
    --body "${preauth_body}" --output none
  ok "App registration configured (client ID: ${CLIENT_ID})."

  # --- Frontend App Service Authentication ---------------------------------
  local auth_settings_uri configured_client_id client_secret=""
  auth_settings_uri="https://management.azure.com/subscriptions/${subscription_id}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${FRONTEND_APP_NAME}/config/authsettingsV2?api-version=2022-09-01"
  configured_client_id="$(az_tsv rest --method get --uri "${auth_settings_uri}" \
    --query 'properties.identityProviders.azureActiveDirectory.registration.clientId' 2>/dev/null || true)"
  if [[ "${configured_client_id}" == "${CLIENT_ID}" ]]; then
    client_secret="$(az_tsv webapp config appsettings list \
      --resource-group "${RESOURCE_GROUP}" \
      --name "${FRONTEND_APP_NAME}" \
      --query "[?name=='${SECRET_SETTING_NAME}'].value | [0]" || true)"
  fi
  if [[ -z "${client_secret}" ]]; then
    info "Creating a client secret for App Service Authentication."
    client_secret="$(az_tsv ad app credential reset \
      --id "${CLIENT_ID}" \
      --append \
      --display-name "MACAE App Service Authentication" \
      --years 2 \
      --query password)"
  fi

  info "Configuring App Service Authentication on '${FRONTEND_APP_NAME}'."
  az webapp config appsettings set \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${FRONTEND_APP_NAME}" \
    --settings "${SECRET_SETTING_NAME}=${client_secret}" \
    --output none

  # The MACAE frontend does not redirect anonymous users itself, so the platform must.
  local auth_body
  auth_body="$(jq -nc \
    --arg client_id "${CLIENT_ID}" \
    --arg tenant_id "${tenant_id}" \
    --arg secret_setting "${SECRET_SETTING_NAME}" \
    --arg scope "${SCOPE_VALUE}" '{
    properties: {
      platform: { enabled: true, runtimeVersion: "~1" },
      globalValidation: {
        requireAuthentication: true,
        unauthenticatedClientAction: "RedirectToLoginPage",
        redirectToProvider: "azureactivedirectory"
      },
      httpSettings: { requireHttps: true },
      identityProviders: {
        azureActiveDirectory: {
          enabled: true,
          registration: {
            clientId: $client_id,
            clientSecretSettingName: $secret_setting,
            openIdIssuer: "https://login.microsoftonline.com/\($tenant_id)/v2.0"
          },
          login: {
            loginParameters: ["scope=openid profile email offline_access api://\($client_id)/\($scope)"]
          },
          validation: { allowedAudiences: [$client_id, "api://\($client_id)"] }
        }
      },
      login: { tokenStore: { enabled: true } }
    }
  }')"
  az rest --method put --uri "${auth_settings_uri}" \
    --headers "Content-Type=application/json" \
    --body "${auth_body}" --output none
  ok "App Service Authentication configured."

  if command -v azd &>/dev/null; then
    azd env set AZURE_AUTH_CLIENT_ID "${CLIENT_ID}" &>/dev/null || true
  fi

  # --- Backend API authentication ------------------------------------------
  info "Enabling API authentication on '${BACKEND_CONTAINER_APP_NAME}'."
  az containerapp update \
    --name "${BACKEND_CONTAINER_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --set-env-vars "AUTH_CLIENT_ID=${CLIENT_ID}" \
    --output none
  ok "Backend AUTH_CLIENT_ID set to ${CLIENT_ID}."

  echo ""
  ok "Authentication configured. Allow a few minutes for the changes to take effect, then sign in at https://${frontend_host}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi

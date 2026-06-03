#!/usr/bin/env bash
set -uo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

backend_url=""
storage_account=""
ai_search=""
ai_search_endpoint=""
openai_endpoint=""
project_endpoint=""
az_subscription_id=""
resource_group=""
user_principal_id=""
python_cmd=""
venv_path="$SCRIPT_DIR/scriptenv"

st_is_public_access_disabled=false
srch_is_public_access_disabled=false
ai_foundry_is_public_access_disabled=false
ai_foundry_account_name=""
ai_foundry_resource_group=""
has_errors=false

info() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

error() {
  echo "[ERROR] $*" >&2
}

fatal() {
  error "$*"
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      -g|--resource-group)
        if [ -z "${2-}" ]; then
          fatal "Missing value for $1"
        fi
        resource_group="$2"
        shift 2
        ;;
      --help|-h)
        cat <<'EOF'
Usage: post_deploy.sh [--resource-group <name>]

Options:
  -g, --resource-group   Resource group name for deployment fallback resolution
  -h, --help             Show this help message
EOF
        exit 0
        ;;
      *)
        fatal "Unknown option: $1"
        ;;
    esac
  done
}

restore_network_access() {
  if [ -z "$resource_group" ] || [ -z "$storage_account" ] || [ -z "$ai_search" ]; then
    return
  fi

  local rg_type_tag
  rg_type_tag="$(az group show --name "$resource_group" --query "tags.Type" -o tsv 2>/dev/null || true)"
  if [ "$rg_type_tag" != "WAF" ]; then
    return
  fi

  if [ "$st_is_public_access_disabled" = true ] || [ "$srch_is_public_access_disabled" = true ] || [ "$ai_foundry_is_public_access_disabled" = true ]; then
    info "=== Restoring network access settings ==="
  fi

  if [ "$st_is_public_access_disabled" = true ]; then
    local current_access
    current_access="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query "publicNetworkAccess" -o tsv 2>/dev/null || true)"
    if [ "$current_access" = "Enabled" ]; then
      info "Disabling public access for Storage Account: $storage_account"
      az storage account update --name "$storage_account" --resource-group "$resource_group" --public-network-access disabled --default-action Deny --output none 2>/dev/null || true
      info "✓ Storage Account public access disabled"
    else
      info "✓ Storage Account access unchanged (already at desired state)"
    fi
  fi

  if [ "$srch_is_public_access_disabled" = true ]; then
    local current_access
    current_access="$(az search service show --name "$ai_search" --resource-group "$resource_group" --query "publicNetworkAccess" -o tsv 2>/dev/null || true)"
    if [ "$current_access" = "Enabled" ]; then
      info "Disabling public access for AI Search Service: $ai_search"
      az search service update --name "$ai_search" --resource-group "$resource_group" --public-network-access disabled --output none 2>/dev/null || true
      info "✓ AI Search Service public access disabled"
    else
      info "✓ AI Search Service access unchanged (already at desired state)"
    fi
  fi

  if [ "$ai_foundry_is_public_access_disabled" = true ] && [ -n "$ai_foundry_account_name" ] && [ -n "$ai_foundry_resource_group" ]; then
    local current_access
    current_access="$(az cognitiveservices account show --name "$ai_foundry_account_name" --resource-group "$ai_foundry_resource_group" --query "properties.publicNetworkAccess" -o tsv 2>/dev/null || true)"
    if [ "$current_access" = "Enabled" ]; then
      info "Disabling public access for AI Foundry: $ai_foundry_account_name"
      az resource update --resource-group "$ai_foundry_resource_group" --name "$ai_foundry_account_name" --resource-type "Microsoft.CognitiveServices/accounts" --set properties.publicNetworkAccess=Disabled --output none 2>/dev/null || true
      info "✓ AI Foundry public access disabled"
    else
      info "✓ AI Foundry access unchanged (already at desired state)"
    fi
  fi

  if [ "$st_is_public_access_disabled" = true ] || [ "$srch_is_public_access_disabled" = true ] || [ "$ai_foundry_is_public_access_disabled" = true ]; then
    info "=========================================="
  fi
}

enable_public_access_if_waf() {
  if [ -z "$resource_group" ]; then
    return
  fi

  local rg_type_tag
  rg_type_tag="$(az group show --name "$resource_group" --query "tags.Type" -o tsv 2>/dev/null || true)"
  if [ "$rg_type_tag" != "WAF" ]; then
    return
  fi

  info "=== WAF deployment detected — temporarily enabling public network access ==="

  local st_public_access
  st_public_access="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query "publicNetworkAccess" -o tsv 2>/dev/null || true)"
  if [ "$st_public_access" = "Disabled" ]; then
    st_is_public_access_disabled=true
    info "Enabling public access for Storage Account: $storage_account"
    az storage account update --name "$storage_account" --resource-group "$resource_group" --public-network-access enabled --default-action Allow --output none
    info "Waiting 30 seconds for public access to propagate..."
    sleep 30
    local current_access
    for i in {1..10}; do
      current_access="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query "publicNetworkAccess" -o tsv 2>/dev/null || true)"
      if [ "$current_access" = "Enabled" ]; then
        info "✓ Storage Account public access enabled successfully"
        break
      fi
      info "Public access not yet enabled (attempt $i/10). Waiting 5 seconds..."
      sleep 5
    done
  else
    info "✓ Storage Account public access already enabled"
  fi

  local srch_public_access
  srch_public_access="$(az search service show --name "$ai_search" --resource-group "$resource_group" --query "publicNetworkAccess" -o tsv 2>/dev/null || true)"
  if [ "$srch_public_access" = "Disabled" ]; then
    srch_is_public_access_disabled=true
    info "Enabling public access for AI Search Service: $ai_search"
    az search service update --name "$ai_search" --resource-group "$resource_group" --public-network-access enabled --output none
    info "Waiting 30 seconds for public access to propagate..."
    sleep 30
    local current_access
    for i in {1..10}; do
      current_access="$(az search service show --name "$ai_search" --resource-group "$resource_group" --query "publicNetworkAccess" -o tsv 2>/dev/null || true)"
      if [ "$current_access" = "Enabled" ]; then
        info "✓ AI Search Service public access enabled successfully"
        break
      fi
      info "Public access not yet enabled (attempt $i/10). Waiting 5 seconds..."
      sleep 5
    done
  else
    info "✓ AI Search Service public access already enabled"
  fi

  if [[ "$openai_endpoint" =~ ^https?://([^.]+)\. ]]; then
    ai_foundry_account_name="${BASH_REMATCH[1]}"
  fi

  local existing_foundry_id
  existing_foundry_id="$(azd env get-value AZURE_EXISTING_AI_PROJECT_RESOURCE_ID 2>/dev/null || true)"
  if [ -n "$existing_foundry_id" ] && [[ "$existing_foundry_id" =~ /resourceGroups/([^/]+)/ ]]; then
    ai_foundry_resource_group="${BASH_REMATCH[1]}"
  else
    ai_foundry_resource_group="$resource_group"
  fi

  if [ -n "$ai_foundry_account_name" ] && [ -n "$ai_foundry_resource_group" ]; then
    local foundry_public_access
    foundry_public_access="$(az cognitiveservices account show --name "$ai_foundry_account_name" --resource-group "$ai_foundry_resource_group" --query "properties.publicNetworkAccess" -o tsv 2>/dev/null || true)"
    if [ "$foundry_public_access" = "Disabled" ]; then
      ai_foundry_is_public_access_disabled=true
      info "Enabling public access for AI Foundry: $ai_foundry_account_name (RG: $ai_foundry_resource_group)"
      az resource update --resource-group "$ai_foundry_resource_group" --name "$ai_foundry_account_name" --resource-type "Microsoft.CognitiveServices/accounts" --set properties.publicNetworkAccess=Enabled --output none
      info "Waiting 30 seconds for public access to propagate..."
      sleep 30
      local current_access
      for i in {1..10}; do
        current_access="$(az cognitiveservices account show --name "$ai_foundry_account_name" --resource-group "$ai_foundry_resource_group" --query "properties.publicNetworkAccess" -o tsv 2>/dev/null || true)"
        if [ "$current_access" = "Enabled" ]; then
          info "✓ AI Foundry public access enabled successfully"
          break
        fi
        info "Public access not yet enabled (attempt $i/10). Waiting 5 seconds..."
        sleep 5
      done
    else
      info "✓ AI Foundry public access already enabled"
    fi
  else
    warn "Could not determine AI Foundry account name/RG — skipping Foundry public-access toggle."
  fi

  info "==========================================================="
}

get_value_from_deployment() {
  local deployment_outputs="$1"
  local primary_key="$2"
  local fallback_key="$3"

  python3 - <<PY
import json
import sys
outputs = json.load(sys.stdin)
keys = ["$primary_key", "$fallback_key"]
output_keys = {k.lower(): k for k in outputs}
for key in keys:
    for candidate in [key, key.lower(), key.upper(), key.capitalize()]:
        actual = output_keys.get(candidate.lower())
        if actual and isinstance(outputs[actual], dict) and outputs[actual].get("value") is not None:
            print(outputs[actual]["value"])
            sys.exit(0)
sys.exit(1)
PY
}

get_values_from_azd_env() {
  if ! command_exists azd; then
    error "Azure Developer CLI (azd) is not installed."
    return 1
  fi

  info "Getting values from azd environment..."
  backend_url="$(azd env get-value BACKEND_URL 2>/dev/null || true)"
  storage_account="$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME 2>/dev/null || true)"
  ai_search="$(azd env get-value AZURE_AI_SEARCH_NAME 2>/dev/null || true)"
  ai_search_endpoint="$(azd env get-value AZURE_SEARCH_ENDPOINT 2>/dev/null || true)"
  if [ -z "$ai_search_endpoint" ]; then
    ai_search_endpoint="$(azd env get-value AZURE_AI_SEARCH_ENDPOINT 2>/dev/null || true)"
  fi
  openai_endpoint="$(azd env get-value AZURE_OPENAI_ENDPOINT 2>/dev/null || true)"
  project_endpoint="$(azd env get-value AZURE_AI_PROJECT_ENDPOINT 2>/dev/null || true)"
  if [ -z "$project_endpoint" ]; then
    project_endpoint="$(azd env get-value AZURE_AI_AGENT_ENDPOINT 2>/dev/null || true)"
  fi
  resource_group="$(azd env get-value AZURE_RESOURCE_GROUP 2>/dev/null || true)"

  if [ -z "$backend_url" ] || [ -z "$storage_account" ] || [ -z "$ai_search" ] || [ -z "$resource_group" ]; then
    error "Could not retrieve all required values from azd environment."
    return 1
  fi

  info "Successfully retrieved values from azd environment."
  return 0
}

get_values_from_az_deployment() {
  info "Getting values from Azure deployment outputs..."
  local deployment_name
  deployment_name="$(az group show --name "$resource_group" --query "tags.DeploymentName" -o tsv 2>/dev/null || true)"
  if [ -z "$deployment_name" ]; then
    error "Could not find deployment name in resource group tags."
    return 1
  fi

  info "Fetching deployment outputs for deployment: $deployment_name"
  local deployment_outputs
  deployment_outputs="$(az deployment group show --resource-group "$resource_group" --name "$deployment_name" --query "properties.outputs" -o json 2>/dev/null || true)"
  if [ -z "$deployment_outputs" ]; then
    error "Could not fetch deployment outputs."
    return 1
  fi

  local dep_storage_account dep_ai_search dep_backend_url dep_ai_search_endpoint dep_openai_endpoint dep_project_endpoint
  dep_storage_account="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_STORAGE_ACCOUNT_NAME" "azureStorageAccountName" 2>/dev/null || true)"
  dep_ai_search="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_AI_SEARCH_NAME" "azureAiSearchName" 2>/dev/null || true)"
  dep_backend_url="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "backenD_URL" "backendUrl" 2>/dev/null || true)"
  dep_ai_search_endpoint="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_SEARCH_ENDPOINT" "azureSearchEndpoint" 2>/dev/null || true)"
  if [ -z "$dep_ai_search_endpoint" ]; then
    dep_ai_search_endpoint="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_AI_SEARCH_ENDPOINT" "azureAiSearchEndpoint" 2>/dev/null || true)"
  fi
  dep_openai_endpoint="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_OPENAI_ENDPOINT" "azureOpenaiEndpoint" 2>/dev/null || true)"
  dep_project_endpoint="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_AI_PROJECT_ENDPOINT" "azureAiProjectEndpoint" 2>/dev/null || true)"
  if [ -z "$dep_project_endpoint" ]; then
    dep_project_endpoint="$(printf '%s' "$deployment_outputs" | get_value_from_deployment "azurE_AI_AGENT_ENDPOINT" "azureAiAgentEndpoint" 2>/dev/null || true)"
  fi

  if [ -n "$dep_storage_account" ]; then
    storage_account="$dep_storage_account"
  fi
  if [ -n "$dep_ai_search" ]; then
    ai_search="$dep_ai_search"
  fi
  if [ -n "$dep_backend_url" ]; then
    backend_url="$dep_backend_url"
  fi
  if [ -n "$dep_ai_search_endpoint" ]; then
    ai_search_endpoint="$dep_ai_search_endpoint"
  fi
  if [ -n "$dep_openai_endpoint" ]; then
    openai_endpoint="$dep_openai_endpoint"
  fi
  if [ -n "$dep_project_endpoint" ]; then
    project_endpoint="$dep_project_endpoint"
  fi

  if [ -z "$storage_account" ] || [ -z "$ai_search" ] || [ -z "$backend_url" ]; then
    error "Could not extract all required values from deployment outputs."
    return 1
  fi

  info "Successfully retrieved values from deployment outputs."
  return 0
}

get_values_using_solution_suffix() {
  info "Getting values from resource naming convention using solution suffix..."
  local solution_suffix
  solution_suffix="$(az group show --name "$resource_group" --query "tags.SolutionSuffix" -o tsv 2>/dev/null || true)"
  if [ -z "$solution_suffix" ]; then
    error "Could not find SolutionSuffix tag in resource group."
    return 1
  fi

  info "Found solution suffix: $solution_suffix"
  storage_account="${solution_suffix//-/}"
  storage_account="st$storage_account"
  ai_search="srch-$solution_suffix"
  local container_app_name="ca-$solution_suffix"

  info "Querying backend URL from Container App..."
  local backend_fqdn
  backend_fqdn="$(az containerapp show --name "$container_app_name" --resource-group "$resource_group" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || true)"
  if [ -z "$backend_fqdn" ]; then
    error "Could not get Container App FQDN. Container App may not be deployed yet."
    return 1
  fi

  backend_url="https://$backend_fqdn"
  ai_search_endpoint="https://$ai_search.search.windows.net"

  if [ -z "$storage_account" ] || [ -z "$ai_search" ] || [ -z "$backend_url" ]; then
    error "Failed to reconstruct all required resource names."
    return 1
  fi

  info "Successfully reconstructed values from resource naming convention."
  return 0
}

run_python() {
  local module="$1"
  shift
  "$python_cmd" "$REPO_ROOT/$module" "$@"
}

deploy_content_pack() {
  local pack_path="$1"
  local storage_account_name="$2"
  local ai_search_name="$3"

  local pack_json_path="$pack_path/pack.json"
  if [ ! -f "$pack_json_path" ]; then
    info "  No pack.json found at $pack_json_path - skipping data deployment."
    return 0
  fi

  info "  Deploying data for content pack: $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$pack_json_path")"
  local had_failure=false

  python3 - "$pack_json_path" <<'PY' > "$SCRIPT_DIR/.pack_items.tmp"
import json, sys
pack = json.load(open(sys.argv[1]))
root = sys.argv[1]
for item in pack.get('blob_indexes', []) or []:
    container = item.get('container')
    source = item.get('source')
    pattern = item.get('pattern') or '*'
    index_name = item.get('index_name')
    if container and source and index_name:
        print('BLOB_INDEX|{}|{}|{}|{}'.format(container, source, pattern, index_name))
for item in pack.get('blob_uploads', []) or []:
    container = item.get('container')
    source = item.get('source')
    pattern = item.get('pattern') or '*'
    if container and source:
        print('BLOB_UPLOAD|{}|{}|{}|-'.format(container, source, pattern))
for item in pack.get('search_indexes', []) or []:
    index_name = item.get('index_name')
    print('SEARCH_INDEX|-|-|-|{}'.format(index_name))
PY
  if [ $? -ne 0 ]; then
    warn "  Failed to parse pack.json; skipping."
    return 1
  fi

  local first_blob_container=""
  while IFS='|' read -r item_type container source pattern index_name; do
    case "$item_type" in
      BLOB_INDEX)
        if [ ! -d "$pack_path/$source" ]; then
          warn "  source directory not found: $pack_path/$source. Skipping."
          had_failure=true
          continue
        fi
        az storage container create --account-name "$storage_account_name" --name "$container" --auth-mode login --output none 2>/dev/null || true
        info "  Uploading blobs to container '$container'..."
        if ! az storage blob upload-batch --account-name "$storage_account_name" --destination "$container" --source "$pack_path/$source" --auth-mode login --pattern "$pattern" --overwrite --output none; then
          error "  Failed to upload blobs to container '$container'."
          had_failure=true
          continue
        fi
        first_blob_container="$container"
        info "  Creating search index '$index_name' from container '$container'..."
        if ! run_python "infra/scripts/index_datasets.py" "$storage_account_name" "$container" "$ai_search_name" "$index_name"; then
          error "  Indexing failed for '$index_name'."
          had_failure=true
        fi
        ;;
      BLOB_UPLOAD)
        if [ ! -d "$pack_path/$source" ]; then
          warn "  source directory not found: $pack_path/$source. Skipping."
          had_failure=true
          continue
        fi
        az storage container create --account-name "$storage_account_name" --name "$container" --auth-mode login --output none 2>/dev/null || true
        info "  Uploading blobs to container '$container'..."
        if ! az storage blob upload-batch --account-name "$storage_account_name" --destination "$container" --source "$pack_path/$source" --auth-mode login --pattern "$pattern" --overwrite --output none; then
          error "  Failed to upload blobs to container '$container'."
          had_failure=true
        fi
        if [ -z "$first_blob_container" ]; then
          first_blob_container="$container"
        fi
        ;;
      SEARCH_INDEX)
        if [ -z "$first_blob_container" ]; then
          warn "  No blob container found for search_index '$index_name'. Skipping."
          continue
        fi
        info "  Creating search index '$index_name' from container '$first_blob_container'..."
        if ! run_python "infra/scripts/index_datasets.py" "$storage_account_name" "$first_blob_container" "$ai_search_name" "$index_name"; then
          error "  Indexing failed for '$index_name'."
          had_failure=true
        fi
        ;;
      *)
        warn "  Unknown pack item type: $item_type"
        ;;
    esac
  done < "$SCRIPT_DIR/.pack_items.tmp"

  rm -f "$SCRIPT_DIR/.pack_items.tmp"
  if [ "$had_failure" = true ]; then
    return 1
  fi
  return 0
}

upload_team_config() {
  local label="$1"
  local team_config_dir="$2"
  local team_id="$3"

  info ""
  info "Uploading Team Configuration for $label..."
  if ! run_python "infra/scripts/upload_team_config.py" "$backend_url" "$team_config_dir" "$user_principal_id" "$team_id"; then
    error "Team configuration for $label upload failed."
    has_errors=true
    return 1
  fi
  info "Uploaded Team Configuration for $label."
  return 0
}

select_use_case() {
  echo ""
  echo "==============================================="
  echo "Available Use Cases:"
  echo "==============================================="
  echo "1. RFP Evaluation"
  echo "2. Retail Customer Satisfaction"
  echo "3. HR Employee Onboarding"
  echo "4. Marketing Press Release"
  echo "5. Contract Compliance Review"
  echo "6. Content Generation"
  echo "7. All"
  echo "==============================================="
  echo ""

  local selected=""
  while true; do
    read -rp "Please enter the number of the use case you would like to install (1-7): " selected
    case "$selected" in
      1) selected_use_case="1"; selected_use_case_label="RFP Evaluation"; break ;; 
      2) selected_use_case="2"; selected_use_case_label="Retail Customer Satisfaction"; break ;; 
      3) selected_use_case="3"; selected_use_case_label="HR Employee Onboarding"; break ;; 
      4) selected_use_case="4"; selected_use_case_label="Marketing Press Release"; break ;; 
      5) selected_use_case="5"; selected_use_case_label="Contract Compliance Review"; break ;; 
      6) selected_use_case="6"; selected_use_case_label="Content Generation"; break ;; 
      7|all) selected_use_case="7"; selected_use_case_label="All"; break ;; 
      *) warn "Invalid selection. Please enter a number from 1-7." ;;
    esac
  done
}

select_subscription() {
  if command_exists azd; then
    az_subscription_id="$(azd env get-value AZURE_SUBSCRIPTION_ID 2>/dev/null || true)"
  fi

  local current_subscription_id
  current_subscription_id="$(az account show --query id -o tsv 2>/dev/null || true)"
  local current_subscription_name
  current_subscription_name="$(az account show --query name -o tsv 2>/dev/null || true)"

  if [ -n "$az_subscription_id" ] && [ "$current_subscription_id" != "$az_subscription_id" ]; then
    echo "Current subscription is $current_subscription_name ($current_subscription_id)."
    read -rp "Do you want to continue with this subscription? (y/n) " continue_choice
    if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
      info "Available subscriptions:"
      az account list --query "[?state=='Enabled'].[name,id]" --output tsv
      read -rp "Enter the subscription ID to use: " chosen_subscription_id
      az account set --subscription "$chosen_subscription_id"
      info "Switched to subscription: $chosen_subscription_id"
      az_subscription_id="$chosen_subscription_id"
    else
      az account set --subscription "$current_subscription_id"
      az_subscription_id="$current_subscription_id"
    fi
  else
    info "Proceeding with subscription: $current_subscription_name ($current_subscription_id)"
    az account set --subscription "$current_subscription_id"
    az_subscription_id="$current_subscription_id"
  fi
}

activate_python_env() {
  if command_exists python3; then
    python_cmd="python3"
  elif command_exists python; then
    python_cmd="python"
  else
    fatal "Python not found. Install Python 3.10+ and add it to PATH."
  fi

  if [ ! -d "$venv_path" ]; then
    info "Creating virtual environment..."
    "$python_cmd" -m venv "$venv_path"
  else
    info "Virtual environment already exists. Skipping creation."
  fi

  if [ -f "$venv_path/bin/activate" ]; then
    # shellcheck disable=SC1091
    . "$venv_path/bin/activate"
  fi

  info "Installing Python dependencies..."
  pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
}

main() {
  trap restore_network_access EXIT

  echo ""
  echo "========================================"
  echo " Post-Deployment Data Seeding"
  echo "========================================"
  echo ""

  if ! az account show >/dev/null 2>&1; then
    info "Not authenticated. Logging in..."
    az login
  else
    info "Already authenticated with Azure."
  fi

  parse_args "$@"
  select_subscription

  if [ -z "$resource_group" ]; then
    if ! get_values_from_azd_env; then
      error "Failed to get values from azd environment. If you want to use deployment outputs instead, pass --resource-group <name>."
      exit 1
    fi
  fi

  if [ -n "$resource_group" ]; then
    info "Resource group: $resource_group"
    if [ -z "$backend_url" ] || [ -z "$storage_account" ] || [ -z "$ai_search" ] || [ -z "$ai_search_endpoint" ] || [ -z "$openai_endpoint" ] || [ -z "$project_endpoint" ]; then
      info "Some values are missing from azd env. Attempting to retrieve them from deployment outputs..."
      if ! get_values_from_az_deployment; then
        warn "Could not retrieve values from deployment outputs. Falling back to naming convention..."
        if ! get_values_using_solution_suffix; then
          fatal "Both fallback methods failed."
        fi
      fi
    fi
  fi

  select_use_case

  echo ""
  echo "==============================================="
  echo "Values to be used:" 
  echo "==============================================="
  echo "Selected Use Case: $selected_use_case_label"
  echo "Resource Group:    $resource_group"
  echo "Backend URL:       $backend_url"
  echo "Storage Account:   $storage_account"
  echo "AI Search:         $ai_search"
  echo "AI Project:        $project_endpoint"
  echo "Subscription ID:   $az_subscription_id"
  echo "==============================================="
  echo ""

  user_principal_id="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
  if [ -z "$user_principal_id" ]; then
    fatal "Could not retrieve signed-in user principal id."
  fi

  activate_python_env

  # Export environment variables for the seed scripts. These are populated from azd env values
  # or from Azure deployment outputs so the Python seeding scripts can run without writing .env.
  if [ -n "$project_endpoint" ]; then
    export AZURE_AI_PROJECT_ENDPOINT="$project_endpoint"
  else
    warn "AZURE_AI_PROJECT_ENDPOINT is not set. KB connection provisioning may fail."
  fi

  if [ -n "$ai_search_endpoint" ]; then
    export AZURE_AI_SEARCH_ENDPOINT="$ai_search_endpoint"
  else
    warn "AZURE_AI_SEARCH_ENDPOINT is not set. Knowledge base seeding and content indexing may fail."
  fi

  if [ -n "$openai_endpoint" ]; then
    export AZURE_OPENAI_ENDPOINT="$openai_endpoint"
  else
    warn "AZURE_OPENAI_ENDPOINT is not set. Knowledge base reasoning may fall back to default or fail."
  fi

  local uses_data=false
  case "$selected_use_case" in
    1|2|5|6|7) uses_data=true ;; 
  esac

  if [ "$uses_data" = true ]; then
    enable_public_access_if_waf
  fi

  local is_team_config_failed=false
  local is_sample_data_failed=false

  if [[ "$selected_use_case" == "3" || "$selected_use_case" == "7" ]]; then
    if ! upload_team_config "HR Employee Onboarding" "content_packs/hr_onboarding/agent_teams" "00000000-0000-0000-0000-000000000001"; then
      is_team_config_failed=true
    fi
  fi

  if [[ "$selected_use_case" == "4" || "$selected_use_case" == "7" ]]; then
    if ! upload_team_config "Marketing Press Release" "content_packs/marketing_press_release/agent_teams" "00000000-0000-0000-0000-000000000002"; then
      is_team_config_failed=true
    fi
  fi

  if [[ "$selected_use_case" == "1" || "$selected_use_case" == "7" ]]; then
    if ! upload_team_config "RFP Evaluation" "content_packs/rfp_evaluation/agent_teams" "00000000-0000-0000-0000-000000000004"; then
      is_team_config_failed=true
    fi
    info "Deploying data for RFP Evaluation content pack..."
    if ! deploy_content_pack "content_packs/rfp_evaluation" "$storage_account" "$ai_search"; then
      error "Data deployment for RFP Evaluation failed."
      is_sample_data_failed=true
    fi
  fi

  if [[ "$selected_use_case" == "5" || "$selected_use_case" == "7" ]]; then
    if ! upload_team_config "Contract Compliance Review" "content_packs/contract_compliance/agent_teams" "00000000-0000-0000-0000-000000000005"; then
      is_team_config_failed=true
    fi
    info "Deploying data for Contract Compliance content pack..."
    if ! deploy_content_pack "content_packs/contract_compliance" "$storage_account" "$ai_search"; then
      error "Data deployment for Contract Compliance failed."
      is_sample_data_failed=true
    fi
  fi

  if [[ "$selected_use_case" == "2" || "$selected_use_case" == "7" ]]; then
    if ! upload_team_config "Retail Customer Satisfaction" "content_packs/retail_customer/agent_teams" "00000000-0000-0000-0000-000000000003"; then
      is_team_config_failed=true
    fi
    info "Deploying data for Retail Customer content pack..."
    if ! deploy_content_pack "content_packs/retail_customer" "$storage_account" "$ai_search"; then
      error "Data deployment for Retail Customer Satisfaction failed."
      is_sample_data_failed=true
    fi
  fi

  if [[ "$selected_use_case" == "6" || "$selected_use_case" == "7" ]]; then
    if ! upload_team_config "Content Generation" "content_packs/content_gen/agent_teams" "00000000-0000-0000-0000-000000000007"; then
      is_team_config_failed=true
    fi
    info "Deploying data for Content Generation content pack..."
    if ! deploy_content_pack "content_packs/content_gen" "$storage_account" "$ai_search"; then
      error "Data deployment for Content Generation failed."
      is_sample_data_failed=true
    fi
  fi

  if [ "$is_team_config_failed" = true ] || [ "$is_sample_data_failed" = true ]; then
    has_errors=true
    warn "One or more tasks failed. Please review the messages above."
  fi

  if [ "$uses_data" = true ] && [ "$is_sample_data_failed" = false ]; then
    declare -A vector_store_map
    vector_store_map[1]=""
    vector_store_map[2]="macae-retail-customer-data,macae-retail-order-data"
    vector_store_map[5]=""
    vector_store_map[6]=""
    vector_store_map[7]="macae-retail-customer-data,macae-retail-order-data"

    declare -A kb_map
    kb_map[1]="macae-rfp-summary-kb,macae-rfp-risk-kb,macae-rfp-compliance-kb"
    kb_map[2]="macae-retail-customer-kb,macae-retail-orders-kb"
    kb_map[5]="macae-contract-summary-kb,macae-contract-risk-kb,macae-contract-compliance-kb"
    kb_map[6]="macae-content-gen-products-kb"
    kb_map[7]="macae-retail-customer-kb,macae-retail-orders-kb,macae-content-gen-products-kb,macae-contract-summary-kb,macae-contract-risk-kb,macae-contract-compliance-kb,macae-rfp-summary-kb,macae-rfp-risk-kb,macae-rfp-compliance-kb"

    local selected_vector_stores="${vector_store_map[$selected_use_case]}"
    local selected_kbs="${kb_map[$selected_use_case]}"

    if [ -n "$selected_vector_stores" ]; then
      info ""
      info "── Creating vector stores ──"
      if ! run_python "infra/scripts/seed_vector_stores.py" "--only" "$selected_vector_stores"; then
        error "Vector store creation failed. Run 'python infra/scripts/seed_vector_stores.py --only $selected_vector_stores' manually."
        has_errors=true
      else
        info "Vector stores created successfully."
      fi
    fi

    if [ -n "$selected_kbs" ]; then
      info ""
      info "── Seeding Foundry IQ Knowledge Bases ──"
      if ! run_python "infra/scripts/seed_knowledge_bases.py" "--only" "$selected_kbs"; then
        error "Knowledge base seeding failed. Run 'python infra/scripts/seed_knowledge_bases.py --only $selected_kbs' manually."
        has_errors=true
      else
        info "Knowledge bases seeded successfully."
      fi

      info ""
      info "── Creating KB MCP RemoteTool connections ──"
      if ! run_python "infra/scripts/seed_kb_connections.py" "--only" "$selected_kbs"; then
        error "KB connection provisioning failed. Run 'python infra/scripts/seed_kb_connections.py --only $selected_kbs' manually."
        has_errors=true
      else
        info "KB MCP connections created successfully."
      fi
    fi
  fi

  echo ""
  if [ "$has_errors" = true ]; then
    echo "========================================"
    echo " Post-deployment seeding completed with ERRORS"
    echo "========================================"
    frontend_host="$(azd env get-value webSiteDefaultHostname 2>/dev/null || true)"
    if [ -n "$frontend_host" ]; then
      echo "Frontend: https://$frontend_host"
    fi
    echo ""
    exit 1
  else
    echo "========================================"
    echo " Post-deployment data seeding complete!"
    echo "========================================"
    frontend_host="$(azd env get-value webSiteDefaultHostname 2>/dev/null || true)"
    if [ -n "$frontend_host" ]; then
      echo "Frontend: https://$frontend_host"
    fi
    echo ""
  fi
}

main "$@"

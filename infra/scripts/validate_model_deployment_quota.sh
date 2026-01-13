#!/bin/bash

SUBSCRIPTION_ID=""
LOCATION=""
MODELS_PARAMETER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subscription)
      SUBSCRIPTION_ID="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    --models-parameter)
      MODELS_PARAMETER="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Verify all required parameters are provided and echo missing ones
MISSING_PARAMS=()

if [[ -z "$SUBSCRIPTION_ID" ]]; then
    MISSING_PARAMS+=("subscription")
fi

if [[ -z "$LOCATION" ]]; then
    MISSING_PARAMS+=("location")
fi

if [[ -z "$MODELS_PARAMETER" ]]; then
    MISSING_PARAMS+=("models-parameter")
fi

if [[ ${#MISSING_PARAMS[@]} -ne 0 ]]; then
    echo "❌ ERROR: Missing required parameters: ${MISSING_PARAMS[*]}"
    echo "Usage: $0 --subscription <SUBSCRIPTION_ID> --location <LOCATION> --models-parameter <MODELS_PARAMETER>"
    exit 1
fi

aiModelDeployments=$(jq -c ".parameters.$MODELS_PARAMETER.value[]" ./infra/main.parameters.json)

if [ $? -ne 0 ]; then
  echo "Error: Failed to parse main.parameters.json. Ensure jq is installed and the JSON file is valid."
  exit 1
fi

az account set --subscription "$SUBSCRIPTION_ID"
echo "🎯 Active Subscription: $(az account show --query '[name, id]' --output tsv)"

quotaAvailable=true

while IFS= read -r deployment; do
  name=$(echo "$deployment" | jq -r '.name')
  model=$(echo "$deployment" | jq -r '.model.name')
  type=$(echo "$deployment" | jq -r '.sku.name')
  capacity=$(echo "$deployment" | jq -r '.sku.capacity')

  echo "🔍 Validating model deployment: $name ..."
    ./infra/scripts/validate_model_quota.sh --location "$LOCATION" --model "$model" --capacity $capacity --deployment-type $type

  # Check if the script failed
  exit_code=$?
  if [ $exit_code -ne 0 ]; then
      if [ $exit_code -eq 2 ]; then
          # Skip printing any quota validation error — already handled inside the validation script
          exit 1
      fi
      echo "❌ ERROR: Quota validation failed for model deployment: $name"
      quotaAvailable=false
  fi
done <<< "$(echo "$aiModelDeployments")"

if [ "$quotaAvailable" = false ]; then
    echo "❌ ERROR: One or more model deployments failed validation."
    exit 1
else
    echo "✅ All model deployments passed quota validation successfully."
    exit 0
fi
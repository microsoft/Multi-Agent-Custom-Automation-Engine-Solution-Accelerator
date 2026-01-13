#!/bin/bash

LOCATION=""
MODEL=""
DEPLOYMENT_TYPE="GlobalStandard"
CAPACITY=0

ALL_REGIONS=('australiaeast' 'eastus2' 'francecentral' 'japaneast' 'norwayeast' 'swedencentral' 'uksouth' 'westus')

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --capacity)
      CAPACITY="$2"
      shift 2
      ;;
    --deployment-type)
      DEPLOYMENT_TYPE="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required params
MISSING_PARAMS=()
[[ -z "$LOCATION" ]] && MISSING_PARAMS+=("location")
[[ -z "$MODEL" ]] && MISSING_PARAMS+=("model")
[[ -z "$CAPACITY" ]] && MISSING_PARAMS+=("capacity")

if [[ ${#MISSING_PARAMS[@]} -ne 0 ]]; then
  echo "❌ ERROR: Missing required parameters: ${MISSING_PARAMS[*]}"
  echo "Usage: $0 --location <LOCATION> --model <MODEL> --capacity <CAPACITY> [--deployment-type <DEPLOYMENT_TYPE>]"
  exit 1
fi

if [[ "$DEPLOYMENT_TYPE" != "Standard" && "$DEPLOYMENT_TYPE" != "GlobalStandard" ]]; then
  echo "❌ ERROR: Invalid deployment type: $DEPLOYMENT_TYPE. Allowed values are 'Standard' or 'GlobalStandard'."
  exit 1
fi

MODEL_TYPE="OpenAI.$DEPLOYMENT_TYPE.$MODEL"

declare -a FALLBACK_REGIONS=()
ROW_NO=1

printf "\n%-5s | %-20s | %-40s | %-10s | %-10s | %-10s\n" "No." "Region" "Model Name" "Limit" "Used" "Available"
printf -- "---------------------------------------------------------------------------------------------------------------------\n"

for region in "${ALL_REGIONS[@]}"; do
  MODEL_INFO=$(az cognitiveservices usage list --location "$region" --query "[?name.value=='$MODEL_TYPE']" --output json 2>/dev/null)

  if [[ -n "$MODEL_INFO" && "$MODEL_INFO" != "[]" ]]; then
    CURRENT_VALUE=$(echo "$MODEL_INFO" | jq -r '.[0].currentValue // 0' | cut -d'.' -f1)
    LIMIT=$(echo "$MODEL_INFO" | jq -r '.[0].limit // 0' | cut -d'.' -f1)
    AVAILABLE=$((LIMIT - CURRENT_VALUE))

    printf "%-5s | %-20s | %-40s | %-10s | %-10s | %-10s\n" "$ROW_NO" "$region" "$MODEL_TYPE" "$LIMIT" "$CURRENT_VALUE" "$AVAILABLE"

    if [[ "$region" == "$LOCATION" && "$AVAILABLE" -ge "$CAPACITY" ]]; then
      echo -e "\n✅ Sufficient quota available in user-specified region: $LOCATION"
      exit 0
    fi

    if [[ "$region" != "$LOCATION" && "$AVAILABLE" -ge "$CAPACITY" ]]; then
      FALLBACK_REGIONS+=("$region ($AVAILABLE)")
    fi
  fi

  ((ROW_NO++))
done

printf -- "---------------------------------------------------------------------------------------------------------------------\n"

if [[ "${#FALLBACK_REGIONS[@]}" -gt 0 ]]; then
  echo -e "\n❌ Deployment cannot proceed because the original region '$LOCATION' lacks sufficient quota."
  echo "➡️  You can retry using one of the following regions with sufficient quota:"
  for fallback in "${FALLBACK_REGIONS[@]}"; do
    echo "   • $fallback"
  done
  echo -e "\n🔧 To proceed, run:"
  echo "    azd env set AZURE_ENV_OPENAI_LOCATION '<region>'"
  echo "📌 To confirm it's set correctly, run:"
  echo "    azd env get-value AZURE_ENV_OPENAI_LOCATION"
  echo "▶️  Once confirmed, re-run azd up to deploy the model in the new region."
  exit 2
fi

echo "❌ ERROR: No available quota found in any of the fallback regions."
exit 1

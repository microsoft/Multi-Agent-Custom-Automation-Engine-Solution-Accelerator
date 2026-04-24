#!/bin/sh
# Pre-provision hook: Informs users how to check for and purge soft-deleted
# Key Vault and Cognitive Services resources before deployment.
# Explains that if redeploying in the same environment, deployment can fail if
# resources with the same name exist in a soft-deleted state. Shows the user
# commands to check and purge, then prompts to proceed or abort.

# Sanitize AZURE_ENV_NAME to match Bicep solutionSuffix logic:
# toLower, strip: - _ . / space *
sanitize_env_name() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | tr -d ' _./*-'
}

if [ -z "$AZURE_ENV_NAME" ]; then
    printf "\033[0;31mWARNING: AZURE_ENV_NAME is not set. Cannot determine resource name patterns.\033[0m\n"
    printf "\033[1;33mPlease ensure you are running this via 'azd provision' or 'azd up'.\033[0m\n"
    exit 1
fi

SANITIZED_NAME=$(sanitize_env_name "$AZURE_ENV_NAME")

printf "\n"
printf "\033[1;33m===============================================================\n"
printf "\033[0;32m SOFT-DELETE RESOURCE CHECK\n"
printf "\033[1;33m===============================================================\033[0m\n"
printf "\n"
printf "If you are redeploying in the same environment, deployment can fail\n"
printf "if Key Vault or Cognitive Services accounts with the same name\n"
printf "exist in a soft-deleted state.\n"
printf "\n"
printf "\033[0;36mExpected resource name patterns (based on AZURE_ENV_NAME='%s'):\033[0m\n" "$AZURE_ENV_NAME"
printf "  Key Vault:          kv-%s*\n" "$SANITIZED_NAME"
printf "  Cognitive Services: aif-%s*\n" "$SANITIZED_NAME"
printf "\n"
printf "\033[1;33mPlease open a SEPARATE terminal to check and purge any soft-deleted resources,\n"
printf "then come back to THIS terminal to continue the deployment.\033[0m\n"
printf "\n"
printf "\033[0;36mSteps:\033[0m\n"
printf "\n"
printf "  1. Check for soft-deleted Key Vaults:\n"
printf "       \033[0;36maz keyvault list-deleted --query \"[?starts_with(name, 'kv-%s')].[name, properties.location, properties.deletionDate]\" -o table\033[0m\n" "$SANITIZED_NAME"
printf "\n"
printf "  2. Check for soft-deleted Cognitive Services accounts:\n"
printf "       \033[0;36maz cognitiveservices account list-deleted --query \"[?starts_with(name, 'aif-%s')].[name, location, resourceGroup, deletionDate]\" -o table\033[0m\n" "$SANITIZED_NAME"
printf "\n"
printf "  3. If soft-deleted Key Vaults are found, purge them:\n"
printf "       \033[0;36maz keyvault purge --name <name> --location <location>\033[0m\n"
printf "\n"
printf "  4. If soft-deleted Cognitive Services accounts are found, purge them:\n"
printf "       \033[0;36maz cognitiveservices account purge --name <name> --location <location> --resource-group <resource-group>\033[0m\n"
printf "\n"
printf "\033[1;33m  If not purged, deployment may fail with 'FlagMustBeSetForRestore' or\n"
printf "  'CustomDomainInUse' errors.\033[0m\n"
printf "\n"
printf "\033[1;33m===============================================================\033[0m\n"
printf "\n"

while true; do
    printf "Do you want to proceed with deployment? (y/n): "
    read response

    case "$response" in
        y|Y)
            printf "\n"
            printf "\033[0;32mProceeding with deployment...\033[0m\n"
            exit 0
            ;;
        n|N)
            printf "\n"
            printf "\033[0;31mDeployment aborted by user.\033[0m\n"
            exit 1
            ;;
        *)
            printf "\033[1;33mInvalid input. Please enter 'y' or 'n'.\033[0m\n"
            ;;
    esac
done

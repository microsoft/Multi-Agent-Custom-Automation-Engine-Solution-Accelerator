#!/bin/sh
# Pre-provision hook: Detects and purges soft-deleted Key Vault and
# Cognitive Services resources that would conflict with deployment.
# Automatically lists soft-deleted resources matching the expected naming
# pattern, displays them, and offers to purge all, selected ones, or abort.

# Sanitize AZURE_ENV_NAME to match Bicep solutionSuffix logic:
# toLower, strip: - _ . / space *
sanitize_env_name() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | tr -d ' _./*-'
}

if [ -z "$AZURE_ENV_NAME" ]; then
    printf "\033[0;31mWARNING: AZURE_ENV_NAME is not set. Cannot determine resource names.\033[0m\n"
    printf "\033[1;33mPlease ensure you are running this via 'azd provision' or 'azd up'.\033[0m\n"
    exit 1
fi

SANITIZED_NAME=$(sanitize_env_name "$AZURE_ENV_NAME")

printf "\n"
printf "\033[1;33m===============================================================\n"
printf "\033[0;32m SOFT-DELETE RESOURCE CHECK\n"
printf "\033[1;33m===============================================================\033[0m\n"
printf "\n"
printf "\033[0;36mChecking for soft-deleted resources that may conflict with deployment...\033[0m\n"
printf "\n"

# Temporary file to store resource list
RESOURCE_FILE=$(mktemp)
RESOURCE_COUNT=0

# Check soft-deleted Key Vaults
printf "Checking soft-deleted Key Vaults...\n"
kv_output=$(az keyvault list-deleted --query "[?starts_with(name, 'kv-${SANITIZED_NAME}')].[name, properties.location, properties.deletionDate]" -o tsv 2>/dev/null)

if [ -n "$kv_output" ]; then
    echo "$kv_output" | while IFS='	' read -r name location deletion_date; do
        if [ -n "$name" ]; then
            RESOURCE_COUNT=$((RESOURCE_COUNT + 1))
            echo "KeyVault	${name}	${location}	-	${deletion_date}" >> "$RESOURCE_FILE"
        fi
    done
fi

# Check soft-deleted Cognitive Services accounts
printf "Checking soft-deleted Cognitive Services accounts...\n"
cs_output=$(az cognitiveservices account list-deleted --query "[?starts_with(name, 'aif-${SANITIZED_NAME}')].[name, location, resourceGroup, deletionDate]" -o tsv 2>/dev/null)

if [ -n "$cs_output" ]; then
    echo "$cs_output" | while IFS='	' read -r name location rg deletion_date; do
        if [ -n "$name" ]; then
            echo "CognitiveServices	${name}	${location}	${rg}	${deletion_date}" >> "$RESOURCE_FILE"
        fi
    done
fi

printf "\n"

# Check if any resources were found
if [ ! -s "$RESOURCE_FILE" ]; then
    printf "\033[0;32mNo soft-deleted resources found matching pattern. Proceeding with deployment.\033[0m\n"
    printf "\n"
    rm -f "$RESOURCE_FILE"
    exit 0
fi

# Count and display resources
TOTAL=$(wc -l < "$RESOURCE_FILE" | tr -d ' ')
printf "\033[1;33mFound %s soft-deleted resource(s) that may conflict with deployment:\033[0m\n" "$TOTAL"
printf "\n"
printf "\033[0;36m%-5s %-22s %-30s %-18s %-20s %s\033[0m\n" "#" "Type" "Name" "Location" "Resource Group" "Deletion Date"
printf "%-5s %-22s %-30s %-18s %-20s %s\n" "---" "----" "----" "--------" "--------------" "-------------"

INDEX=1
while IFS='	' read -r type name location rg deletion_date; do
    printf "%-5s %-22s %-30s %-18s %-20s %s\n" "$INDEX" "$type" "$name" "$location" "$rg" "$deletion_date"
    INDEX=$((INDEX + 1))
done < "$RESOURCE_FILE"

printf "\n"
printf "\033[1;33mIf not purged, deployment may fail with 'FlagMustBeSetForRestore' or\n"
printf "'CustomDomainInUse' errors.\033[0m\n"
printf "\n"

# Prompt user
while true; do
    printf "\033[0;36mOptions:\033[0m\n"
    printf "  a             - Purge ALL listed resources\n"
    printf "  1,2,3,...     - Purge specific resources (comma-separated numbers)\n"
    printf "  n             - Abort deployment\n"
    printf "\n"
    printf "Enter your choice: "
    read response

    case "$response" in
        a|A)
            SELECTED="all"
            break
            ;;
        n|N)
            printf "\n"
            printf "\033[0;31mDeployment aborted. Please purge the soft-deleted resources manually before redeploying.\033[0m\n"
            rm -f "$RESOURCE_FILE"
            exit 1
            ;;
        *)
            # Validate comma-separated numbers
            valid=true
            echo "$response" | tr ',' '\n' | while read -r num; do
                num=$(echo "$num" | tr -d ' ')
                case "$num" in
                    ''|*[!0-9]*) valid=false ;;
                    *)
                        if [ "$num" -lt 1 ] || [ "$num" -gt "$TOTAL" ]; then
                            valid=false
                        fi
                        ;;
                esac
            done
            # Re-validate outside subshell
            VALID_INPUT=true
            for num in $(echo "$response" | tr ',' ' '); do
                num=$(echo "$num" | tr -d ' ')
                case "$num" in
                    ''|*[!0-9]*)
                        VALID_INPUT=false
                        break
                        ;;
                    *)
                        if [ "$num" -lt 1 ] 2>/dev/null || [ "$num" -gt "$TOTAL" ] 2>/dev/null; then
                            VALID_INPUT=false
                            break
                        fi
                        ;;
                esac
            done
            if [ "$VALID_INPUT" = true ] && [ -n "$response" ]; then
                SELECTED="$response"
                break
            else
                printf "\033[1;33mInvalid input. Please enter 'a', 'n', or comma-separated numbers (e.g., 1,3).\033[0m\n"
            fi
            ;;
    esac
done

# Purge selected resources
printf "\n"
FAILED=false
INDEX=1
while IFS='	' read -r type name location rg deletion_date; do
    SHOULD_PURGE=false

    if [ "$SELECTED" = "all" ]; then
        SHOULD_PURGE=true
    else
        for num in $(echo "$SELECTED" | tr ',' ' '); do
            num=$(echo "$num" | tr -d ' ')
            if [ "$num" = "$INDEX" ]; then
                SHOULD_PURGE=true
                break
            fi
        done
    fi

    if [ "$SHOULD_PURGE" = true ]; then
        printf "\033[0;36mPurging %s: %s (location: %s)...\033[0m\n" "$type" "$name" "$location"

        if [ "$type" = "KeyVault" ]; then
            az keyvault purge --name "$name" --location "$location" 2>/dev/null
        elif [ "$type" = "CognitiveServices" ]; then
            az cognitiveservices account purge --name "$name" --location "$location" --resource-group "$rg" 2>/dev/null
        fi

        if [ $? -ne 0 ]; then
            printf "\033[0;31m  Failed to purge %s. Please purge manually.\033[0m\n" "$name"
            FAILED=true
        else
            printf "\033[0;32m  Successfully purged %s.\033[0m\n" "$name"
        fi
    fi

    INDEX=$((INDEX + 1))
done < "$RESOURCE_FILE"

rm -f "$RESOURCE_FILE"

if [ "$FAILED" = true ]; then
    printf "\n"
    printf "\033[0;31mOne or more resources failed to purge. Deployment aborted.\033[0m\n"
    exit 1
fi

printf "\n"
printf "\033[0;32mAll selected resources purged successfully. Proceeding with deployment.\033[0m\n"
exit 0

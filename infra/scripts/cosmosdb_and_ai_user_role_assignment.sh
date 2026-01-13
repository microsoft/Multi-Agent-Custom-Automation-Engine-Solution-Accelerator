#!/bin/bash

# Variables

principal_ids="$1"
cosmosDbAccountName="$2"
resourceGroupName="$3"
managedIdentityClientId="$4"
aif_resource_id="${5}"

# Function to merge and deduplicate principal IDs
merge_principal_ids() {
    local param_ids="$1"
    local env_ids="$2"
    local all_ids=""
    
    # Add parameter IDs if provided
    if [ -n "$param_ids" ]; then
        all_ids="$param_ids"
    fi

    signed_user_id=$(az ad signed-in-user show --query id -o tsv)

    # Add environment variable IDs if provided
    if [ -n "$env_ids" ]; then
        if [ -n "$all_ids" ]; then
            all_ids="$all_ids,$env_ids"
        else
            all_ids="$env_ids"
        fi
    fi
    
    all_ids="$all_ids,$signed_user_id"
    # Remove duplicates and return
    if [ -n "$all_ids" ]; then
        # Convert to array, remove duplicates, and join back
        IFS=',' read -r -a ids_array <<< "$all_ids"
        declare -A unique_ids
        for id in "${ids_array[@]}"; do
            # Trim whitespace
            id=$(echo "$id" | xargs)
            if [ -n "$id" ]; then
                unique_ids["$id"]=1
            fi
        done
        
        # Join unique IDs back with commas
        local result=""
        for id in "${!unique_ids[@]}"; do
            if [ -n "$result" ]; then
                result="$result,$id"
            else
                result="$id"
            fi
        done
        echo "$result"
    fi
}


# get parameters from azd env, if not provided
if [ -z "$resourceGroupName" ]; then
    resourceGroupName=$(azd env get-value AZURE_RESOURCE_GROUP)
fi

if [ -z "$cosmosDbAccountName" ]; then
    cosmosDbAccountName=$(azd env get-value COSMOSDB_ACCOUNT_NAME)
fi

if [ -z "$aif_resource_id" ]; then
    aif_resource_id=$(azd env get-value AI_FOUNDRY_RESOURCE_ID)
fi

azSubscriptionId=$(azd env get-value AZURE_SUBSCRIPTION_ID)
env_principal_ids=$(azd env get-value PRINCIPAL_IDS)

# Merge principal IDs from parameter and environment variable
principal_ids=$(merge_principal_ids "$principal_ids_param" "$env_principal_ids")

# Check if all required arguments are provided
if [ -z "$principal_ids" ] || [ -z "$cosmosDbAccountName" ] || [ -z "$resourceGroupName" ] || [ -z "$aif_resource_id" ] ; then
    echo "Usage: $0 <principal_ids> <cosmosDbAccountName> <resourceGroupName> <managedIdentityClientId> <aif_resource_id>"
    exit 1
fi

echo "Using principal IDs: $principal_ids"

# Authenticate with Azure
if az account show &> /dev/null; then
    echo "Already authenticated with Azure."
else
    if [ -n "$managedIdentityClientId" ]; then
        # Use managed identity if running in Azure
        echo "Authenticating with Managed Identity..."
        az login --identity --client-id ${managedIdentityClientId}
    else
        # Use Azure CLI login if running locally
        echo "Authenticating with Azure CLI..."
        az login
    fi
    echo "Not authenticated with Azure. Attempting to authenticate..."
fi

#check if user has selected the correct subscription
currentSubscriptionId=$(az account show --query id -o tsv)
currentSubscriptionName=$(az account show --query name -o tsv)
if [ "$currentSubscriptionId" != "$azSubscriptionId" ]; then
    echo "Current selected subscription is $currentSubscriptionName ( $currentSubscriptionId )."
    read -rp "Do you want to continue with this subscription?(y/n): " confirmation
    if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
        echo "Fetching available subscriptions..."
        availableSubscriptions=$(az account list --query "[?state=='Enabled'].[name,id]" --output tsv)
        while true; do
            echo ""
            echo "Available Subscriptions:"
            echo "========================"
            echo "$availableSubscriptions" | awk '{printf "%d. %s ( %s )\n", NR, $1, $2}'
            echo "========================"
            echo ""
            read -rp "Enter the number of the subscription (1-$(echo "$availableSubscriptions" | wc -l)) to use: " subscriptionIndex
            if [[ "$subscriptionIndex" =~ ^[0-9]+$ ]] && [ "$subscriptionIndex" -ge 1 ] && [ "$subscriptionIndex" -le $(echo "$availableSubscriptions" | wc -l) ]; then
                selectedSubscription=$(echo "$availableSubscriptions" | sed -n "${subscriptionIndex}p")
                selectedSubscriptionName=$(echo "$selectedSubscription" | cut -f1)
                selectedSubscriptionId=$(echo "$selectedSubscription" | cut -f2)

                # Set the selected subscription
                if  az account set --subscription "$selectedSubscriptionId"; then
                    echo "Switched to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )"
                    break
                else
                    echo "Failed to switch to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )."
                fi
            else
                echo "Invalid selection. Please try again."
            fi
        done
    else
        echo "Proceeding with the current subscription: $currentSubscriptionName ( $currentSubscriptionId )"
        az account set --subscription "$currentSubscriptionId"
    fi
else
    echo "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    az account set --subscription "$currentSubscriptionId"
fi

# Call add_cosmosdb_access.sh
echo "Running add_cosmosdb_access.sh"
bash infra/scripts/add_cosmosdb_access.sh "$resourceGroupName" "$cosmosDbAccountName" "$principal_ids" "$managedIdentityClientId" 
if [ $? -ne 0 ]; then
    echo "Error: add_cosmosdb_access.sh failed."
    exit 1
fi
echo "add_cosmosdb_access.sh completed successfully."


# Call add_cosmosdb_access.sh
echo "Running assign_azure_ai_user_role.sh"
bash infra/scripts/assign_azure_ai_user_role.sh "$resourceGroupName" "$aif_resource_id" "$principal_ids" "$managedIdentityClientId"
if [ $? -ne 0 ]; then
    echo "Error: assign_azure_ai_user_role.sh failed."
    exit 1
fi
echo "assign_azure_ai_user_role.sh completed successfully."
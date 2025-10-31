#!/bin/bash

# Variables
resourceGroup="$1"

directoryPath=""
backendUrl=""
storageAccount=""
blobContainer=""
aiSearch=""
aiSearchIndex=""
azSubscriptionId=""

# check if azd cli is installed
check_azd_installed() {
    if command -v azd &> /dev/null; then
        return 0
    else
        return 1
    fi
}

get_values_from_azd_env() {
    check_azd_installed
    if [ $? -ne 0 ]; then
        echo "Error: Azure Developer CLI is not installed."
        return 1
    fi

    echo "Getting values from azd environment..."
    
    directoryPath="data/agent_teams"
    backendUrl=$(azd env get-value BACKEND_URL)
    storageAccount=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
    blobContainer=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME)
    aiSearch=$(azd env get-value AZURE_AI_SEARCH_NAME)
    aiSearchIndex=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME)
    resourceGroup=$(azd env get-value AZURE_RESOURCE_GROUP)
    
    # Validate that we got all required values
    if [ -z "$backendUrl" ] || [ -z "$storageAccount" ] || [ -z "$blobContainer" ] || [ -z "$aiSearch" ] || [ -z "$aiSearchIndex" ] || [ -z "$resourceGroup" ]; then
        echo "Error: Could not retrieve all required values from azd environment."
        return 1
    fi
    
    echo "Successfully retrieved values from azd environment."
    return 0
}

get_values_from_az_deployment() {
    echo "Getting values from Azure deployment outputs..."
    
    directoryPath="data/agent_teams"
    
    echo "Fetching deployment name..."
    deploymentName=$(az group show --name "$resourceGroup" --query "tags.DeploymentName" -o tsv)
    if [ -z "$deploymentName" ]; then
        echo "Error: Could not find deployment name in resource group tags."
        return 1
    fi
    
    echo "Fetching deployment outputs for deployment: $deploymentName"
    deploymentOutputs=$(az deployment group show --resource-group "$resourceGroup" --name "$deploymentName" --query "properties.outputs" -o json)
    if [ -z "$deploymentOutputs" ]; then
        echo "Error: Could not fetch deployment outputs."
        return 1
    fi
    
    # Extract specific outputs
    storageAccount=$(echo "$deploymentOutputs" | grep -A 3 '"azurE_STORAGE_ACCOUNT_NAME"' | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    blobContainer=$(echo "$deploymentOutputs" | grep -A 3 '"azurE_STORAGE_CONTAINER_NAME"' | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    aiSearch=$(echo "$deploymentOutputs" | grep -A 3 '"azurE_AI_SEARCH_NAME"' | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    aiSearchIndex=$(echo "$deploymentOutputs" | grep -A 3 '"azurE_AI_SEARCH_INDEX_NAME"' | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    backendUrl=$(echo "$deploymentOutputs" | grep -A 3 '"backenD_URL"' | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    
    # Validate that we extracted all required values
    if [ -z "$storageAccount" ] || [ -z "$blobContainer" ] || [ -z "$aiSearch" ] || [ -z "$aiSearchIndex" ] || [ -z "$backendUrl" ]; then
        echo "Error: Could not extract all required values from deployment outputs."
        return 1
    fi
    
    echo "Successfully retrieved values from deployment outputs."
    return 0
}

# Authenticate with Azure
if az account show &> /dev/null; then
    echo "Already authenticated with Azure."
else
    echo "Not authenticated with Azure. Attempting to authenticate..."
    echo "Authenticating with Azure CLI..."
    az login
fi

if check_azd_installed; then
    azSubscriptionId=$(azd env get-value AZURE_SUBSCRIPTION_ID) || azSubscriptionId="$AZURE_SUBSCRIPTION_ID" || azSubscriptionId=""
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
                    azSubscriptionId="$selectedSubscriptionId"
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
        azSubscriptionId="$currentSubscriptionId"
    fi
else
    echo "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    az account set --subscription "$currentSubscriptionId"
    azSubscriptionId="$currentSubscriptionId"
fi


if [ -z "$resourceGroup" ]; then
    # No resource group provided - use azd env
    if ! get_values_from_azd_env; then
        echo "Failed to get values from azd environment."
        echo "If you want to use deployment outputs instead, please provide the resource group name as an argument."
        echo "Usage: $0 [ResourceGroupName]"
        exit 1
    fi
else
    # Resource group provided - use deployment outputs
    echo "Resource group provided: $resourceGroup"
    
    # Call deployment function
    if ! get_values_from_az_deployment; then
        echo "Failed to get values from deployment outputs."
        exit 1
    fi
fi

echo ""
echo "==============================================="
echo "Values to be used:"
echo "==============================================="
echo "Resource Group: $resourceGroup"
echo "Backend URL: $backendUrl"
echo "Storage Account: $storageAccount"
echo "Blob Container: $blobContainer"
echo "AI Search: $aiSearch"
echo "AI Search Index: $aiSearchIndex"
echo "Directory Path: $directoryPath"
echo "Subscription ID: $azSubscriptionId"
echo "==============================================="
echo ""

isTeamConfigFailed=false
isSampleDataFailed=false

echo "Uploading team configuration..."
bash infra/scripts/upload_team_config.sh "$backendUrl" "$directoryPath" "$azSubscriptionId"
if [ $? -ne 0 ]; then
    echo "Error: Team configuration upload failed."
    isTeamConfigFailed=true
fi

echo ""
echo "----------------------------------------"
echo "----------------------------------------"
echo ""

echo "Processing sample data..."
bash infra/scripts/process_sample_data.sh "$storageAccount" "$blobContainer" "$aiSearch" "$aiSearchIndex" "$resourceGroup" "$azSubscriptionId"
if [ $? -ne 0 ]; then
    echo "Error: Sample data processing failed."
    isSampleDataFailed=true
fi

if [ "$isTeamConfigFailed" = true ] || [ "$isSampleDataFailed" = true ]; then
    echo "One or more processes failed."
    exit 1
fi

echo "Both team configuration upload and sample data processing completed successfully."
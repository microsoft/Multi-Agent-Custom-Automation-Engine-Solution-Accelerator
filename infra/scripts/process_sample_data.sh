#!/bin/bash

# Variables
storageAccount="$1"
blobContainer="$2"
aiSearch="$3"
aiSearchIndex="$4"
resourceGroup="$5"
azSubscriptionId="$6"

# get parameters from azd env, if not provided
if [ -z "$storageAccount" ]; then
    storageAccount=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
fi

if [ -z "$blobContainer" ]; then
    blobContainer=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME)
fi

if [ -z "$aiSearch" ]; then
    aiSearch=$(azd env get-value AZURE_AI_SEARCH_NAME)
fi

if [ -z "$aiSearchIndex" ]; then
    aiSearchIndex=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME)
fi

if [ -z "$resourceGroup" ]; then
    resourceGroup=$(azd env get-value AZURE_RESOURCE_GROUP)
fi

if [ -z "$azSubscriptionId" ]; then
    azSubscriptionId=$(azd env get-value AZURE_SUBSCRIPTION_ID)
fi

# Check if all required arguments are provided
if [ -z "$storageAccount" ] || [ -z "$blobContainer" ] || [ -z "$aiSearch" ]; then
    echo "Usage: $0 <StorageAccountName> <StorageContainerName> <AISearchName> [AISearchIndexName] [ResourceGroupName]"
    exit 1
fi

# Authenticate with Azure
if az account show &> /dev/null; then
    echo "Already authenticated with Azure."
else
    echo "Not authenticated with Azure. Attempting to authenticate..."
    echo "Authenticating with Azure CLI..."
    az login
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

stIsPublicAccessDisabled=false
srchIsPublicAccessDisabled=false
#Enable Public Access for resources
if [ -n "$resourceGroup" ]; then
    stPublicAccess=$(az storage account show --name "$storageAccount" --resource-group "$resourceGroup" --query "publicNetworkAccess" -o tsv)
    srchPublicAccess=$(az search service show --name "$aiSearch" --resource-group "$resourceGroup" --query "publicNetworkAccess" -o tsv)
    if [ "$stPublicAccess" == "Disabled" ]; then
        stIsPublicAccessDisabled=true
        echo "Enabling public access for storage account: $storageAccount"
        az storage account update --name "$storageAccount" --public-network-access enabled --default-action Allow --output none
        if [ $? -ne 0 ]; then
            echo "Error: Failed to enable public access for storage account."
            exit 1
        fi
        echo "Public access enabled for storage account: $storageAccount"
    else
        echo "Public access is already enabled for storage account: $storageAccount"
    fi

    if [ "$srchPublicAccess" == "Disabled" ]; then
        srchIsPublicAccessDisabled=true
        echo "Enabling public access for search service: $aiSearch"
        az search service update --name "$aiSearch" --resource-group "$resourceGroup" --public-network-access enabled --output none
        if [ $? -ne 0 ]; then
            echo "Error: Failed to enable public access for search service."
            exit 1
        fi
        echo "Public access enabled for search service: $aiSearch"
    else
        echo "Public access is already enabled for search service: $aiSearch"
    fi

fi


#Upload sample files to blob storage
echo "Uploading sample files to blob storage..."
az storage blob upload-batch --account-name "$storageAccount" --destination "$blobContainer" --source "data/datasets" --auth-mode login --pattern '*' --overwrite --output none
if [ $? -ne 0 ]; then
    echo "Error: Failed to upload files to blob storage."
    exit 1
fi
echo "Files uploaded successfully to blob storage."

# Determine the correct Python command
if command -v python && python --version &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 && python3 --version &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Python is not installed on this system. Or it is not added in the PATH."
    exit 1
fi

# create virtual environment
if [ -d "infra/scripts/scriptenv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    echo "Creating virtual environment"
    $PYTHON_CMD -m venv infra/scripts/scriptenv
fi

# Activate the virtual environment
if [ -f "infra/scripts/scriptenv/bin/activate" ]; then
    echo "Activating virtual environment (Linux/macOS)"
    source "infra/scripts/scriptenv/bin/activate"
elif [ -f "infra/scripts/scriptenv/Scripts/activate" ]; then
    echo "Activating virtual environment (Windows)"
    source "infra/scripts/scriptenv/Scripts/activate"
else
    echo "Error activating virtual environment. Requirements may be installed globally."
fi

# Install the requirements
echo "Installing requirements"
pip install --quiet -r infra/scripts/requirements.txt
echo "Requirements installed"

echo "Running the python script to index data"
$PYTHON_CMD infra/scripts/index_datasets.py "$storageAccount" "$blobContainer" "$aiSearch" "$aiSearchIndex"
if [ $? -ne 0 ]; then
    echo "Error: Indexing python script execution failed."
    exit 1
fi

#disable public access for resources
if [ "$stIsPublicAccessDisabled" = true ]; then
    echo "Disabling public access for storage account: $storageAccount"
    az storage account update --name "$storageAccount" --public-network-access disabled --default-action Deny --output none
    if [ $? -ne 0 ]; then
        echo "Error: Failed to disable public access for storage account."
        exit 1
    fi
    echo "Public access disabled for storage account: $storageAccount"
fi

if [ "$srchIsPublicAccessDisabled" = true ]; then
    echo "Disabling public access for search service: $aiSearch"
    az search service update --name "$aiSearch" --resource-group "$resourceGroup" --public-network-access disabled --output none
    if [ $? -ne 0 ]; then
        echo "Error: Failed to disable public access for search service."
        exit 1
    fi
    echo "Public access disabled for search service: $aiSearch"
fi

echo "Script executed successfully. Sample Data Processed Successfully."
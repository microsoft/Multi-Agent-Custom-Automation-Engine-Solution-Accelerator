#!/bin/bash

# Parse command line arguments
ResourceGroup=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group)
            ResourceGroup="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Variables
directoryPath=""
backendUrl=""
storageAccount=""
blobContainerForRetailCustomer=""
blobContainerForRetailOrder=""
blobContainerForRFPSummary=""
blobContainerForRFPRisk=""
blobContainerForRFPCompliance=""

aiSearch=""
aiSearchIndexForRetailCustomer=""
aiSearchIndexForRetailOrder=""
aiSearchIndexForRFPSummary=""
aiSearchIndexForRFPRisk=""
aiSearchIndexForRFPCompliance=""

azSubscriptionId=""

function test_azd_installed() {
    if command -v azd &> /dev/null; then
        return 0
    else
        return 1
    fi
}

function get_values_from_azd_env() {
    if ! test_azd_installed; then
        echo "Error: Azure Developer CLI is not installed."
        return 1
    fi

    echo "Getting values from azd environment..."
    
    directoryPath="data/agent_teams"
    backendUrl=$(azd env get-value BACKEND_URL)
    storageAccount=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
    blobContainerForRetailCustomer=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER)
    blobContainerForRetailOrder=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER)
    blobContainerForRFPSummary=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY)
    blobContainerForRFPRisk=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RFP_RISK)
    blobContainerForRFPCompliance=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE)

    aiSearch=$(azd env get-value AZURE_AI_SEARCH_NAME)
    aiSearchIndexForRetailCustomer=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER)
    aiSearchIndexForRetailOrder=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER)
    aiSearchIndexForRFPSummary=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY)
    aiSearchIndexForRFPRisk=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK)
    aiSearchIndexForRFPCompliance=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE)

    ResourceGroup=$(azd env get-value AZURE_RESOURCE_GROUP)
    
    # Validate that we got all required values
    if [[ -z "$backendUrl" || -z "$storageAccount" || -z "$blobContainerForRetailCustomer" || -z "$aiSearch" || -z "$aiSearchIndexForRetailOrder" || -z "$ResourceGroup" ]]; then
        echo "Error: Could not retrieve all required values from azd environment."
        return 1
    fi
    
    echo "Successfully retrieved values from azd environment."
    return 0
}

# Helper function to extract value with fallback
extract_value() {
    local primary_key="$1"
    local fallback_key="$2"
    local result
    
    result=$(echo "$deploymentOutputs" | grep -A 3 "\"$primary_key\"" | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    if [ -z "$result" ]; then
        result=$(echo "$deploymentOutputs" | grep -A 3 "\"$fallback_key\"" | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/')
    fi
    echo "$result"
}

function get_values_from_az_deployment() {
    echo "Getting values from Azure deployment outputs..."
    
    directoryPath="data/agent_teams"
    
    echo "Fetching deployment name..."
    deploymentName=$(az group show --name "$ResourceGroup" --query "tags.DeploymentName" -o tsv)
    if [[ -z "$deploymentName" ]]; then
        echo "Error: Could not find deployment name in resource group tags."
        return 1
    fi
    
    echo "Fetching deployment outputs for deployment: $deploymentName"
    deploymentOutputs=$(az deployment group show --resource-group "$ResourceGroup" --name "$deploymentName" --query "properties.outputs" -o json)
    if [[ -z "$deploymentOutputs" ]]; then
        echo "Error: Could not fetch deployment outputs."
        return 1
    fi
    
    # Extract all values using the helper function
    storageAccount=$(extract_value "azurE_STORAGE_ACCOUNT_NAME" "azureStorageAccountName")
    blobContainerForRetailCustomer=$(extract_value "azurE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER" "azureStorageContainerNameRetailCustomer")
    blobContainerForRetailOrder=$(extract_value "azurE_STORAGE_CONTAINER_NAME_RETAIL_ORDER" "azureStorageContainerNameRetailOrder")
    blobContainerForRFPSummary=$(extract_value "azurE_STORAGE_CONTAINER_NAME_RFP_SUMMARY" "azureStorageContainerNameRfpSummary")
    blobContainerForRFPRisk=$(extract_value "azurE_STORAGE_CONTAINER_NAME_RFP_RISK" "azureStorageContainerNameRfpRisk")
    blobContainerForRFPCompliance=$(extract_value "azurE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE" "azureStorageContainerNameRfpCompliance")

    aiSearchIndexForRetailCustomer=$(extract_value "azurE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER" "azureAiSearchIndexNameRetailCustomer")
    aiSearchIndexForRetailOrder=$(extract_value "azurE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER" "azureAiSearchIndexNameRetailOrder")
    aiSearchIndexForRFPSummary=$(extract_value "azurE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY" "azureAiSearchIndexNameRfpSummary")
    aiSearchIndexForRFPRisk=$(extract_value "azurE_AI_SEARCH_INDEX_NAME_RFP_RISK" "azureAiSearchIndexNameRfpRisk")
    aiSearchIndexForRFPCompliance=$(extract_value "azurE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE" "azureAiSearchIndexNameRfpCompliance")

    aiSearch=$(extract_value "azurE_AI_SEARCH_NAME" "azureAiSearchName")
    backendUrl=$(extract_value "backenD_URL" "backendUrl")
    
    # Validate that we extracted all required values
    if [[ -z "$storageAccount" || -z "$aiSearch" || -z "$backendUrl" ]]; then
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

# Get subscription ID from azd if available
if test_azd_installed; then
    azSubscriptionId=$(azd env get-value AZURE_SUBSCRIPTION_ID 2>/dev/null || echo "")
    if [[ -z "$azSubscriptionId" ]]; then
        azSubscriptionId="$AZURE_SUBSCRIPTION_ID"
    fi
fi

# Check if user has selected the correct subscription
currentSubscriptionId=$(az account show --query id -o tsv)
currentSubscriptionName=$(az account show --query name -o tsv)

if [[ "$currentSubscriptionId" != "$azSubscriptionId" && -n "$azSubscriptionId" ]]; then
    echo "Current selected subscription is $currentSubscriptionName ( $currentSubscriptionId )."
    read -p "Do you want to continue with this subscription?(y/n): " confirmation
    if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
        echo "Fetching available subscriptions..."
        availableSubscriptions=$(az account list --query "[?state=='Enabled'].[name,id]" --output tsv)
        
        # Convert to array
        IFS=$'\n' read -d '' -r -a subscriptions <<< "$availableSubscriptions"
        
        while true; do
            echo ""
            echo "Available Subscriptions:"
            echo "========================"
            local index=1
            for ((i=0; i<${#subscriptions[@]}; i++)); do
                IFS=$'\t' read -r name id <<< "${subscriptions[i]}"
                echo "$index. $name ( $id )"
                ((index++))
            done
            echo "========================"
            echo ""
            
            read -p "Enter the number of the subscription (1-$((${#subscriptions[@]}))) to use: " subscriptionIndex
            
            if [[ "$subscriptionIndex" =~ ^[0-9]+$ ]] && [[ "$subscriptionIndex" -ge 1 ]] && [[ "$subscriptionIndex" -le "${#subscriptions[@]}" ]]; then
                selectedIndex=$((subscriptionIndex - 1))
                IFS=$'\t' read -r selectedSubscriptionName selectedSubscriptionId <<< "${subscriptions[selectedIndex]}"
                
                if az account set --subscription "$selectedSubscriptionId"; then
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

# Get configuration values based on strategy
if [[ -z "$ResourceGroup" ]]; then
    # No resource group provided - use azd env
    if ! get_values_from_azd_env; then
        echo "Failed to get values from azd environment."
        echo "If you want to use deployment outputs instead, please provide the resource group name as an argument."
        echo "Usage: ./selecting-team-config-and-data.sh --resource-group <ResourceGroupName>"
        exit 1
    fi
else
    # Resource group provided - use deployment outputs
    echo "Resource group provided: $ResourceGroup"
    
    if ! get_values_from_az_deployment; then
        echo "Failed to get values from deployment outputs."
        exit 1
    fi
fi

# Interactive Use Case Selection
echo ""
echo "==============================================="
echo "Available Use Cases:"
echo "==============================================="
echo "1. RFP Evaluation"
echo "2. Retail Customer Satisfaction"
echo "3. HR Employee Onboarding"
echo "4. Marketing Press Release"
echo "5. All"
echo "==============================================="
echo ""

# Prompt user for use case selection
useCaseValid=false
while [[ "$useCaseValid" != true ]]; do
    read -p "Please enter the number of the use case you would like to install: " useCaseSelection
    
    # Handle both numeric and text input for 'all'
    if [[ "$useCaseSelection" == "all" || "$useCaseSelection" == "5" ]]; then
        selectedUseCase="All"
        useCaseValid=true
        echo "Selected: All use cases will be installed."
    elif [[ "$useCaseSelection" == "1" ]]; then
        selectedUseCase="RFP Evaluation"
        useCaseValid=true
        echo "Selected: RFP Evaluation"
        echo "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    elif [[ "$useCaseSelection" == "2" ]]; then
        selectedUseCase="Retail Customer Satisfaction"
        useCaseValid=true
        echo "Selected: Retail Customer Satisfaction"
        echo "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    elif [[ "$useCaseSelection" == "3" ]]; then
        selectedUseCase="HR Employee Onboarding"
        useCaseValid=true
        echo "Selected: HR Employee Onboarding"
        echo "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    elif [[ "$useCaseSelection" == "4" ]]; then
        selectedUseCase="Marketing Press Release"
        useCaseValid=true
        echo "Selected: Marketing Press Release"
        echo "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    else
        useCaseValid=false
        echo -e "\033[31mInvalid selection. Please enter a number from 1-5.\033[0m"
    fi
done

echo ""
echo "==============================================="
echo "Values to be used:"
echo "==============================================="
echo "Selected Use Case: $selectedUseCase"
echo "Resource Group: $ResourceGroup"
echo "Backend URL: $backendUrl"
echo "Storage Account: $storageAccount"
echo "AI Search: $aiSearch"
echo "Directory Path: $directoryPath"
echo "Subscription ID: $azSubscriptionId"
echo "==============================================="
echo ""

userPrincipalId=$(az ad signed-in-user show --query id -o tsv)

# Determine the correct Python command
pythonCmd=""

if command -v python &> /dev/null; then
    pythonVersion=$(python --version 2>&1)
    if [[ "$pythonVersion" =~ Python\ [0-9] ]]; then
        pythonCmd="python"
    fi
fi

if [[ -z "$pythonCmd" ]]; then
    if command -v python3 &> /dev/null; then
        pythonVersion=$(python3 --version 2>&1)
        if [[ "$pythonVersion" =~ Python\ [0-9] ]]; then
            pythonCmd="python3"
        fi
    fi
fi

if [[ -z "$pythonCmd" ]]; then
    echo "Python is not installed on this system or it is not added in the PATH."
    exit 1
fi

# Create virtual environment
venvPath="infra/scripts/scriptenv"
if [[ -d "$venvPath" ]]; then
    echo "Virtual environment already exists. Skipping creation."
else
    echo "Creating virtual environment"
    $pythonCmd -m venv "$venvPath"
fi

# Activate the virtual environment
if [[ -f "$venvPath/bin/activate" ]]; then
    echo "Activating virtual environment"
    source "$venvPath/bin/activate"
elif [[ -f "$venvPath/Scripts/activate" ]]; then
    echo "Activating virtual environment"
    source "$venvPath/Scripts/activate"
else
    echo "Error activating virtual environment. Requirements may be installed globally."
fi

# Install the requirements
echo "Installing requirements"
pip install --quiet -r infra/scripts/requirements.txt
echo "Requirements installed"

isTeamConfigFailed=false
isSampleDataFailed=false
failedTeamConfigs=0

# Use Case 3 - HR Employee Onboarding
if [[ "$useCaseSelection" == "3" || "$useCaseSelection" == "all" || "$useCaseSelection" == "5" ]]; then
    echo "Uploading Team Configuration for HR Employee Onboarding..."
    directoryPath="data/agent_teams"
    teamId="00000000-0000-0000-0000-000000000001"
    
    if $pythonCmd infra/scripts/upload_team_config.py "$backendUrl" "$directoryPath" "$userPrincipalId" "$teamId"; then
        echo "Successfully uploaded team configuration for HR Employee Onboarding."
    else
        echo "Error: Team configuration for HR Employee Onboarding upload failed."
        isTeamConfigFailed=true
        ((failedTeamConfigs++))
    fi
fi

# Use Case 4 - Marketing Press Release
if [[ "$useCaseSelection" == "4" || "$useCaseSelection" == "all" || "$useCaseSelection" == "5" ]]; then
    echo "Uploading Team Configuration for Marketing Press Release..."
    directoryPath="data/agent_teams"
    teamId="00000000-0000-0000-0000-000000000002"
    
    if $pythonCmd infra/scripts/upload_team_config.py "$backendUrl" "$directoryPath" "$userPrincipalId" "$teamId"; then
        echo "Successfully uploaded team configuration for Marketing Press Release."
    else
        echo "Error: Team configuration for Marketing Press Release upload failed."
        isTeamConfigFailed=true
        ((failedTeamConfigs++))
    fi
fi

stIsPublicAccessDisabled=false
srchIsPublicAccessDisabled=false

# Enable public access for resources
if [[ "$useCaseSelection" == "1" || "$useCaseSelection" == "2" || "$useCaseSelection" == "5" || "$useCaseSelection" == "all" ]]; then
    if [[ -n "$ResourceGroup" ]]; then
        stPublicAccess=$(az storage account show --name "$storageAccount" --resource-group "$ResourceGroup" --query "publicNetworkAccess" -o tsv)
        if [[ "$stPublicAccess" == "Disabled" ]]; then
            stIsPublicAccessDisabled=true
            echo "Enabling public access for storage account: $storageAccount"
            az storage account update --name "$storageAccount" --public-network-access enabled --default-action Allow --output none
            if [[ $? -ne 0 ]]; then
                echo "Error: Failed to enable public access for storage account."
                exit 1
            fi
        else
            echo "Public access is already enabled for storage account: $storageAccount"
        fi

        srchPublicAccess=$(az search service show --name "$aiSearch" --resource-group "$ResourceGroup" --query "publicNetworkAccess" -o tsv)
        if [[ "$srchPublicAccess" == "Disabled" ]]; then
            srchIsPublicAccessDisabled=true
            echo "Enabling public access for search service: $aiSearch"
            az search service update --name "$aiSearch" --resource-group "$ResourceGroup" --public-network-access enabled --output none
            if [[ $? -ne 0 ]]; then
                echo "Error: Failed to enable public access for search service."
                exit 1
            fi
        else
            echo "Public access is already enabled for search service: $aiSearch"
        fi
    fi
fi

# Use Case 1 - RFP Evaluation
if [[ "$useCaseSelection" == "1" || "$useCaseSelection" == "all" || "$useCaseSelection" == "5" ]]; then
    echo "Uploading Team Configuration for RFP Evaluation..."
    directoryPath="data/agent_teams"
    teamId="00000000-0000-0000-0000-000000000004"
    
    if $pythonCmd infra/scripts/upload_team_config.py "$backendUrl" "$directoryPath" "$userPrincipalId" "$teamId"; then
        echo "Uploaded Team Configuration for RFP Evaluation..."
    else
        echo "Error: Team configuration for RFP Evaluation upload failed."
        ((failedTeamConfigs++))
        isTeamConfigFailed=true
    fi

    directoryPath="data/datasets/rfp/summary"
    # Upload sample files to blob storage
    echo "Uploading sample files to blob storage for RFP Evaluation..."
    if ! az storage blob upload-batch --account-name "$storageAccount" --destination "$blobContainerForRFPSummary" --source "$directoryPath" --auth-mode login --pattern "*" --overwrite --output none; then
        echo "Error: Failed to upload files to blob storage."
        isSampleDataFailed=true
        exit 1
    fi

    directoryPath="data/datasets/rfp/risk"
    if ! az storage blob upload-batch --account-name "$storageAccount" --destination "$blobContainerForRFPRisk" --source "$directoryPath" --auth-mode login --pattern "*" --overwrite --output none; then
        echo "Error: Failed to upload files to blob storage."
        isSampleDataFailed=true
        exit 1
    fi

    directoryPath="data/datasets/rfp/compliance"
    if ! az storage blob upload-batch --account-name "$storageAccount" --destination "$blobContainerForRFPCompliance" --source "$directoryPath" --auth-mode login --pattern "*" --overwrite --output none; then
        echo "Error: Failed to upload files to blob storage."
        isSampleDataFailed=true
        exit 1
    fi
    echo "Files uploaded successfully to blob storage."

    # Run the Python script to index data
    echo "Running the python script to index data for RFP Evaluation"
    if $pythonCmd infra/scripts/index_datasets.py "$storageAccount" "$blobContainerForRFPSummary" "$aiSearch" "$aiSearchIndexForRFPSummary"; then
        echo "Python script to index data for RFP Summary successfully executed."
    else
        echo "Error: Indexing python script execution failed for RFP Summary."
        isSampleDataFailed=true
    fi

    if $pythonCmd infra/scripts/index_datasets.py "$storageAccount" "$blobContainerForRFPRisk" "$aiSearch" "$aiSearchIndexForRFPRisk"; then
        echo "Python script to index data for RFP Risk successfully executed."
    else
        echo "Error: Indexing python script execution failed for RFP Risk."
        isSampleDataFailed=true
    fi

    if $pythonCmd infra/scripts/index_datasets.py "$storageAccount" "$blobContainerForRFPCompliance" "$aiSearch" "$aiSearchIndexForRFPCompliance"; then
        echo "Python script to index data for RFP Compliance successfully executed."
    else
        echo "Error: Indexing python script execution failed for RFP Compliance."
        isSampleDataFailed=true
    fi
    echo "Python script to index data for RFP Evaluation successfully executed."
fi


# Use Case 2 - Retail Customer Satisfaction
if [[ "$useCaseSelection" == "2" || "$useCaseSelection" == "all" || "$useCaseSelection" == "5" ]]; then
    echo "Uploading Team Configuration for Retail Customer Satisfaction..."
    directoryPath="data/agent_teams"
    teamId="00000000-0000-0000-0000-000000000003"
    
    if $pythonCmd infra/scripts/upload_team_config.py "$backendUrl" "$directoryPath" "$userPrincipalId" "$teamId"; then
        echo "Uploaded Team Configuration for Retail Customer Satisfaction..."
    else
        echo "Error: Team configuration for Retail Customer Satisfaction upload failed."
        ((failedTeamConfigs++))
        isTeamConfigFailed=true
    fi

    directoryPath="data/datasets/retail/customer"
    # Upload sample files to blob storage
    echo "Uploading sample files to blob storage for Retail Customer Satisfaction..."
    if ! az storage blob upload-batch --account-name "$storageAccount" --destination "retail-dataset-customer" --source "$directoryPath" --auth-mode login --pattern "*" --overwrite --output none; then
        echo "Error: Failed to upload files to blob storage."
        isSampleDataFailed=true
        exit 1
    fi
    
    directoryPath="data/datasets/retail/order"
    if ! az storage blob upload-batch --account-name "$storageAccount" --destination "retail-dataset-order" --source "data/datasets/retail/order" --auth-mode login --pattern "*" --overwrite --output none; then
        echo "Error: Failed to upload files to blob storage."
        isSampleDataFailed=true
        exit 1
    fi
    echo "Files uploaded successfully to blob storage."

    # Run the Python script to index data
    echo "Running the python script to index data for Retail Customer Satisfaction"
    if ! $pythonCmd infra/scripts/index_datasets.py "$storageAccount" "retail-dataset-customer" "$aiSearch" "macae-retail-customer-index"; then
        echo "Error: Indexing python script execution failed."
        isSampleDataFailed=true
        exit 1
    fi
    
    if ! $pythonCmd infra/scripts/index_datasets.py "$storageAccount" "retail-dataset-order" "$aiSearch" "macae-retail-order-index"; then
        echo "Error: Indexing python script execution failed."
        isSampleDataFailed=true
        exit 1
    fi
    echo "Python script to index data for Retail Customer Satisfaction successfully executed."
fi

# Disable public access for resources
if [[ "$stIsPublicAccessDisabled" == true ]]; then
    echo "Disabling public access for storage account: $storageAccount"
    az storage account update --name "$storageAccount" --public-network-access disabled --default-action Deny --output none
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to disable public access for storage account."
        exit 1
    fi
fi

if [[ "$srchIsPublicAccessDisabled" == true ]]; then
    echo "Disabling public access for search service: $aiSearch"
    az search service update --name "$aiSearch" --resource-group "$ResourceGroup" --public-network-access disabled --output none
    if [[ $? -ne 0 ]]; then
        echo "Error: Failed to disable public access for search service."
        exit 1
    fi
fi

echo "Script executed successfully. Sample Data Processed Successfully."

if [[ "$isTeamConfigFailed" == true || "$isSampleDataFailed" == true ]]; then
    echo ""
    echo "One or more tasks failed. Please check the error messages above."
    exit 1
else
    if [[ "$useCaseSelection" == "1" || "$useCaseSelection" == "2" || "$useCaseSelection" == "5" || "$useCaseSelection" == "all"  ]]; then
        echo ""
        echo "Team configuration upload and sample data processing completed successfully."
    else
        echo ""
        echo "Team configuration upload completed successfully."
    fi
fi
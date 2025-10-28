#!/bin/bash
set -e

# ============================================================
#  process_rfp_data.sh
#  Uploads RFP PDFs to Azure Blob Storage and triggers Azure Search indexing
# ============================================================

# --- Load environment variables from azd ---
storageAccount=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
blobContainer=$(azd env get-value AZURE_STORAGE_CONTAINER_NAME)
aiSearchName=$(azd env get-value AZURE_AI_SEARCH_NAME)
aiSearchIndex=$(azd env get-value AZURE_AI_SEARCH_INDEX_NAME)
resourceGroupName=$(azd env get-value AZURE_RESOURCE_GROUP)
subscriptionId=$(azd env get-value AZURE_SUBSCRIPTION_ID)
managedIdentityClientId=$(azd env get-value AZURE_CLIENT_ID)
location=$(azd env get-value AZURE_LOCATION)

# --- Validate required values ---
if [ -z "$storageAccount" ] || [ -z "$blobContainer" ] || [ -z "$aiSearchName" ] || [ -z "$aiSearchIndex" ] || [ -z "$resourceGroupName" ]; then
    echo "❌ Missing required environment variables from azd."
    echo "Make sure azd env values are set correctly."
    exit 1
fi

echo "============================================================"
echo " RFP PDF Indexing Script"
echo "------------------------------------------------------------"
echo " Storage Account      : $storageAccount"
echo " Blob Container       : $blobContainer"
echo " AI Search Service    : $aiSearchName"
echo " AI Search Index Name : $aiSearchIndex"
echo " Resource Group       : $resourceGroupName"
echo " Subscription ID      : $subscriptionId"
echo "============================================================"

# --- Authenticate with Azure ---
if az account show &> /dev/null; then
    echo "✅ Already authenticated with Azure."
else
    if [ -n "$managedIdentityClientId" ]; then
        echo "🔐 Authenticating with Managed Identity..."
        az login --identity --client-id ${managedIdentityClientId}
    else
        echo "🔐 Authenticating with Azure CLI..."
        az login
    fi
fi

# --- Ensure correct subscription is set ---
currentSub=$(az account show --query id -o tsv)
if [ "$currentSub" != "$subscriptionId" ]; then
    echo "⚙️ Switching to correct subscription..."
    az account set --subscription "$subscriptionId"
fi

# --- Enable public access if disabled ---
echo "🔍 Checking network access for Azure resources..."
stPublicAccess=$(az storage account show --name "$storageAccount" --resource-group "$resourceGroupName" --query "publicNetworkAccess" -o tsv)
srchPublicAccess=$(az search service show --name "$aiSearchName" --resource-group "$resourceGroupName" --query "publicNetworkAccess" -o tsv)

stIsPublicAccessDisabled=false
srchIsPublicAccessDisabled=false

if [ "$stPublicAccess" == "Disabled" ]; then
    stIsPublicAccessDisabled=true
    echo "🌐 Enabling public access for storage account..."
    az storage account update --name "$storageAccount" --public-network-access enabled --default-action Allow --output none
fi

if [ "$srchPublicAccess" == "Disabled" ]; then
    srchIsPublicAccessDisabled=true
    echo "🌐 Enabling public access for search service..."
    az search service update --name "$aiSearchName" --resource-group "$resourceGroupName" --public-network-access enabled --output none
fi

# --- Upload dataset to Azure Blob Storage ---
DATASET_PATH="data/dataset/RFP_dataset"

if [ ! -d "$DATASET_PATH" ]; then
    echo "❌ Dataset folder not found at: $DATASET_PATH"
    exit 1
fi

echo "📤 Uploading RFP PDFs to container '$blobContainer'..."
az storage blob upload-batch \
    --account-name "$storageAccount" \
    --destination "$blobContainer" \
    --source "$DATASET_PATH" \
    --auth-mode login \
    --overwrite \
    --output none

echo "✅ PDF dataset uploaded successfully."

# --- Run cloud indexing using Python (direct Azure indexer setup) ---
cd infra/scripts

if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Python not found in PATH."
    exit 1
fi

# Create and activate virtual environment if not exists
if [ ! -d "scriptenv" ]; then
    echo "🐍 Creating virtual environment..."
    $PYTHON_CMD -m venv scriptenv
fi

if [ -f "scriptenv/bin/activate" ]; then
    source "scriptenv/bin/activate"
elif [ -f "scriptenv/Scripts/activate" ]; then
    source "scriptenv/Scripts/activate"
fi

echo "📦 Installing requirements..."
pip install --quiet -r requirements.txt
echo "✅ Requirements installed."

echo "🚀 Running Azure Search indexer setup..."
$PYTHON_CMD index_rfp_data.py "$storageAccount" "$blobContainer" "$aiSearchName" "$aiSearchIndex" "$resourceGroupName"

if [ $? -ne 0 ]; then
    echo "❌ Indexing failed."
    exit 1
fi

# --- Restore public access settings ---
if [ "$stIsPublicAccessDisabled" = true ]; then
    echo "🔒 Disabling public access for storage account..."
    az storage account update --name "$storageAccount" --public-network-access disabled --default-action Deny --output none
fi

if [ "$srchIsPublicAccessDisabled" = true ]; then
    echo "🔒 Disabling public access for search service..."
    az search service update --name "$aiSearchName" --resource-group "$resourceGroupName" --public-network-access disabled --output none
fi

echo "Successfully uploaded and indexed RFP PDFs in Azure!"

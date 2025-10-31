#Requires -Version 7.0

param(
    [string]$StorageAccount,
    [string]$BlobContainer,
    [string]$AiSearch,
    [string]$AiSearchIndex,
    [string]$ResourceGroup
)

# Get parameters from azd env, if not provided
if (-not $StorageAccount) { $StorageAccount = $(azd env get-value AZURE_STORAGE_ACCOUNT_NAME) }
if (-not $BlobContainer) { $BlobContainer = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME) }
if (-not $AiSearch) { $AiSearch = $(azd env get-value AZURE_AI_SEARCH_NAME) }
if (-not $AiSearchIndex) { $AiSearchIndex = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME) }
if (-not $ResourceGroup) { $ResourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP) }

$AzSubscriptionId = $(azd env get-value AZURE_SUBSCRIPTION_ID)

# Check if all required arguments are provided
if (-not $StorageAccount -or -not $BlobContainer -or -not $AiSearch) {
    Write-Host "Usage: .\infra\scripts\Process-Sample-Data.ps1 -StorageAccount <StorageAccountName> -BlobContainer <StorageContainerName> -AiSearch <AISearchName> [-AiSearchIndex <AISearchIndexName>] [-ResourceGroup <ResourceGroupName>]"
    exit 1
}

# Authenticate with Azure
try {
    $currentAzContext = az account show | ConvertFrom-Json -ErrorAction Stop
    Write-Host "Already authenticated with Azure."
} 
catch {
    Write-Host "Not authenticated with Azure. Attempting to authenticate..."
    Write-Host "Authenticating with Azure CLI..."
    az login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Authentication failed."
        exit 1
    }
    $currentAzContext = az account show | ConvertFrom-Json
}

# Check if user has selected the correct subscription
$currentSubscriptionId = $currentAzContext.id
$currentSubscriptionName = $currentAzContext.name

if ($currentSubscriptionId -ne $AzSubscriptionId) {
    Write-Host "Current selected subscription is $currentSubscriptionName ( $currentSubscriptionId )."
    $confirmation = Read-Host "Do you want to continue with this subscription? (y/n)"
    
    if ($confirmation.ToLower() -ne "y") {
        Write-Host "Fetching available subscriptions..."
        $availableSubscriptions = (az account list --query "[?state=='Enabled']" | ConvertFrom-Json -AsHashtable)
        $subscriptionArray = $availableSubscriptions | ForEach-Object {
            [PSCustomObject]@{ Name = $_.name; Id = $_.id }
        }
        
        do {
            Write-Host ""
            Write-Host "Available Subscriptions:"
            Write-Host "========================"
            for ($i = 0; $i -lt $subscriptionArray.Count; $i++) {
                Write-Host "$($i+1). $($subscriptionArray[$i].Name) ( $($subscriptionArray[$i].Id) )"
            }
            Write-Host "========================"
            Write-Host ""
            
            [int]$subscriptionIndex = Read-Host "Enter the number of the subscription (1-$($subscriptionArray.Count)) to use"
            
            if ($subscriptionIndex -ge 1 -and $subscriptionIndex -le $subscriptionArray.Count) {
                $selectedSubscription = $subscriptionArray[$subscriptionIndex-1]
                $result = az account set --subscription $selectedSubscription.Id
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Switched to subscription: $($selectedSubscription.Name) ( $($selectedSubscription.Id) )"
                    break
                }
                else {
                    Write-Host "Failed to switch to subscription: $($selectedSubscription.Name) ( $($selectedSubscription.Id) )."
                }
            }
            else {
                Write-Host "Invalid selection. Please try again."
            }
        } while ($true)
    }
    else {
        Write-Host "Proceeding with the current subscription: $currentSubscriptionName ( $currentSubscriptionId )"
        az account set --subscription $currentSubscriptionId
    }
}
else {
    Write-Host "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    az account set --subscription $currentSubscriptionId
}

$stIsPublicAccessDisabled = $false
$srchIsPublicAccessDisabled = $false

# Enable public access for resources
if ($ResourceGroup) {
    $stPublicAccess = $(az storage account show --name $StorageAccount --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv)
    if ($stPublicAccess -eq "Disabled") {
        $stIsPublicAccessDisabled = $true
        Write-Host "Enabling public access for storage account: $StorageAccount"
        az storage account update --name $StorageAccount --public-network-access enabled --default-action Allow --output none
        if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to enable public access for storage account."; exit 1 }
    } else {
        Write-Host "Public access is already enabled for storage account: $StorageAccount"
    }

    $srchPublicAccess = $(az search service show --name $AiSearch --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv)
    if ($srchPublicAccess -eq "Disabled") {
        $srchIsPublicAccessDisabled = $true
        Write-Host "Enabling public access for search service: $AiSearch"
        az search service update --name $AiSearch --resource-group $ResourceGroup --public-network-access enabled --output none
        if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to enable public access for search service."; exit 1 }
    } else {
        Write-Host "Public access is already enabled for search service: $AiSearch"
    }
}

# Upload CSV files
Write-Host "Uploading CSV files to blob storage..."
az storage blob upload-batch --account-name $StorageAccount --destination $BlobContainer --source "data/datasets" --auth-mode login --pattern "*.csv" --overwrite --output none
az storage blob upload-batch --account-name $StorageAccount --destination $BlobContainer --source "data/datasets" --auth-mode login --pattern "*.json" --overwrite --output none
if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to upload CSV files."; exit 1 }
Write-Host "CSV files uploaded successfully."

# Upload PDF files
Write-Host "Uploading PDF files from RFP_dataset to blob storage..."
az storage blob upload-batch --account-name $StorageAccount --destination $BlobContainer --source "data/datasets/RFP_dataset" --auth-mode login --pattern "*.pdf" --overwrite --output none
if ($LASTEXITCODE -ne 0) { Write-Host "Error: Failed to upload PDF files."; exit 1 }
Write-Host "PDF files uploaded successfully."

# Detect file types
Write-Host "Detecting file types in blob container..."
$fileList = az storage blob list --account-name $StorageAccount --container-name $BlobContainer --query "[].name" -o tsv --auth-mode login
$hasPdf = $false
$hasCsv = $false
foreach ($file in $fileList) {
    if ($file -match "\.pdf$") { $hasPdf = $true }
    if ($file -match "\.csv$") { $hasCsv = $true }
}

# Determine the correct Python command
$pythonCmd = $null
try {
    $pythonVersion = (python --version) 2>&1
    if ($pythonVersion -match "Python \d") { $pythonCmd = "python" }
} catch {}
if (-not $pythonCmd) {
    try {
        $pythonVersion = (python3 --version) 2>&1
        if ($pythonVersion -match "Python \d") { $pythonCmd = "python3" }
    } catch {
        Write-Host "Python is not installed or not in PATH."
        exit 1
    }
}
if (-not $pythonCmd) { Write-Host "Python is not installed or not in PATH."; exit 1 }

# Virtual environment
$venvPath = "infra/scripts/scriptenv"
if (Test-Path $venvPath) {
    Write-Host "Virtual environment already exists. Skipping creation."
} else {
    Write-Host "Creating virtual environment"
    & $pythonCmd -m venv $venvPath
}

# Activate venv
if (Test-Path (Join-Path $venvPath "bin/Activate.ps1")) {
    . (Join-Path $venvPath "bin/Activate.ps1")
} elseif (Test-Path (Join-Path $venvPath "Scripts/Activate.ps1")) {
    . (Join-Path $venvPath "Scripts/Activate.ps1")
} else {
    Write-Host "Error activating virtual environment. Requirements may be installed globally."
}

# Install requirements
Write-Host "Installing requirements"
pip install --quiet -r infra/scripts/requirements.txt
Write-Host "Requirements installed"

# Run indexing scripts
if ($hasCsv) {
    Write-Host "Running the python script to index CSV data"
    & $pythonCmd "infra/scripts/index_datasets.py" $StorageAccount $BlobContainer $AiSearch $AiSearchIndex
    if ($LASTEXITCODE -ne 0) { Write-Host "Error: CSV indexing script failed."; exit 1 }
}
# if ($hasPdf) {
#     Write-Host "Running the python script to index PDF data"
#     & $pythonCmd "infra/scripts/index_rfp_data.py" $StorageAccount $BlobContainer $AiSearch $AiSearchIndex
#     if ($LASTEXITCODE -ne 0) { Write-Host "Error: PDF indexing script failed."; exit 1 }
# }
if (-not $hasCsv -and -not $hasPdf) {
    Write-Host "No CSV or PDF files found to index."
}

# Disable public access again
if ($stIsPublicAccessDisabled) {
    Write-Host "Disabling public access for storage account: $StorageAccount"
    az storage account update --name $StorageAccount --public-network-access disabled --default-action Deny --output none
}
if ($srchIsPublicAccessDisabled) {
    Write-Host "Disabling public access for search service: $AiSearch"
    az search service update --name $AiSearch --resource-group $ResourceGroup --public-network-access disabled --output none
}

Write-Host "Script executed successfully. Sample Data Processed Successfully."

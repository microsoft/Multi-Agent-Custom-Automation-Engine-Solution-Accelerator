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
if (-not $BlobContainer)   { $BlobContainer = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME) }
if (-not $AiSearch)        { $AiSearch = $(azd env get-value AZURE_AI_SEARCH_NAME) }
if (-not $AiSearchIndex)   { $AiSearchIndex = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME) }
if (-not $ResourceGroup)   { $ResourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP) }

$AzSubscriptionId = $(azd env get-value AZURE_SUBSCRIPTION_ID)

# Validate required parameters
if (-not $StorageAccount -or -not $BlobContainer -or -not $AiSearch) {
    Write-Host "Usage: .\infra\scripts\Process-RFP-Data.ps1 -StorageAccount <StorageAccount> -BlobContainer <Container> -AiSearch <SearchName> [-AiSearchIndex <IndexName>] [-ResourceGroup <ResourceGroup>]"
    exit 1
}

# Authenticate with Azure
try {
    $currentAzContext = az account show | ConvertFrom-Json -ErrorAction Stop
    Write-Host "Already authenticated with Azure."
} catch {
    Write-Host "Not authenticated. Logging in..."
    az login
    if ($LASTEXITCODE -ne 0) { Write-Host "Authentication failed."; exit 1 }
    $currentAzContext = az account show | ConvertFrom-Json
}

# Ensure correct subscription
$currentSubscriptionId = $currentAzContext.id
$currentSubscriptionName = $currentAzContext.name

if ($currentSubscriptionId -ne $AzSubscriptionId) {
    Write-Host "Current subscription: $currentSubscriptionName ($currentSubscriptionId)"
    $confirmation = Read-Host "Continue with this subscription? (y/n)"
    if ($confirmation.ToLower() -ne "y") {
        Write-Host "Fetching available subscriptions..."
        $availableSubs = az account list --query "[?state=='Enabled']" | ConvertFrom-Json
        $subArray = $availableSubs | ForEach-Object { [PSCustomObject]@{ Name=$_.name; Id=$_.id } }

        do {
            Write-Host "`nAvailable Subscriptions:`n======================"
            for ($i=0; $i -lt $subArray.Count; $i++) { Write-Host "$($i+1). $($subArray[$i].Name) ($($subArray[$i].Id))" }
            $subIndex = Read-Host "Enter subscription number (1-$($subArray.Count))"
            if ($subIndex -ge 1 -and $subIndex -le $subArray.Count) {
                $selectedSub = $subArray[$subIndex-1]
                az account set --subscription $selectedSub.Id
                if ($LASTEXITCODE -eq 0) { Write-Host "Switched to $($selectedSub.Name)"; break }
                else { Write-Host "Failed to switch. Try again." }
            } else { Write-Host "Invalid selection." }
        } while ($true)
    } else { az account set --subscription $currentSubscriptionId }
}

# Track public access state
$stWasDisabled = $false
$srchWasDisabled = $false

# Enable public access if needed
$stAccess = az storage account show --name $StorageAccount --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv
if ($stAccess -eq "Disabled") { 
    $stWasDisabled = $true
    Write-Host "Enabling public access for storage account $StorageAccount"
    az storage account update --name $StorageAccount --resource-group $ResourceGroup --public-network-access Enabled --default-action Allow --output none
}

$srchAccess = az search service show --name $AiSearch --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv
if ($srchAccess -eq "Disabled") {
    $srchWasDisabled = $true
    Write-Host "Enabling public access for search service $AiSearch"
    az search service update --name $AiSearch --resource-group $ResourceGroup --public-network-access Enabled --output none
}

# Upload PDFs
Write-Host "Uploading RFP PDFs to blob storage..."
az storage blob upload-batch --account-name $StorageAccount --destination $BlobContainer --source "data/dataset/RFP_dataset" --auth-mode login --pattern "*.pdf" --overwrite --output none
if ($LASTEXITCODE -ne 0) { Write-Host "Upload failed."; exit 1 }
Write-Host "Upload complete."

# Determine Python
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { Write-Host "Python not found"; exit 1 }

# Virtual environment
$venvPath = "infra/scripts/scriptenv"
if (-not (Test-Path $venvPath)) { Write-Host "Creating virtual environment"; & $pythonCmd -m venv $venvPath }

# Activate virtual environment
$activateScript = if (Test-Path "$venvPath\Scripts\Activate.ps1") { "$venvPath\Scripts\Activate.ps1" } elseif (Test-Path "$venvPath/bin/Activate.ps1") { "$venvPath/bin/Activate.ps1" } else { "" }
if ($activateScript) { Write-Host "Activating venv"; . $activateScript }

# Install requirements
Write-Host "Installing Python requirements"
pip install --quiet -r infra/scripts/requirements.txt
Write-Host "Requirements installed."

# Run Python indexer
Write-Host "Running RFP indexer"
$process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_rfp_data.py", $StorageAccount, $BlobContainer, $AiSearch, $AiSearchIndex -Wait -NoNewWindow -PassThru
if ($process.ExitCode -ne 0) { Write-Host "Indexing failed."; exit 1 }

# Restore public access
if ($stWasDisabled) { az storage account update --name $StorageAccount --resource-group $ResourceGroup --public-network-access Disabled --default-action Deny --output none }
if ($srchWasDisabled) { az search service update --name $AiSearch --resource-group $ResourceGroup --public-network-access Disabled --output none }

Write-Host "RFP PDFs uploaded and indexed successfully."

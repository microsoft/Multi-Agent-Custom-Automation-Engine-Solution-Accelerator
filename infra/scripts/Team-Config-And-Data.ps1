#Requires -Version 7.0

param(
    [string]$ResourceGroup
)

# Variables
$directoryPath = ""
$backendUrl = ""
$storageAccount = ""
$blobContainer = ""
$aiSearch = ""
$aiSearchIndex = ""
$azSubscriptionId = ""

function Test-AzdInstalled {
    try {
        $null = Get-Command azd -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Get-ValuesFromAzdEnv {
    if (-not (Test-AzdInstalled)) {
        Write-Host "Error: Azure Developer CLI is not installed."
        return $false
    }

    Write-Host "Getting values from azd environment..."
    
    $script:directoryPath = "data/agent_teams"
    $script:backendUrl = $(azd env get-value BACKEND_URL)
    $script:storageAccount = $(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
    $script:blobContainer = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME)
    $script:aiSearch = $(azd env get-value AZURE_AI_SEARCH_NAME)
    $script:aiSearchIndex = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME)
    $script:ResourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP)
    
    # Validate that we got all required values
    if (-not $script:backendUrl -or -not $script:storageAccount -or -not $script:blobContainer -or -not $script:aiSearch -or -not $script:aiSearchIndex -or -not $script:ResourceGroup) {
        Write-Host "Error: Could not retrieve all required values from azd environment."
        return $false
    }
    
    Write-Host "Successfully retrieved values from azd environment."
    return $true
}

function Get-ValuesFromAzDeployment {
    Write-Host "Getting values from Azure deployment outputs..."
    
    $script:directoryPath = "data/agent_teams"
    
    Write-Host "Fetching deployment name..."
    $deploymentName = az group show --name $ResourceGroup --query "tags.DeploymentName" -o tsv
    if (-not $deploymentName) {
        Write-Host "Error: Could not find deployment name in resource group tags."
        return $false
    }
    
    Write-Host "Fetching deployment outputs for deployment: $deploymentName"
    $deploymentOutputs = az deployment group show --resource-group $ResourceGroup --name $deploymentName --query "properties.outputs" -o json | ConvertFrom-Json
    if (-not $deploymentOutputs) {
        Write-Host "Error: Could not fetch deployment outputs."
        return $false
    }
    
    # Extract specific outputs
    $script:storageAccount = $deploymentOutputs.azurE_STORAGE_ACCOUNT_NAME.value
    $script:blobContainer = $deploymentOutputs.azurE_STORAGE_CONTAINER_NAME.value
    $script:aiSearch = $deploymentOutputs.azurE_AI_SEARCH_NAME.value
    $script:aiSearchIndex = $deploymentOutputs.azurE_AI_SEARCH_INDEX_NAME.value
    $script:backendUrl = $deploymentOutputs.backenD_URL.value
    
    # Validate that we extracted all required values
    if (-not $script:storageAccount -or -not $script:blobContainer -or -not $script:aiSearch -or -not $script:aiSearchIndex -or -not $script:backendUrl) {
        Write-Host "Error: Could not extract all required values from deployment outputs."
        return $false
    }
    
    Write-Host "Successfully retrieved values from deployment outputs."
    return $true
}

# Authenticate with Azure
try {
    $null = az account show 2>$null
    Write-Host "Already authenticated with Azure."
} catch {
    Write-Host "Not authenticated with Azure. Attempting to authenticate..."
    Write-Host "Authenticating with Azure CLI..."
    az login
}

# Get subscription ID from azd if available
if (Test-AzdInstalled) {
    try {
        $azSubscriptionId = $(azd env get-value AZURE_SUBSCRIPTION_ID)
        if (-not $azSubscriptionId) {
            $azSubscriptionId = $env:AZURE_SUBSCRIPTION_ID
        }
    } catch {
        $azSubscriptionId = ""
    }
}

# Check if user has selected the correct subscription
$currentSubscriptionId = az account show --query id -o tsv
$currentSubscriptionName = az account show --query name -o tsv

if ($currentSubscriptionId -ne $azSubscriptionId -and $azSubscriptionId) {
    Write-Host "Current selected subscription is $currentSubscriptionName ( $currentSubscriptionId )."
    $confirmation = Read-Host "Do you want to continue with this subscription?(y/n)"
    if ($confirmation -notin @("y", "Y")) {
        Write-Host "Fetching available subscriptions..."
        $availableSubscriptions = az account list --query "[?state=='Enabled'].[name,id]" --output tsv
        $subscriptions = $availableSubscriptions -split "`n" | ForEach-Object { $_.Split("`t") }
        
        do {
            Write-Host ""
            Write-Host "Available Subscriptions:"
            Write-Host "========================"
            for ($i = 0; $i -lt $subscriptions.Count; $i += 2) {
                $index = ($i / 2) + 1
                Write-Host "$index. $($subscriptions[$i]) ( $($subscriptions[$i + 1]) )"
            }
            Write-Host "========================"
            Write-Host ""
            
            $subscriptionIndex = Read-Host "Enter the number of the subscription (1-$(($subscriptions.Count / 2))) to use"
            
            if ($subscriptionIndex -match '^\d+$' -and [int]$subscriptionIndex -ge 1 -and [int]$subscriptionIndex -le ($subscriptions.Count / 2)) {
                $selectedIndex = ([int]$subscriptionIndex - 1) * 2
                $selectedSubscriptionName = $subscriptions[$selectedIndex]
                $selectedSubscriptionId = $subscriptions[$selectedIndex + 1]
                
                try {
                    az account set --subscription $selectedSubscriptionId
                    Write-Host "Switched to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )"
                    $azSubscriptionId = $selectedSubscriptionId
                    break
                } catch {
                    Write-Host "Failed to switch to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )."
                }
            } else {
                Write-Host "Invalid selection. Please try again."
            }
        } while ($true)
    } else {
        Write-Host "Proceeding with the current subscription: $currentSubscriptionName ( $currentSubscriptionId )"
        az account set --subscription $currentSubscriptionId
        $azSubscriptionId = $currentSubscriptionId
    }
} else {
    Write-Host "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    az account set --subscription $currentSubscriptionId
    $azSubscriptionId = $currentSubscriptionId
}

# Get configuration values based on strategy
if (-not $ResourceGroup) {
    # No resource group provided - use azd env
    if (-not (Get-ValuesFromAzdEnv)) {
        Write-Host "Failed to get values from azd environment."
        Write-Host "If you want to use deployment outputs instead, please provide the resource group name as an argument."
        Write-Host "Usage: .\Team-Config-And-Data.ps1 [-ResourceGroup <ResourceGroupName>]"
        exit 1
    }
} else {
    # Resource group provided - use deployment outputs
    Write-Host "Resource group provided: $ResourceGroup"
    
    if (-not (Get-ValuesFromAzDeployment)) {
        Write-Host "Failed to get values from deployment outputs."
        exit 1
    }
}

Write-Host ""
Write-Host "==============================================="
Write-Host "Values to be used:"
Write-Host "==============================================="
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Backend URL: $backendUrl"
Write-Host "Storage Account: $storageAccount"
Write-Host "Blob Container: $blobContainer"
Write-Host "AI Search: $aiSearch"
Write-Host "AI Search Index: $aiSearchIndex"
Write-Host "Directory Path: $directoryPath"
Write-Host "Subscription ID: $azSubscriptionId"
Write-Host "==============================================="
Write-Host ""

# Check if all required arguments are provided
if (-not $backendUrl -or -not $directoryPath -or -not $storageAccount -or -not $blobContainer -or -not $aiSearch -or -not $aiSearchIndex -or -not $ResourceGroup) {
    Write-Host "Error: Missing required configuration values."
    Write-Host "Usage: .\Team-Config-And-Data.ps1 [-ResourceGroup <ResourceGroupName>]"
    exit 1
}

$isTeamConfigFailed = $false
$isSampleDataFailed = $false

# Upload Team Configuration
Write-Host "Uploading Team Configuration..."
try {
    .\infra\scripts\Upload-Team-Config.ps1 -backendUrl $backendUrl -DirectoryPath $directoryPath -AzSubscriptionId $azSubscriptionId
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
    }
} catch {
    Write-Host "Error: Uploading team configuration failed."
    $isTeamConfigFailed = $true
}

Write-Host "`n----------------------------------------"
Write-Host "----------------------------------------`n"

# Process Sample Data
Write-Host "Processing Sample Data..."
try {
    .\infra\scripts\Process-Sample-Data.ps1 -StorageAccount $storageAccount -BlobContainer $blobContainer -AiSearch $aiSearch -AiSearchIndex $aiSearchIndex -ResourceGroup $ResourceGroup -AzSubscriptionId $azSubscriptionId
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Processing sample data failed."
        $isSampleDataFailed = $true
    }
} catch {
    Write-Host "Error: Processing sample data failed."
    $isSampleDataFailed = $true
}

if ($isTeamConfigFailed -or $isSampleDataFailed) {
    Write-Host "`nOne or more tasks failed. Please check the error messages above."
    exit 1
} else {
    Write-Host "`nBoth team configuration upload and sample data processing completed successfully."
}

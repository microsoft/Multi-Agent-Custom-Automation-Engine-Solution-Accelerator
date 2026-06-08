#Requires -Version 7.0

param(
    [string]$ResourceGroup
)

# Variables
$backendUrl = ""
$storageAccount = ""
$aiSearch = ""
$azSubscriptionId = ""
$stIsPublicAccessDisabled = $false
$srchIsPublicAccessDisabled = $false

# Cleanup function to restore network access
function Restore-NetworkAccess {
    if ($script:ResourceGroup -and $script:storageAccount -and $script:aiSearch) {
        # Check resource group tag
        $rgTypeTag = (az group show --name $script:ResourceGroup --query "tags.Type" -o tsv 2>$null)
        
        if ($rgTypeTag -eq "WAF") {
            if ($script:stIsPublicAccessDisabled -eq $true -or $script:srchIsPublicAccessDisabled -eq $true) {
                Write-Host "=== Restoring network access settings ==="
            }
            
            if ($script:stIsPublicAccessDisabled -eq $true) {
                $currentAccess = $(az storage account show --name $script:storageAccount --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
                if ($currentAccess -eq "Enabled") {
                    Write-Host "Disabling public access for Storage Account: $($script:storageAccount)"
                    az storage account update --name $script:storageAccount --public-network-access disabled --default-action Deny --output none 2>$null
                    Write-Host "✓ Storage Account public access disabled"
                } else {
                    Write-Host "✓ Storage Account access unchanged (already at desired state)"
                }
            } else {
                if ($script:ResourceGroup) {
                    $checkTag = (az group show --name $script:ResourceGroup --query "tags.Type" -o tsv 2>$null)
                    if ($checkTag -eq "WAF") {
                        if ($script:stIsPublicAccessDisabled -eq $false -and $script:srchIsPublicAccessDisabled -eq $false) {
                            Write-Host "=== Restoring network access settings ==="
                        }
                        Write-Host "✓ Storage Account access unchanged (already at desired state)"
                    }
                }
            }
            
            if ($script:srchIsPublicAccessDisabled -eq $true) {
                $currentAccess = $(az search service show --name $script:aiSearch --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
                if ($currentAccess -eq "Enabled") {
                    Write-Host "Disabling public access for AI Search Service: $($script:aiSearch)"
                    az search service update --name $script:aiSearch --resource-group $script:ResourceGroup --public-network-access disabled --output none 2>$null
                    Write-Host "✓ AI Search Service public access disabled"
                } else {
                    Write-Host "✓ AI Search Service access unchanged (already at desired state)"
                }
            } else {
                if ($script:ResourceGroup) {
                    $checkTag = (az group show --name $script:ResourceGroup --query "tags.Type" -o tsv 2>$null)
                    if ($checkTag -eq "WAF") {
                        Write-Host "✓ AI Search Service access unchanged (already at desired state)"
                    }
                }
            }
            
            if ($script:stIsPublicAccessDisabled -eq $true -or $script:srchIsPublicAccessDisabled -eq $true) {
                Write-Host "=========================================="
            } else {
                if ($script:ResourceGroup) {
                    $checkTag = (az group show --name $script:ResourceGroup --query "tags.Type" -o tsv 2>$null)
                    if ($checkTag -eq "WAF") {
                        Write-Host "=========================================="
                    }
                }
            }
        }
    }
}

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
    
    $script:backendUrl = $(azd env get-value BACKEND_URL)
    $script:storageAccount = $(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
    $script:aiSearch = $(azd env get-value AZURE_AI_SEARCH_NAME)
    $script:ResourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP)
    
    # Validate that we got all required values
    if (-not $script:backendUrl -or -not $script:storageAccount -or -not $script:aiSearch -or -not $script:ResourceGroup) {
        Write-Host "Error: Could not retrieve all required values from azd environment."
        return $false
    }
    
    Write-Host "Successfully retrieved values from azd environment."
    return $true
}

function Get-DeploymentValue {
    param(
        [object]$DeploymentOutputs,
        [string]$PrimaryKey,
        [string]$FallbackKey
    )
    
    $value = $null
    
    # Try primary key first
    if ($DeploymentOutputs.PSObject.Properties[$PrimaryKey]) {
        $value = $DeploymentOutputs.$PrimaryKey.value
    }
    
    # If primary key failed, try fallback key
    if (-not $value -and $DeploymentOutputs.PSObject.Properties[$FallbackKey]) {
        $value = $DeploymentOutputs.$FallbackKey.value
    }
    
    return $value
}

function Get-ValuesFromAzDeployment {
    Write-Host "Getting values from Azure deployment outputs..."
    
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
    
    # Extract specific outputs with fallback logic
    $script:storageAccount = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_ACCOUNT_NAME" -FallbackKey "azureStorageAccountName"
    $script:aiSearch = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_NAME" -FallbackKey "azureAiSearchName"
    $script:backendUrl = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "backenD_URL" -FallbackKey "backendUrl"
    
    # Validate that we extracted all required values
    if (-not $script:storageAccount -or -not $script:aiSearch -or -not $script:backendUrl) {
        Write-Host "Error: Could not extract all required values from deployment outputs."
        return $false
    }
    
    Write-Host "Successfully retrieved values from deployment outputs."
    return $true
}

function Get-ValuesUsingSolutionSuffix {
    Write-Host "Getting values from resource naming convention using solution suffix..."
    
    # Get the solution suffix from resource group tags
    $solutionSuffix = az group show --name $ResourceGroup --query "tags.SolutionSuffix" -o tsv
    if (-not $solutionSuffix) {
        Write-Host "Error: Could not find SolutionSuffix tag in resource group."
        return $false
    }
    
    Write-Host "Found solution suffix: $solutionSuffix"
    
    # Reconstruct resource names using same naming convention as Bicep
    $script:storageAccount = "st$solutionSuffix" -replace '-', ''  # Remove dashes like Bicep does
    $script:aiSearch = "srch-$solutionSuffix"
    $containerAppName = "ca-$solutionSuffix"
    
    # Query dynamic value (backend URL) from Container App
    Write-Host "Querying backend URL from Container App..."
    $backendFqdn = az containerapp show `
      --name $containerAppName `
      --resource-group $ResourceGroup `
      --query "properties.configuration.ingress.fqdn" `
      -o tsv 2>$null
    
    if (-not $backendFqdn) {
        Write-Host "Error: Could not get Container App FQDN. Container App may not be deployed yet."
        return $false
    }
    
    $script:backendUrl = "https://$backendFqdn"
    
    # Validate that we got all critical values
    if (-not $script:storageAccount -or -not $script:aiSearch -or -not $script:backendUrl) {
        Write-Host "Error: Failed to reconstruct all required resource names."
        return $false
    }
    
    Write-Host "Successfully reconstructed values from resource naming convention."
    return $true
}

function Deploy-ContentPack {
    param(
        [string]$PackPath,
        [string]$StorageAccountName,
        [string]$AiSearchName,
        [string]$PythonCmd
    )

    $packJsonPath = Join-Path $PackPath "pack.json"
    if (-not (Test-Path $packJsonPath)) {
        Write-Host "  No pack.json found at $packJsonPath - skipping data deployment."
        return $true
    }

    $pack = Get-Content $packJsonPath -Raw | ConvertFrom-Json
    Write-Host "  Deploying data for content pack: $($pack.name)"
    $hadFailure = $false

    # Process blob_indexes: upload files to blob container, then create search index
    if ($pack.blob_indexes) {
        foreach ($entry in $pack.blob_indexes) {
            $container = $entry.container
            $sourcePath = Join-Path $PackPath $entry.source
            $pattern = if ($entry.pattern) { $entry.pattern } else { "*" }
            $indexName = $entry.index_name

            if (-not (Test-Path $sourcePath)) {
                Write-Host "  Warning: source directory not found: $sourcePath. Skipping."
                $hadFailure = $true
                continue
            }

            # Ensure container exists
            az storage container create --account-name $StorageAccountName --name $container --auth-mode login --output none 2>$null

            Write-Host "  Uploading blobs to container '$container'..."
            az storage blob upload-batch --account-name $StorageAccountName --destination $container --source $sourcePath --auth-mode login --pattern $pattern --overwrite --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Error: Failed to upload blobs to container '$container'."
                $hadFailure = $true
                continue
            }

            Write-Host "  Creating search index '$indexName' from container '$container'..."
            $process = Start-Process -FilePath $PythonCmd -ArgumentList "infra/scripts/index_datasets.py", $StorageAccountName, $container, $AiSearchName, $indexName -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  Error: Indexing failed for '$indexName'."
                $hadFailure = $true
            }
        }
    }

    # Process blob_uploads: upload files only (no indexing)
    if ($pack.blob_uploads) {
        foreach ($entry in $pack.blob_uploads) {
            $container = $entry.container
            $sourcePath = Join-Path $PackPath $entry.source
            $pattern = if ($entry.pattern) { $entry.pattern } else { "*" }

            if (-not (Test-Path $sourcePath)) {
                Write-Host "  Warning: source directory not found: $sourcePath. Skipping."
                $hadFailure = $true
                continue
            }

            # Ensure container exists
            az storage container create --account-name $StorageAccountName --name $container --auth-mode login --output none 2>$null

            Write-Host "  Uploading blobs to container '$container'..."
            az storage blob upload-batch --account-name $StorageAccountName --destination $container --source $sourcePath --auth-mode login --pattern $pattern --overwrite --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Error: Failed to upload blobs to container '$container'."
                $hadFailure = $true
            }
        }
    }

    # Process search_indexes: create indexes from already-uploaded blob data
    if ($pack.search_indexes) {
        foreach ($entry in $pack.search_indexes) {
            $indexName = $entry.index_name
            # Use the first blob_uploads container as the data source
            $container = $null
            if ($pack.blob_uploads -and $pack.blob_uploads.Count -gt 0) {
                $container = $pack.blob_uploads[0].container
            }
            if (-not $container) {
                Write-Host "  Warning: No blob container found for search_index '$indexName'. Skipping."
                continue
            }

            Write-Host "  Creating search index '$indexName' from container '$container'..."
            $process = Start-Process -FilePath $PythonCmd -ArgumentList "infra/scripts/index_datasets.py", $StorageAccountName, $container, $AiSearchName, $indexName -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  Error: Indexing failed for '$indexName'."
                $hadFailure = $true
            }
        }
    }

    if ($hadFailure) {
        return $false
    }
    return $true
}

# Main script execution with cleanup handling
try {
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
    # Resource group provided - try deployment outputs first, then fallback to naming convention
    Write-Host "Resource group provided: $ResourceGroup"
    
    if (-not (Get-ValuesFromAzDeployment)) {
        Write-Host ""
        Write-Host "Warning: Could not retrieve values from deployment outputs (deployment may be deleted)."
        Write-Host "Attempting fallback method: reconstructing values from resource naming convention..."
        Write-Host ""
        
        if (-not (Get-ValuesUsingSolutionSuffix)) {
            Write-Host ""
            Write-Host "Error: Both methods failed to retrieve configuration values."
            Write-Host "Please ensure:"
            Write-Host "  1. The deployment exists and has a DeploymentName tag, OR"
            Write-Host "  2. The resource group has a SolutionSuffix tag"
            exit 1
        }
    }
}

# Interactive Use Case Selection
Write-Host ""
Write-Host "==============================================="
Write-Host "Available Use Cases:"
Write-Host "==============================================="
Write-Host "1. RFP Evaluation"
Write-Host "2. Retail Customer Satisfaction"
Write-Host "3. HR Employee Onboarding"
Write-Host "4. Marketing Press Release"
Write-Host "5. Contract Compliance Review"
Write-Host "6. Content Generation"
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ NEW CONTENT PACK: Add a new menu entry here.                                │
# │ Just add the next number — "All" is always printed last automatically.      │
# │ Example:                                                                    │
# │   Write-Host "7. Your Pack Name"                                            │
# └─────────────────────────────────────────────────────────────────────────────┘
$allOption = 7  # ← UPDATE: set this to (highest use-case number + 1) when adding a new pack
Write-Host "$allOption. All"
Write-Host "==============================================="
Write-Host ""

# Prompt user for use case selection
do {
    $useCaseSelection = Read-Host "Please enter the number of the use case you would like to install."
    
    # Normalize: if the user types the "All" number or the word "all", set to "all"
    if ($useCaseSelection -eq "all" -or $useCaseSelection -eq "$allOption") {
        $useCaseSelection = "all"
        $selectedUseCase = "All"
        $useCaseValid = $true
        Write-Host "Selected: All use cases will be installed."
    }
    elseif ($useCaseSelection -eq "1") {
        $selectedUseCase = "RFP Evaluation"
        $useCaseValid = $true
        Write-Host "Selected: RFP Evaluation"
        Write-Host "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    }
    elseif ($useCaseSelection -eq "2") {
        $selectedUseCase = "Retail Customer Satisfaction"
        $useCaseValid = $true
        Write-Host "Selected: Retail Customer Satisfaction"
        Write-Host "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    }
    elseif ($useCaseSelection -eq "3") {
        $selectedUseCase = "HR Employee Onboarding"
        $useCaseValid = $true
        Write-Host "Selected: HR Employee Onboarding"
        Write-Host "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    }
    elseif ($useCaseSelection -eq "4") {
        $selectedUseCase = "Marketing Press Release"
        $useCaseValid = $true
        Write-Host "Selected: Marketing Press Release"
        Write-Host "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    }
    elseif ($useCaseSelection -eq "5") {
        $selectedUseCase = "Contract Compliance Review"
        $useCaseValid = $true
        Write-Host "Selected: Contract Compliance Review"
        Write-Host "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    }
    elseif ($useCaseSelection -eq "6") {
        $selectedUseCase = "Content Generation"
        $useCaseValid = $true
        Write-Host "Selected: Content Generation"
        Write-Host "Note: If you choose to install a single use case, installation of other use cases will require re-running this script."
    }
    # ┌─────────────────────────────────────────────────────────────────────────┐
    # │ NEW CONTENT PACK: Add an elseif block for your menu number.             │
    # │ Example:                                                                │
    # │   elseif ($useCaseSelection -eq "7") {                                  │
    # │       $selectedUseCase = "Your Pack Name"                               │
    # │       $useCaseValid = $true                                             │
    # │       Write-Host "Selected: Your Pack Name"                             │
    # │       Write-Host "Note: If you choose to install a single use case..."  │
    # │   }                                                                     │
    # │ Then update $allOption above to (new number + 1).                       │
    # └─────────────────────────────────────────────────────────────────────────┘
    else {
        $useCaseValid = $false
        Write-Host "Invalid selection. Please enter a number from 1-$allOption." -ForegroundColor Red
    }
} while (-not $useCaseValid)

# WAF/Private Networking: If the Container App has IP restrictions or internal ingress,
# the backendUrl is not reachable from the developer's machine. Route through the frontend
# App Service proxy instead, which is public and forwards /api/* to the private backend over VNet.
$solutionSuffix = az group show --name $ResourceGroup --query "tags.SolutionSuffix" -o tsv 2>$null
if ($solutionSuffix) {
    $containerAppName = "ca-$solutionSuffix"
    $isExternal = az containerapp show --name $containerAppName --resource-group $ResourceGroup `
        --query "properties.configuration.ingress.external" -o tsv 2>$null
    $hasIpRestrictions = az containerapp show --name $containerAppName --resource-group $ResourceGroup `
        --query "length(properties.configuration.ingress.ipSecurityRestrictions || ``[]``)" -o tsv 2>$null
    $proxyEnabled = az webapp config appsettings list --name "app-$solutionSuffix" --resource-group $ResourceGroup `
        --query "[?name=='PROXY_API_REQUESTS'].value" -o tsv 2>$null
    if ($isExternal -eq "false" -or [int]$hasIpRestrictions -gt 0 -or $proxyEnabled -eq "true") {
        $frontendHostname = "app-$solutionSuffix"
        $frontendUrl = "https://${frontendHostname}.azurewebsites.net"
        Write-Host "Private networking detected: Container App has restricted access."
        Write-Host "Routing API calls through frontend App Service: $frontendUrl"
        $script:backendUrl = $frontendUrl
    }
}

Write-Host ""
Write-Host "==============================================="
Write-Host "Values to be used:"
Write-Host "==============================================="
Write-Host "Selected Use Case: $selectedUseCase"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Backend URL: $backendUrl"
Write-Host "Storage Account: $storageAccount"
Write-Host "AI Search: $aiSearch"
Write-Host "Subscription ID: $azSubscriptionId"
Write-Host "==============================================="
Write-Host ""


$userPrincipalId = $(az ad signed-in-user show --query id -o tsv)

# Determine the correct Python command
$pythonCmd = $null

try {
    $pythonVersion = (python --version) 2>&1
    if ($pythonVersion -match "Python \d") {
        $pythonCmd = "python"
    }
} 
catch {
    # Do nothing, try python3 next
}

if (-not $pythonCmd) {
    try {
        $pythonVersion = (python3 --version) 2>&1
        if ($pythonVersion -match "Python \d") {
            $pythonCmd = "python3"
        }
    }
    catch {
        Write-Host "Python is not installed on this system or it is not added in the PATH."
        exit 1
    }
}

if (-not $pythonCmd) {
    Write-Host "Python is not installed on this system or it is not added in the PATH."
    exit 1
}

# Create virtual environment
$venvPath = "infra/scripts/scriptenv"
if (Test-Path $venvPath) {
    Write-Host "Virtual environment already exists. Skipping creation."
} else {
    Write-Host "Creating virtual environment"
    & $pythonCmd -m venv $venvPath
}

# Activate the virtual environment
$activateScript = ""
if (Test-Path (Join-Path -Path $venvPath -ChildPath "bin/Activate.ps1")) {
    $activateScript = Join-Path -Path $venvPath -ChildPath "bin/Activate.ps1"
} elseif (Test-Path (Join-Path -Path $venvPath -ChildPath "Scripts/Activate.ps1")) {
    $activateScript = Join-Path -Path $venvPath -ChildPath "Scripts/Activate.ps1"
}
if ($activateScript) {
    Write-Host "Activating virtual environment"
    . $activateScript
} else {
    Write-Host "Error activating virtual environment. Requirements may be installed globally."
}

# Install the requirements
Write-Host "Installing requirements"
pip install --quiet -r infra/scripts/requirements.txt
Write-Host "Requirements installed"

$isTeamConfigFailed = $false
$isSampleDataFailed = $false
$failedTeamConfigs = 0

# Use Case 3 -----=--
if($useCaseSelection -eq "3" -or $useCaseSelection -eq "all") {
    Write-Host "Uploading Team Configuration for HR Employee Onboarding..."
    $teamConfigDir = "content_packs/hr_onboarding/agent_teams"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000001" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for HR Employee Onboarding upload failed."
            $isTeamConfigFailed = $true
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
        $failedTeamConfigs += 1
    }
}

# Use Case 4 -----=--
if($useCaseSelection -eq "4" -or $useCaseSelection -eq "all") {
    Write-Host "Uploading Team Configuration for Marketing Press Release..."
    $teamConfigDir = "content_packs/marketing_press_release/agent_teams"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000002" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for Marketing Press Release upload failed."
            $isTeamConfigFailed = $true
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
        $failedTeamConfigs += 1
    }
}

$stIsPublicAccessDisabled = $false
$srchIsPublicAccessDisabled = $false
# Enable public access for resources
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ NEW CONTENT PACK: If your pack uploads data to blob/search, add your menu   │
# │ number to this condition so network access is enabled for WAF deployments.  │
# │ Example: -or $useCaseSelection -eq "7"                                      │
# └─────────────────────────────────────────────────────────────────────────────┘
if($useCaseSelection -eq "1"-or $useCaseSelection -eq "2" -or $useCaseSelection -eq "5" -or $useCaseSelection -eq "6" -or $useCaseSelection -eq "all"){
    if ($ResourceGroup) {
        # Check if resource group has Type=WAF tag
        $rgTypeTag = (az group show --name $ResourceGroup --query "tags.Type" -o tsv 2>$null)
        
        if ($rgTypeTag -eq "WAF") {
            Write-Host ""
            Write-Host "=== Temporarily enabling public network access for services ==="
            $stPublicAccess = $(az storage account show --name $storageAccount --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv)
            if ($stPublicAccess -eq "Disabled") {
                $stIsPublicAccessDisabled = $true
                Write-Host "Enabling public access for Storage Account: $storageAccount"
                az storage account update --name $storageAccount --public-network-access enabled --default-action Allow --output none
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "Error: Failed to enable public access for storage account."
                    exit 1
                }
                
                # Wait 30 seconds for the change to propagate
                Write-Host "Waiting 30 seconds for public access to be enabled..."
                Start-Sleep -Seconds 30
                
                # Verify public access is enabled in a loop
                Write-Host "Verifying public access is enabled..."
                $maxRetries = 10
                $retryCount = 0
                while ($retryCount -lt $maxRetries) {
                    $currentAccess = $(az storage account show --name $storageAccount --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv)
                    if ($currentAccess -eq "Enabled") {
                        Write-Host "✓ Storage Account public access enabled successfully"
                        break
                    } else {
                        Write-Host "Public access not yet enabled (attempt $($retryCount + 1)/$maxRetries). Waiting 5 seconds..."
                        Start-Sleep -Seconds 5
                        $retryCount++
                    }
                }
                
                if ($retryCount -eq $maxRetries) {
                    Write-Host "Warning: Public access verification timed out for storage account."
                }
            } else {
                Write-Host "✓ Storage Account public access already enabled"
            }
        }

        if ($rgTypeTag -eq "WAF") {
            $srchPublicAccess = $(az search service show --name $aiSearch --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv)
            if ($srchPublicAccess -eq "Disabled") {
                $srchIsPublicAccessDisabled = $true
                Write-Host "Enabling public access for AI Search Service: $aiSearch"
                az search service update --name $aiSearch --resource-group $ResourceGroup --public-network-access enabled --output none
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "Error: Failed to enable public access for search service."
                    exit 1
                }
                Write-Host "Public access enabled"
                
                # Wait 30 seconds for the change to propagate
                Write-Host "Waiting 30 seconds for public access to be enabled..."
                Start-Sleep -Seconds 30
                
                # Verify public access is enabled in a loop
                Write-Host "Verifying public access is enabled..."
                $maxRetries = 10
                $retryCount = 0
                while ($retryCount -lt $maxRetries) {
                    $currentAccess = $(az search service show --name $aiSearch --resource-group $ResourceGroup --query "publicNetworkAccess" -o tsv)
                    if ($currentAccess -eq "Enabled") {
                        Write-Host "✓ AI Search Service public access enabled successfully"
                        break
                    } else {
                        Write-Host "Public access not yet enabled (attempt $($retryCount + 1)/$maxRetries). Waiting 5 seconds..."
                        Start-Sleep -Seconds 5
                        $retryCount++
                    }
                }
                
                if ($retryCount -eq $maxRetries) {
                    Write-Host "Warning: Public access verification timed out for search service."
                }
            } else {
                Write-Host "✓ AI Search Service public access already enabled"
            }
            Write-Host "==========================================================="
            Write-Host ""
        }
    }
}



if($useCaseSelection -eq "1" -or $useCaseSelection -eq "all") {
    Write-Host "Uploading Team Configuration for RFP Evaluation..."
    $teamConfigDir = "content_packs/rfp_evaluation/agent_teams"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000004" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for RFP Evaluation upload failed."
            $failedTeamConfigs += 1
            $isTeamConfigFailed = $true
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
    }
    Write-Host "Uploaded Team Configuration for RFP Evaluation..."

    Write-Host "Deploying data for RFP Evaluation content pack..."
    $packResult = Deploy-ContentPack -PackPath "content_packs/rfp_evaluation" -StorageAccountName $storageAccount -AiSearchName $aiSearch -PythonCmd $pythonCmd
    if (-not $packResult) {
        Write-Host "Error: Data deployment for RFP Evaluation failed."
        $isSampleDataFailed = $true
    } else {
        Write-Host "Data deployment for RFP Evaluation completed successfully."
    }
}


if($useCaseSelection -eq "5" -or $useCaseSelection -eq "all") {
    Write-Host "Uploading Team Configuration for Contract Compliance Review..."
    $teamConfigDir = "content_packs/contract_compliance/agent_teams"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000005" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for Contract Compliance Review upload failed."
            $failedTeamConfigs += 1
            $isTeamConfigFailed = $true
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
    }
    Write-Host "Uploaded Team Configuration for Contract Compliance Review..."

    Write-Host "Deploying data for Contract Compliance content pack..."
    $packResult = Deploy-ContentPack -PackPath "content_packs/contract_compliance" -StorageAccountName $storageAccount -AiSearchName $aiSearch -PythonCmd $pythonCmd
    if (-not $packResult) {
        Write-Host "Error: Data deployment for Contract Compliance failed."
        $isSampleDataFailed = $true
    } else {
        Write-Host "Data deployment for Contract Compliance completed successfully."
    }
}

if($useCaseSelection -eq "2" -or $useCaseSelection -eq "all") {
    Write-Host "Uploading Team Configuration for Retail Customer Satisfaction..."
    $teamConfigDir = "content_packs/retail_customer/agent_teams"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000003" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for Retail Customer Satisfaction upload failed."
            $failedTeamConfigs += 1
            $isTeamConfigFailed = $true
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
    }
    Write-Host "Uploaded Team Configuration for Retail Customer Satisfaction..."

    Write-Host "Deploying data for Retail Customer content pack..."
    $packResult = Deploy-ContentPack -PackPath "content_packs/retail_customer" -StorageAccountName $storageAccount -AiSearchName $aiSearch -PythonCmd $pythonCmd
    if (-not $packResult) {
        Write-Host "Error: Data deployment for Retail Customer Satisfaction failed."
        $isSampleDataFailed = $true
    } else {
        Write-Host "Data deployment for Retail Customer Satisfaction completed successfully."
    }
}

if($useCaseSelection -eq "6" -or $useCaseSelection -eq "all") {
    Write-Host "Uploading Team Configuration for Content Generation..."
    $teamConfigDir = "content_packs/content_gen/agent_teams"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000007" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for Content Generation upload failed."
            $failedTeamConfigs += 1
            $isTeamConfigFailed = $true
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed."
        $isTeamConfigFailed = $true
    }
    Write-Host "Uploaded Team Configuration for Content Generation..."

    Write-Host "Deploying data for Content Generation content pack..."
    $packResult = Deploy-ContentPack -PackPath "content_packs/content_gen" -StorageAccountName $storageAccount -AiSearchName $aiSearch -PythonCmd $pythonCmd
    if (-not $packResult) {
        Write-Host "Error: Data deployment for Content Generation failed."
        $isSampleDataFailed = $true
    } else {
        Write-Host "Data deployment for Content Generation completed successfully."
    }
}

# ┌─────────────────────────────────────────────────────────────────────────────────┐
# │ NEW CONTENT PACK: Add a deployment block here. Copy and customize this template.│
# │                                                                                 │
# │ Three things to change:                                                         │
# │   1. The menu number in the condition (e.g. "8")                                │
# │   2. The team config directory path                                             │
# │   3. The team UUID (must be unique, use a new one from uuidgen or online tool)  │
# │                                                                                 │
# │ The "all" check is handled automatically — just use your number + "all".        │
# │ If your pack has data (CSV/PDF), also add Deploy-ContentPack.                   │
# │ If it does NOT have data (no pack.json indexes), skip Deploy-ContentPack.       │
# └─────────────────────────────────────────────────────────────────────────────────┘
# if($useCaseSelection -eq "7" -or $useCaseSelection -eq "all") {
#     # ── Step 1: Upload team config ──
#     Write-Host "Uploading Team Configuration for Your Pack Name..."
#     $teamConfigDir = "content_packs/your_pack/agent_teams"
#     try {
#         $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $teamConfigDir, $userPrincipalId, "00000000-0000-0000-0000-000000000008" -Wait -NoNewWindow -PassThru
#         if ($process.ExitCode -ne 0) {
#             Write-Host "Error: Team configuration for Your Pack Name upload failed."
#             $failedTeamConfigs += 1
#             $isTeamConfigFailed = $true
#         }
#     } catch {
#         Write-Host "Error: Uploading team configuration failed."
#         $isTeamConfigFailed = $true
#     }
#     Write-Host "Uploaded Team Configuration for Your Pack Name..."
#
#     # ── Step 2: Deploy data (only if pack.json has search_indexes or blob_indexes) ──
#     Write-Host "Deploying data for Your Pack content pack..."
#     $packResult = Deploy-ContentPack -PackPath "content_packs/your_pack" -StorageAccountName $storageAccount -AiSearchName $aiSearch -PythonCmd $pythonCmd
#     if (-not $packResult) {
#         Write-Host "Error: Data deployment for Your Pack failed."
#         $isSampleDataFailed = $true
#     } else {
#         Write-Host "Data deployment for Your Pack completed successfully."
#     }
# }

if ($isTeamConfigFailed -or $isSampleDataFailed) {
    Write-Host "`nOne or more tasks failed. Please check the error messages above."
    exit 1
}

# Seed Foundry IQ Knowledge Bases (depends on indexes existing)
# ┌─────────────────────────────────────────────────────────────────────────────┐
# │ NEW CONTENT PACK: Add your menu number to this condition if your pack       │
# │ uses a Knowledge Base (use_knowledge_base=true in agent config).            │
# │ Example: -or $useCaseSelection -eq "7"                                      │
# └─────────────────────────────────────────────────────────────────────────────┘
if ($useCaseSelection -eq "1" -or $useCaseSelection -eq "2" -or $useCaseSelection -eq "5" -or $useCaseSelection -eq "6" -or $useCaseSelection -eq "all") {
    # Set env vars needed by seed scripts (they read from env or src/backend/.env)
    $env:AZURE_AI_SEARCH_ENDPOINT = $(azd env get-value AZURE_AI_SEARCH_ENDPOINT)
    $env:AZURE_OPENAI_ENDPOINT = $(azd env get-value AZURE_OPENAI_ENDPOINT)
    $env:AZURE_AI_PROJECT_ENDPOINT = $(azd env get-value AZURE_AI_PROJECT_ENDPOINT)

    Write-Host "`nSeeding Foundry IQ Knowledge Bases..."
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_knowledge_bases.py" -Wait -NoNewWindow -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Host "Warning: Knowledge base seeding failed. You can run 'python infra/scripts/seed_knowledge_bases.py' manually after deployment."
    } else {
        Write-Host "Knowledge bases seeded successfully."
    }

    # Create RemoteTool MCP connections in Foundry for each KB
    Write-Host "`nCreating KB MCP connections in Foundry..."
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_kb_connections.py" -Wait -NoNewWindow -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Host "Warning: KB MCP connection provisioning failed. You can run 'python infra/scripts/seed_kb_connections.py' manually after deployment."
    } else {
        Write-Host "KB MCP connections created successfully."
    }
}

if($useCaseSelection -eq "1"-or $useCaseSelection -eq "2" -or $useCaseSelection -eq "5" -or $useCaseSelection -eq "6" -or $useCaseSelection -eq "all"){
    Write-Host "`nTeam configuration upload and sample data processing completed successfully."
}else {
    Write-Host "`nTeam configuration upload completed successfully."
}

} finally {
    # Cleanup: Restore network access
    Write-Host ""
    Restore-NetworkAccess
}

#Requires -Version 7.0

param(
    [string]$ResourceGroup
)

# Variables
$directoryPath = ""
$backendUrl = ""
$storageAccount = ""
$blobContainerForRetailCustomer = ""
$blobContainerForRetailOrder = ""
$blobContainerForRFPSummary = ""
$blobContainerForRFPRisk = ""
$blobContainerForRFPCompliance = ""
$blobContainerForContractSummary = ""
$blobContainerForContractRisk = ""
$blobContainerForContractCompliance = ""
$aiSearch = ""
$aiSearchIndexForRetailCustomer = ""
$aiSearchIndexForRetailOrder = ""
$aiSearchIndexForRFPSummary = ""
$aiSearchIndexForRFPRisk = ""
$aiSearchIndexForRFPCompliance = ""
$aiSearchIndexForContractSummary = ""
$aiSearchIndexForContractRisk = ""
$aiSearchIndexForContractCompliance = ""
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
    
    $script:directoryPath = "data/agent_teams"
    $script:backendUrl = $(azd env get-value BACKEND_URL)
    $script:storageAccount = $(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)
    $script:blobContainerForRetailCustomer = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER)
    $script:blobContainerForRetailOrder = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER)
    $script:blobContainerForRFPSummary = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY)
    $script:blobContainerForRFPRisk = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RFP_RISK)
    $script:blobContainerForRFPCompliance = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE)
    $script:blobContainerForContractSummary = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY)
    $script:blobContainerForContractRisk = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK)
    $script:blobContainerForContractCompliance = $(azd env get-value AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE)
    $script:aiSearch = $(azd env get-value AZURE_AI_SEARCH_NAME)
    $script:aiSearchIndexForRetailCustomer = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER)
    $script:aiSearchIndexForRetailOrder = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER)
    $script:aiSearchIndexForRFPSummary = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY)
    $script:aiSearchIndexForRFPRisk = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK)
    $script:aiSearchIndexForRFPCompliance = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE)
    $script:aiSearchIndexForContractSummary = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY)
    $script:aiSearchIndexForContractRisk = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK)
    $script:aiSearchIndexForContractCompliance = $(azd env get-value AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE)
    $script:ResourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP)
    
    # Validate that we got all required values
    if (-not $script:backendUrl -or -not $script:storageAccount -or -not $script:blobContainerForRetailCustomer -or -not $script:aiSearch -or -not $script:aiSearchIndexForRetailOrder -or -not $script:ResourceGroup) {
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
    
    # Extract specific outputs with fallback logic
    $script:storageAccount = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_ACCOUNT_NAME" -FallbackKey "azureStorageAccountName"
    $script:blobContainerForRetailCustomer = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER" -FallbackKey "azureStorageContainerNameRetailCustomer"
    $script:blobContainerForRetailOrder = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_RETAIL_ORDER" -FallbackKey "azureStorageContainerNameRetailOrder"
    $script:blobContainerForRFPSummary = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_RFP_SUMMARY" -FallbackKey "azureStorageContainerNameRfpSummary"
    $script:blobContainerForRFPRisk = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_RFP_RISK" -FallbackKey "azureStorageContainerNameRfpRisk"
    $script:blobContainerForRFPCompliance = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE" -FallbackKey "azureStorageContainerNameRfpCompliance"
    $script:blobContainerForContractSummary = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY" -FallbackKey "azureStorageContainerNameContractSummary"
    $script:blobContainerForContractRisk = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_CONTRACT_RISK" -FallbackKey "azureStorageContainerNameContractRisk"
    $script:blobContainerForContractCompliance = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE" -FallbackKey "azureStorageContainerNameContractCompliance"
    $script:aiSearchIndexForRetailCustomer = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER" -FallbackKey "azureAiSearchIndexNameRetailCustomer"
    $script:aiSearchIndexForRetailOrder = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER" -FallbackKey "azureAiSearchIndexNameRetailOrder"
    $script:aiSearchIndexForRFPSummary = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY" -FallbackKey "azureAiSearchIndexNameRfpSummary"
    $script:aiSearchIndexForRFPRisk = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_RFP_RISK" -FallbackKey "azureAiSearchIndexNameRfpRisk"
    $script:aiSearchIndexForRFPCompliance = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE" -FallbackKey "azureAiSearchIndexNameRfpCompliance"
    $script:aiSearchIndexForContractSummary = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY" -FallbackKey "azureAiSearchIndexNameContractSummary"
    $script:aiSearchIndexForContractRisk = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK" -FallbackKey "azureAiSearchIndexNameContractRisk"
    $script:aiSearchIndexForContractCompliance = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE" -FallbackKey "azureAiSearchIndexNameContractCompliance"
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
    
    # Hardcoded container names (These don't follow the suffix pattern in Bicep, hence need to be changed here if changed in Bicep)
    $script:blobContainerForRetailCustomer = "retail-dataset-customer"
    $script:blobContainerForRetailOrder = "retail-dataset-order"
    $script:blobContainerForRFPSummary = "rfp-summary-dataset"
    $script:blobContainerForRFPRisk = "rfp-risk-dataset"
    $script:blobContainerForRFPCompliance = "rfp-compliance-dataset"
    $script:blobContainerForContractSummary = "contract-summary-dataset"
    $script:blobContainerForContractRisk = "contract-risk-dataset"
    $script:blobContainerForContractCompliance = "contract-compliance-dataset"
    
    # Hardcoded index names (These don't follow the suffix pattern in Bicep, hence need to be changed here if changed in Bicep)
    $script:aiSearchIndexForRetailCustomer = "macae-retail-customer-index"
    $script:aiSearchIndexForRetailOrder = "macae-retail-order-index"
    $script:aiSearchIndexForRFPSummary = "macae-rfp-summary-index"
    $script:aiSearchIndexForRFPRisk = "macae-rfp-risk-index"
    $script:aiSearchIndexForRFPCompliance = "macae-rfp-compliance-index"
    $script:aiSearchIndexForContractSummary = "contract-summary-doc-index"
    $script:aiSearchIndexForContractRisk = "contract-risk-doc-index"
    $script:aiSearchIndexForContractCompliance = "contract-compliance-doc-index"
    
    $script:directoryPath = "data/agent_teams"
    
    # Validate that we got all critical values
    if (-not $script:storageAccount -or -not $script:aiSearch -or -not $script:backendUrl) {
        Write-Host "Error: Failed to reconstruct all required resource names."
        return $false
    }
    
    Write-Host "Successfully reconstructed values from resource naming convention."
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
Write-Host "6. All"
Write-Host "==============================================="
Write-Host ""

# Prompt user for use case selection
do {
    $useCaseSelection = Read-Host "Please enter the number of the use case you would like to install."
    
    # Handle both numeric and text input for 'all'
    if ($useCaseSelection -eq "all" -or $useCaseSelection -eq "6") {
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
    else {
        $useCaseValid = $false
        Write-Host "Invalid selection. Please enter a number from 1-6." -ForegroundColor Red
    }
} while (-not $useCaseValid)

Write-Host ""
Write-Host "==============================================="
Write-Host "Values to be used:"
Write-Host "==============================================="
Write-Host "Selected Use Case: $selectedUseCase"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Backend URL: $backendUrl"
Write-Host "Storage Account: $storageAccount"
Write-Host "AI Search: $aiSearch"
Write-Host "Directory Path: $directoryPath"
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
if($useCaseSelection -eq "3" -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6") {
    Write-Host "Uploading Team Configuration for HR Employee Onboarding..."
    $directoryPath = "data/agent_teams"
    $teamId = "00000000-0000-0000-0000-000000000001"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $directoryPath, $userPrincipalId, $teamId -Wait -NoNewWindow -PassThru
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
if($useCaseSelection -eq "4" -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6") {
    Write-Host "Uploading Team Configuration for Marketing Press Release..."
    $directoryPath = "data/agent_teams"
    $teamId = "00000000-0000-0000-0000-000000000002"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $directoryPath, $userPrincipalId, $teamId -Wait -NoNewWindow -PassThru
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
if($useCaseSelection -eq "1"-or $useCaseSelection -eq "2" -or $useCaseSelection -eq "5"  -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6"){
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



if($useCaseSelection -eq "1" -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6") {
    Write-Host "Uploading Team Configuration for RFP Evaluation..."
    $directoryPath = "data/agent_teams"
    $teamId = "00000000-0000-0000-0000-000000000004"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $directoryPath, $userPrincipalId, $teamId -Wait -NoNewWindow -PassThru
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

    $directoryPath = "data/datasets/rfp/summary"
    # Upload sample files to blob storage
    Write-Host "Uploading sample files to blob storage for RFP Evaluation..."
    $result = az storage blob upload-batch --account-name $storageAccount --destination $blobContainerForRFPSummary --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }

    $directoryPath = "data/datasets/rfp/risk"
    $result = az storage blob upload-batch --account-name $storageAccount --destination $blobContainerForRFPRisk --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }

    $directoryPath = "data/datasets/rfp/compliance"
    # Upload sample files to blob storage
    $result = az storage blob upload-batch --account-name $storageAccount --destination $blobContainerForRFPCompliance --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }
    Write-Host "Files uploaded successfully to blob storage."

    # Run the Python script to index data
    Write-Host "Running the python script to index data for RFP Evaluation"
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, $blobContainerForRFPSummary , $aiSearch, $aiSearchIndexForRFPSummary -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
    }

    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, $blobContainerForRFPRisk , $aiSearch, $aiSearchIndexForRFPRisk -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
    }

    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, $blobContainerForRFPCompliance , $aiSearch, $aiSearchIndexForRFPCompliance -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
    }
    Write-Host "Python script to index data for RFP Evaluation successfully executed."
}


if($useCaseSelection -eq "5" -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6") {
    Write-Host "Uploading Team Configuration for Contract Compliance Review..."
    $directoryPath = "data/agent_teams"
    $teamId = "00000000-0000-0000-0000-000000000005"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $directoryPath, $userPrincipalId, $teamId -Wait -NoNewWindow -PassThru
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

    $directoryPath = "data/datasets/contract_compliance/summary"
    # Upload sample files to blob storage
    Write-Host "Uploading sample files to blob storage for Contract Compliance Review..."
    $result = az storage blob upload-batch --account-name $storageAccount --destination $blobContainerForContractSummary --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }

    $directoryPath = "data/datasets/contract_compliance/risk"
    $result = az storage blob upload-batch --account-name $storageAccount --destination $blobContainerForContractRisk --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }

    $directoryPath = "data/datasets/contract_compliance/compliance"

    $result = az storage blob upload-batch --account-name $storageAccount --destination $blobContainerForContractCompliance --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }
    Write-Host "Files uploaded successfully to blob storage."

    # Run the Python script to index data
    Write-Host "Running the python script to index data for Contract Compliance Review"
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, $blobContainerForContractSummary , $aiSearch, $aiSearchIndexForContractSummary -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
    }

    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, $blobContainerForContractRisk , $aiSearch, $aiSearchIndexForContractRisk -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
    }

    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, $blobContainerForContractCompliance , $aiSearch, $aiSearchIndexForContractCompliance -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
    }
    Write-Host "Python script to index data for Contract Compliance Review successfully executed."
}

if($useCaseSelection -eq "2" -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6") {
    Write-Host "Uploading Team Configuration for Retail Customer Satisfaction..."
    $directoryPath = "data/agent_teams"
    $teamId = "00000000-0000-0000-0000-000000000003"
    try {
        $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $directoryPath, $userPrincipalId, $teamId -Wait -NoNewWindow -PassThru
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

    $directoryPath = "data/datasets/retail/customer"
    # Upload sample files to blob storage
    Write-Host "Uploading sample files to blob storage for Retail Customer Satisfaction ..."
    $result = az storage blob upload-batch --account-name $storageAccount --destination "retail-dataset-customer" --source $directoryPath --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }

    $directoryPath = "data/datasets/retail/order"
    $result = az storage blob upload-batch --account-name $storageAccount --destination "retail-dataset-order" --source "data/datasets/retail/order" --auth-mode login --pattern "*" --overwrite --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to upload files to blob storage."
        $isSampleDataFailed = $true
        exit 1
    }
    Write-Host "Files uploaded successfully to blob storage."

    # Run the Python script to index data
    Write-Host "Running the python script to index data for Retail Customer Satisfaction"
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, "retail-dataset-customer", $aiSearch, "macae-retail-customer-index" -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
        exit 1
    }
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/index_datasets.py", $storageAccount, "retail-dataset-order" , $aiSearch, "macae-retail-order-index" -Wait -NoNewWindow -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Host "Error: Indexing python script execution failed."
        $isSampleDataFailed = $true
        exit 1
    }
    Write-Host "Python script to index data for Retail Customer Satisfaction successfully executed."
}

if ($isTeamConfigFailed -or $isSampleDataFailed) {
    Write-Host "`nOne or more tasks failed. Please check the error messages above."
    exit 1
} else {
    if($useCaseSelection -eq "1"-or $useCaseSelection -eq "2" -or $useCaseSelection -eq "5" -or $useCaseSelection -eq "all" -or $useCaseSelection -eq "6"){
        Write-Host "`nTeam configuration upload and sample data processing completed successfully."
    }else {
        Write-Host "`nTeam configuration upload completed successfully."
    }
    
}

} finally {
    # Cleanup: Restore network access
    Write-Host ""
    Restore-NetworkAccess
}

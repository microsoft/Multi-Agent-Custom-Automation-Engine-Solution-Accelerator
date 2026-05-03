# =============================================================================
# Azure OpenAI Quota Check (PowerShell)
# =============================================================================
# PowerShell sibling of infra/scripts/quota_check_params.sh.
# Behavior, defaults, and tabular output mirror the bash version so it can be
# used interchangeably from Windows PowerShell / pwsh on any OS.
#
# Defaults (when no parameters provided):
#   Models  : gpt-4.1:150, o4-mini:50, gpt-4.1-mini:50
#   Regions : australiaeast, eastus2, francecentral, japaneast,
#             norwayeast, swedencentral, uksouth, westus
#
# Usage examples:
#   .\quota_check_params.ps1
#   .\quota_check_params.ps1 -Models 'gpt-4.1:150'
#   .\quota_check_params.ps1 -Regions 'eastus2,westus'
#   .\quota_check_params.ps1 -Models 'gpt-4.1:150,o4-mini:50' -Regions 'eastus2,westus' -Verbose
# =============================================================================

[CmdletBinding()]
param(
    [string]$Models = "",
    [string]$Regions = ""
)

$ErrorActionPreference = "Continue"

function Write-Verb {
    param([string]$Message)
    if ($PSCmdlet.MyInvocation.BoundParameters.ContainsKey('Verbose') -or $VerbosePreference -ne 'SilentlyContinue') {
        Write-Host $Message
    }
}

# Default Models and Capacities
# NOTE: Azure publishes these SKUs without a hyphen between 'gpt' and the
# version (e.g. OpenAI.GlobalStandard.gpt4.1, OpenAI.GlobalStandard.gpt4.1-mini),
# so the model identifiers below must match that naming exactly.
$DefaultModelCapacity = "gpt4.1:150,o4-mini:50,gpt4.1-mini:50"

# Default Regions to check
$DefaultRegions = @("australiaeast", "eastus2", "francecentral", "japaneast", "norwayeast", "swedencentral", "uksouth", "westus")

Write-Host "Models: $Models"
Write-Host "Regions: $Regions"

# Resolve subscription (allow caller to pre-set AZURE_SUBSCRIPTION_ID)
Write-Host "🔄 Fetching available Azure subscriptions..."

$SubscriptionId = $env:AZURE_SUBSCRIPTION_ID
if ($SubscriptionId) {
    Write-Host "✅ Using pre-set AZURE_SUBSCRIPTION_ID: $SubscriptionId"
}
else {
    $subList = az account list --query "[?state=='Enabled'].{Name:name, ID:id}" --output json 2>$null | ConvertFrom-Json
    if (-not $subList -or $subList.Count -eq 0) {
        Write-Host "❌ ERROR: No active Azure subscriptions found. Please log in using 'az login'."
        exit 1
    }
    if ($subList.Count -eq 1) {
        $SubscriptionId = $subList[0].ID
        Write-Host "✅ Using the only available subscription: $SubscriptionId"
    }
    else {
        # Default to the active subscription (no prompts)
        $active = az account show --query id -o tsv 2>$null
        if ($active) {
            $SubscriptionId = $active.Trim()
            Write-Host "✅ Using active subscription: $SubscriptionId"
        }
        else {
            $SubscriptionId = $subList[0].ID
            Write-Host "✅ Using first enabled subscription: $SubscriptionId"
        }
    }
}

az account set --subscription $SubscriptionId 2>$null | Out-Null
$activeName = az account show --query name -o tsv 2>$null
Write-Host "🎯 Active Subscription: $activeName ($SubscriptionId)"

# Parse model:capacity pairs
$modelCapacityPairs = @()
if ($Models) {
    $modelCapacityPairs = $Models.Split(",")
    Write-Host "Using provided model and capacity pairs: $($modelCapacityPairs -join ', ')"
}
else {
    $modelCapacityPairs = $DefaultModelCapacity.Split(",")
    Write-Host "No parameters provided, using default model-capacity pairs: $($modelCapacityPairs -join ', ')"
}

$finalModelNames = @()
$finalCapacities = @()
foreach ($pair in $modelCapacityPairs) {
    $parts = $pair.Split(":")
    if ($parts.Count -ne 2 -or -not $parts[0] -or -not $parts[1]) {
        Write-Host "❌ ERROR: Invalid model and capacity pair '$pair'. Expected 'model:capacity'."
        exit 1
    }
    $finalModelNames += $parts[0].Trim().ToLower()
    $finalCapacities += [int]$parts[1].Trim()
}

Write-Host "🔄 Using Models: $($finalModelNames -join ', ') with respective Capacities: $($finalCapacities -join ', ')"
Write-Host "----------------------------------------"

# Resolve regions
if ($Regions) {
    Write-Host "🔍 User provided region: $Regions"
    $regionList = $Regions.Split(",") | ForEach-Object { $_.Trim() }
    $applyOrCondition = $false
}
else {
    Write-Host "No region specified, using default regions: $($DefaultRegions -join ', ')"
    $regionList = $DefaultRegions
    $applyOrCondition = $true
}

Write-Host "✅ Retrieved Azure regions. Checking availability..."

$validRegions = @()
$tableRows = New-Object System.Collections.Generic.List[string]
$index = 1

foreach ($region in $regionList) {
    Write-Verb "----------------------------------------"
    Write-Verb "🔍 Checking region: $region"

    $quotaInfo = az cognitiveservices usage list --location $region --output json 2>$null | ConvertFrom-Json
    if (-not $quotaInfo) {
        Write-Verb "⚠️ WARNING: Failed to retrieve quota for region $region. Skipping."
        continue
    }

    $atLeastOneModelAvailable = $false
    $tempRows = New-Object System.Collections.Generic.List[string]

    for ($i = 0; $i -lt $finalModelNames.Count; $i++) {
        $modelName = $finalModelNames[$i]
        $requiredCapacity = $finalCapacities[$i]
        $modelTypes = @("OpenAI.Standard.$modelName", "OpenAI.GlobalStandard.$modelName")

        foreach ($modelType in $modelTypes) {
            Write-Verb "🔍 Checking model: $modelName with required capacity: $requiredCapacity ($modelType)"

            $entry = $quotaInfo | Where-Object { $_.name.value -ieq $modelType } | Select-Object -First 1
            if (-not $entry) {
                Write-Verb "⚠️ WARNING: No quota information found for $modelName in $region for $modelType."
                continue
            }

            $currentValue = [int]([math]::Floor([double]($entry.currentValue)))
            $limit = [int]([math]::Floor([double]($entry.limit)))
            $available = $limit - $currentValue
            Write-Verb "✅ Model: $modelType | Used: $currentValue | Limit: $limit | Available: $available"

            if ($available -ge $requiredCapacity) {
                $atLeastOneModelAvailable = $true
                $row = ("| {0,-4} | {1,-20} | {2,-43} | {3,-10} | {4,-10} | {5,-10} |" -f $index, $region, $modelType, $limit, $currentValue, $available)
                $tempRows.Add($row)
            }
            else {
                Write-Verb "⚠️ Model $modelName in $region has insufficient quota ($modelType): $available available, $requiredCapacity required."
            }
        }
    }

    if ((-not $applyOrCondition) -or $atLeastOneModelAvailable) {
        if ($tempRows.Count -gt 0) {
            $validRegions += $region
            foreach ($row in $tempRows) { [void]$tableRows.Add($row) }
            $index++
        }
        elseif (-not $Models) {
            Write-Host "🚫 Skipping $region as it does not meet quota requirements."
        }
    }
    elseif (-not $Models) {
        Write-Host "🚫 Skipping $region as it does not meet quota requirements."
    }
}

if ($tableRows.Count -eq 0) {
    Write-Host "--------------------------------------------------------------------------------------------------------------------"
    Write-Host "❌ No regions have sufficient quota for all required models. Please request a quota increase: https://aka.ms/oai/stuquotarequest"
}
else {
    Write-Host "---------------------------------------------------------------------------------------------------------------------"
    Write-Host ("| {0,-4} | {1,-20} | {2,-43} | {3,-10} | {4,-10} | {5,-10} |" -f "No.", "Region", "Model Name", "Limit", "Used", "Available")
    Write-Host "---------------------------------------------------------------------------------------------------------------------"
    foreach ($row in $tableRows) { Write-Host $row }
    Write-Host "---------------------------------------------------------------------------------------------------------------------"
    Write-Host "➡️  To request a quota increase, visit: https://aka.ms/oai/stuquotarequest"
}

Write-Host "✅ Script completed."

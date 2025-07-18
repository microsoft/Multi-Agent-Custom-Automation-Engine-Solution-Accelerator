param (
    [string]$Location,
    [string]$Model,
    [string]$DeploymentType = "GlobalStandard",
    [int]$Capacity
)

# Verify required parameters
$MissingParams = @()
if (-not $Location) { $MissingParams += "location" }
if (-not $Model) { $MissingParams += "model" }
if (-not $Capacity) { $MissingParams += "capacity" }
if (-not $DeploymentType) { $MissingParams += "deployment-type" }

if ($MissingParams.Count -gt 0) {
    Write-Error "❌ ERROR: Missing required parameters: $($MissingParams -join ', ')"
    Write-Host "Usage: .\validate_model_quota.ps1 -Location <LOCATION> -Model <MODEL> -Capacity <CAPACITY> [-DeploymentType <DEPLOYMENT_TYPE>]"
    exit 1
}

if ($DeploymentType -ne "Standard" -and $DeploymentType -ne "GlobalStandard") {
    Write-Error "❌ ERROR: Invalid deployment type: $DeploymentType. Allowed values are 'Standard' or 'GlobalStandard'."
    exit 1
}

$ModelType = "OpenAI.$DeploymentType.$Model"

$PreferredRegions = @('australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus')
$AllResults = @()

function Check-Quota {
    param (
        [string]$Region
    )

    $ModelInfoRaw = az cognitiveservices usage list --location $Region --query "[?name.value=='$ModelType']" --output json
    $ModelInfo = $null

    try {
        $ModelInfo = $ModelInfoRaw | ConvertFrom-Json
    } catch {
        return
    }

    if (-not $ModelInfo) {
        return
    }

    $CurrentValue = ($ModelInfo | Where-Object { $_.name.value -eq $ModelType }).currentValue
    $Limit = ($ModelInfo | Where-Object { $_.name.value -eq $ModelType }).limit

    $CurrentValue = [int]($CurrentValue -replace '\.0+$', '')
    $Limit = [int]($Limit -replace '\.0+$', '')
    $Available = $Limit - $CurrentValue

    $script:AllResults += [PSCustomObject]@{
        Region    = $Region
        Model     = $ModelType
        Limit     = $Limit
        Used      = $CurrentValue
        Available = $Available
    }
}

foreach ($region in $PreferredRegions) {
    Check-Quota -Region $region
}

# Display Results Table
Write-Host "\n-------------------------------------------------------------------------------------------------------------"
Write-Host "| No.  | Region            | Model Name                           | Limit   | Used    | Available |"
Write-Host "-------------------------------------------------------------------------------------------------------------"

$count = 1
foreach ($entry in $AllResults) {
    $index = $PreferredRegions.IndexOf($entry.Region) + 1
    $modelShort = $entry.Model.Substring($entry.Model.LastIndexOf(".") + 1)
    Write-Host ("| {0,-4} | {1,-16} | {2,-35} | {3,-7} | {4,-7} | {5,-9} |" -f $index, $entry.Region, $entry.Model, $entry.Limit, $entry.Used, $entry.Available)
    $count++
}
Write-Host "-------------------------------------------------------------------------------------------------------------"

$EligibleRegion = $AllResults | Where-Object { $_.Region -eq $Location -and $_.Available -ge $Capacity }
if ($EligibleRegion) {
    Write-Host "\n✅ Sufficient quota found in original region '$Location'."
    exit 0
}

$FallbackRegions = $AllResults | Where-Object { $_.Region -ne $Location -and $_.Available -ge $Capacity }

if ($FallbackRegions.Count -gt 0) {
    Write-Host "`n❌ Deployment cannot proceed because the original region '$Location' lacks sufficient quota."
    Write-Host "➡️ You can retry using one of the following regions with sufficient quota:`n"

    foreach ($region in $FallbackRegions) {
        Write-Host "   • $($region.Region) (Available: $($region.Available))"
    }

    Write-Host "`n🔧 To proceed, run:"
    Write-Host "    azd env set AZURE_ENV_OPENAI_LOCATION '<region>'"
    Write-Host "📌 To confirm it's set correctly, run:"
    Write-Host "    azd env get-value AZURE_ENV_OPENAI_LOCATION"
    Write-Host "▶️  Once confirmed, re-run azd up to deploy the model in the new region."
    exit 2
}

Write-Error "❌ ERROR: No available quota found in any region."
exit 1

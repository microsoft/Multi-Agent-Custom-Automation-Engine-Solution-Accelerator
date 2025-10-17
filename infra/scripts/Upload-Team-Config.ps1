#Requires -Version 7.0

param(
    [string]$backendUrl,
    [string]$DirectoryPath,
    [string]$AzSubscriptionId
)

# Get parameters from azd env, if not provided
if (-not $backendUrl) {
    $backendUrl = $(azd env get-value BACKEND_URL)
}
if (-not $DirectoryPath) {
    $DirectoryPath = "data/agent_teams"
}

if (-not $AzSubscriptionId) {
    $AzSubscriptionId = $(azd env get-value AZURE_SUBSCRIPTION_ID)
}

# Check if all required arguments are provided
if (-not $backendUrl -or -not $DirectoryPath) {
    Write-Host "Usage: .\infra\scripts\Upload-Team-Config.ps1 -backendUrl <backendUrl> -DirectoryPath <DirectoryPath>"
    exit 1
}

# Authenticate with Azure
try {
    $currentAzContext = az account show | ConvertFrom-Json -ErrorAction Stop
    Write-Host "Already authenticated with Azure."
} catch {
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
                $selectedSubscriptionName = $selectedSubscription.Name
                $selectedSubscriptionId = $selectedSubscription.Id
                $result = az account set --subscription $selectedSubscriptionId
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Switched to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )"
                    break
                } else {
                    Write-Host "Failed to switch to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )."
                }
            } else {
                Write-Host "Invalid selection. Please try again."
            }
        } while ($true)
    } else {
        Write-Host "Proceeding with the current subscription: $currentSubscriptionName ( $currentSubscriptionId )"
        az account set --subscription $currentSubscriptionId
    }
} else {
    Write-Host "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    az account set --subscription $currentSubscriptionId
}

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

# Run the Python script to upload team configuration
Write-Host "Running the python script to upload team configuration"
$process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/upload_team_config.py", $backendUrl, $DirectoryPath, $userPrincipalId -Wait -NoNewWindow -PassThru
if ($process.ExitCode -ne 0) {
    Write-Host "Error: Team configuration upload failed."
    exit 1
}

Write-Host "Script executed successfully. Team configuration uploaded."

#!/bin/bash

# Variables
backendUrl=$1
directoryPath=$2
azSubscriptionId=$3

# get parameters from azd env, if not provided as arguments
if [ -z "$directoryPath" ]; then
    directoryPath="data/agent_teams"
fi

if [ -z "$backendUrl" ]; then
    backendUrl=$(azd env get-value BACKEND_URL)
fi

if [ -z "$azSubscriptionId" ]; then
    azSubscriptionId=$(azd env get-value AZURE_SUBSCRIPTION_ID)
fi

if [ -z "$backendUrl" ] || [ -z "$directoryPath" ]; then
    echo "Error: Missing required arguments."
    echo "Usage: $0 <backendUrl> <directoryPath>"
    exit 1
fi

# Authenticate with Azure
if az account show &> /dev/null; then
    echo "Already authenticated with Azure."
else
    echo "Not authenticated with Azure. Attempting to authenticate..."
    echo "Authenticating with Azure CLI..."
    az login
fi

#check if user has selected the correct subscription
currentSubscriptionId=$(az account show --query id -o tsv)
currentSubscriptionName=$(az account show --query name -o tsv)
if [ "$currentSubscriptionId" != "$azSubscriptionId" ]; then
    echo "Current selected subscription is $currentSubscriptionName ( $currentSubscriptionId )."
    read -rp "Do you want to continue with this subscription?(y/n): " confirmation
    if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
        echo "Fetching available subscriptions..."
        availableSubscriptions=$(az account list --query "[?state=='Enabled'].[name,id]" --output tsv)
        while true; do
            echo ""
            echo "Available Subscriptions:"
            echo "========================"
            echo "$availableSubscriptions" | awk '{printf "%d. %s ( %s )\n", NR, $1, $2}'
            echo "========================"
            echo ""
            read -rp "Enter the number of the subscription (1-$(echo "$availableSubscriptions" | wc -l)) to use: " subscriptionIndex
            if [[ "$subscriptionIndex" =~ ^[0-9]+$ ]] && [ "$subscriptionIndex" -ge 1 ] && [ "$subscriptionIndex" -le $(echo "$availableSubscriptions" | wc -l) ]; then
                selectedSubscription=$(echo "$availableSubscriptions" | sed -n "${subscriptionIndex}p")
                selectedSubscriptionName=$(echo "$selectedSubscription" | cut -f1)
                selectedSubscriptionId=$(echo "$selectedSubscription" | cut -f2)

                # Set the selected subscription
                if  az account set --subscription "$selectedSubscriptionId"; then
                    echo "Switched to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )"
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
    fi
else
    echo "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    az account set --subscription "$currentSubscriptionId"
fi

userPrincipalId=$(az ad signed-in-user show --query id -o tsv)

# Determine the correct Python command
if command -v python && python --version &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 && python3 --version &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Python is not installed on this system. Or it is not added in the PATH."
    exit 1
fi

# create virtual environment
if [ -d "infra/scripts/scriptenv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    echo "Creating virtual environment"
    $PYTHON_CMD -m venv infra/scripts/scriptenv
fi

# Activate the virtual environment
if [ -f "infra/scripts/scriptenv/bin/activate" ]; then
    echo "Activating virtual environment (Linux/macOS)"
    source "infra/scripts/scriptenv/bin/activate"
elif [ -f "infra/scripts/scriptenv/Scripts/activate" ]; then
    echo "Activating virtual environment (Windows)"
    source "infra/scripts/scriptenv/Scripts/activate"
else
    echo "Error activating virtual environment. Requirements may be installed globally."
fi

# Install the requirements
echo "Installing requirements"
pip install --quiet -r infra/scripts/requirements.txt
echo "Requirements installed"

echo "Running the python script to upload team configuration"
$PYTHON_CMD infra/scripts/upload_team_config.py "$backendUrl" "$directoryPath" "$userPrincipalId"
if [ $? -ne 0 ]; then
    echo "Error: Team configuration upload failed."
    exit 1
fi

echo "Script executed successfully. Team configuration uploaded."
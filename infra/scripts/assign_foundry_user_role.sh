#!/bin/bash

# Variables
resource_group="$1"
aif_resource_id="$2"
principal_ids="$3"
managedIdentityClientId="$4"


# Authenticate with Azure
if az account show &> /dev/null; then
    echo "Already authenticated with Azure."
else
    if [ -n "$managedIdentityClientId" ]; then
        # Use managed identity if running in Azure
        echo "Authenticating with Managed Identity..."
        az login --identity --client-id ${managedIdentityClientId}
    else
        # Use Azure CLI login if running locally
        echo "Authenticating with Azure CLI..."
        az login
    fi
    echo "Not authenticated with Azure. Attempting to authenticate..."
fi


IFS=',' read -r -a principal_ids_array <<< $principal_ids

echo "Assigning Foundry User role to users"

echo "Using provided Foundry resource id: $aif_resource_id"

for principal_id in "${principal_ids_array[@]}"; do

    # Check if the user has the Foundry User role
    echo "Checking if user - ${principal_id} has the Foundry User role"
    role_assignment=$(MSYS_NO_PATHCONV=1 az role assignment list --role 53ca6127-db72-4b80-b1b0-d745d6d5456d --scope $aif_resource_id --assignee $principal_id --query "[].roleDefinitionId" -o tsv)
    if [ -z "$role_assignment" ]; then
        echo "User - ${principal_id} does not have the Foundry User role. Assigning the role."
        MSYS_NO_PATHCONV=1 az role assignment create --assignee $principal_id --role 53ca6127-db72-4b80-b1b0-d745d6d5456d --scope $aif_resource_id --output none
        if [ $? -eq 0 ]; then
            echo "Foundry User role assigned successfully."
        else
            echo "Failed to assign Foundry User role."
            exit 1
        fi
    else
        echo "User - ${principal_id} already has the Foundry User role."
    fi
done
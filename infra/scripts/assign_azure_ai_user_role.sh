#!/bin/bash

# Variables
resource_group="$1"
aif_resource_id="$2"
principal_ids="$3"


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

echo "Assigning Azure AI User role role to users"

echo "Using provided Azure AI resource id: $aif_resource_id"

for principal_id in "${principal_ids_array[@]}"; do

    # Check if the user has the Azure AI User role
    echo "Checking if user - ${principal_id} has the Azure AI User role"
    role_assignment=$(MSYS_NO_PATHCONV=1 az role assignment list --role 53ca6127-db72-4b80-b1b0-d745d6d5456d --scope $aif_resource_id --assignee $principal_id --query "[].roleDefinitionId" -o tsv)
    if [ -z "$role_assignment" ]; then
        echo "User - ${principal_id} does not have the Azure AI User role. Assigning the role."
        MSYS_NO_PATHCONV=1 az role assignment create --assignee $principal_id --role 53ca6127-db72-4b80-b1b0-d745d6d5456d --scope $aif_resource_id --output none
        if [ $? -eq 0 ]; then
            echo "Azure AI User role assigned successfully."
        else
            echo "Failed to assign Azure AI User role."
            exit 1
        fi
    else
        echo "User - ${principal_id} already has the Azure AI User role."
    fi
done
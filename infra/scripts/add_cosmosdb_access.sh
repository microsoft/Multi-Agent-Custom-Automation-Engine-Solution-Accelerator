#!/bin/bash

# Variables
resource_group="$1"
account_name="$2"
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

echo "Assigning Cosmos DB Built-in Data Contributor role to users"
for principal_id in "${principal_ids_array[@]}"; do

    # Check if the user has the Cosmos DB Built-in Data Contributor role
    echo "Checking if user - ${principal_id} has the Cosmos DB Built-in Data Contributor role"
    roleExists=$(az cosmosdb sql role assignment list \
        --resource-group $resource_group \
        --account-name $account_name \
        --query "[?roleDefinitionId.ends_with(@, '00000000-0000-0000-0000-000000000002') && principalId == '$principal_id']" -o tsv)

    # Check if the role exists
    if [ -n "$roleExists" ]; then
        echo "User - ${principal_id} already has the Cosmos DB Built-in Data Contributer role."
    else
        echo "User - ${principal_id} does not have the Cosmos DB Built-in Data Contributer role. Assigning the role."
        MSYS_NO_PATHCONV=1 az cosmosdb sql role assignment create \
            --resource-group $resource_group \
            --account-name $account_name \
            --role-definition-id 00000000-0000-0000-0000-000000000002 \
            --principal-id $principal_id \
            --scope "/" \
            --output none
        if [ $? -eq 0 ]; then
            echo "Cosmos DB Built-in Data Contributer role assigned successfully."
        else
            echo "Failed to assign Cosmos DB Built-in Data Contributer role."
        fi
    fi
done
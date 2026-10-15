#!/bin/bash

# Script para asignar permisos necesarios a la identidad

: "${OBJECT_ID:?Set OBJECT_ID to the target service principal object ID}"
: "${AZURE_AI_SUBSCRIPTION_ID:?Set AZURE_AI_SUBSCRIPTION_ID}"
: "${AZURE_AI_RESOURCE_GROUP:?Set AZURE_AI_RESOURCE_GROUP}"
: "${AZURE_AI_PROJECT_NAME:?Set AZURE_AI_PROJECT_NAME}"
: "${AZURE_KEY_VAULT_NAME:?Set AZURE_KEY_VAULT_NAME}"
SUBSCRIPTION_ID="$AZURE_AI_SUBSCRIPTION_ID"
RESOURCE_GROUP="$AZURE_AI_RESOURCE_GROUP"
WORKSPACE_NAME="$AZURE_AI_PROJECT_NAME"
KEY_VAULT_NAME="$AZURE_KEY_VAULT_NAME"

echo "Asignando rol 'AzureML Data Scientist' a la identidad..."

az role assignment create \
  --assignee-object-id "$OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "AzureML Data Scientist" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.MachineLearningServices/workspaces/$WORKSPACE_NAME"

echo "Asignando rol 'Key Vault Secrets Officer' a la identidad..."

az role assignment create \
  --assignee-object-id "$OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets Officer" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME"

echo "Permisos asignados correctamente"

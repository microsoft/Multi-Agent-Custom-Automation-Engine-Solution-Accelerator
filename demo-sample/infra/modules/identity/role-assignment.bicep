@description('Object ID of the App Service managed identity.')
param appServicePrincipalId string

@description('Name of the Azure Container Registry.')
param containerRegistryName string

var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: containerRegistryName
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, appServicePrincipalId, acrPullRoleDefinitionId)
  scope: containerRegistry
  properties: {
    principalId: appServicePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
  }
}

@description('Resource ID of the role assignment.')
output resourceId string = acrPullRoleAssignment.id

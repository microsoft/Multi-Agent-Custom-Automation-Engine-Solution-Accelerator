@description('Name of the App Service.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Resource ID of the App Service Plan.')
param serverFarmResourceId string

@description('Docker image name (e.g., DOCKER|registry.azurecr.io/image:tag).')
param linuxFxVersion string

resource appService 'Microsoft.Web/sites@2025-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: serverFarmResourceId
    publicNetworkAccess: 'Enabled'
    siteConfig: {
      alwaysOn: true
      linuxFxVersion: linuxFxVersion
      acrUseManagedIdentityCreds: true
    }
  }
}

@description('Name of the App Service.')
output name string = appService.name

@description('URL of the App Service.')
output appUrl string = 'https://${appService.properties.defaultHostName}'

@description('System-assigned identity principal ID.')
output identityPrincipalId string = appService.identity.principalId

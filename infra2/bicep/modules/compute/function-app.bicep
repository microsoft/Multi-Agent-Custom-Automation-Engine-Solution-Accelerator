targetScope = 'resourceGroup'

@description('The name of the Function App.')
param name string

@description('The Azure region where the Function App will be deployed.')
param solutionLocation string

@description('Tags to apply to the resource.')
param tags object = {}

@description('The resource ID of the App Service plan hosting the Function App.')
param serverFarmId string

@description('The name of the storage account used by the Function App.')
param storageAccountName string

@description('The resource ID of the storage account (used to derive access key).')
param storageAccountId string

@description('Additional application settings to apply to the Function App.')
param appSettings array = []

@description('The worker runtime stack for the Function App.')
param runtimeStack string = 'python'

@description('The runtime version for the worker stack.')
param runtimeVersion string = '3.11'

@description('The managed identity type assigned to the Function App.')
param identityType string = 'SystemAssigned'

@description('The user-assigned identities to associate with the Function App when applicable.')
param userAssignedIdentities object = {}

var functionAppIdentity = identityType == 'None' ? null : {
  type: identityType
  userAssignedIdentities: contains(identityType, 'UserAssigned') ? userAssignedIdentities : null
}

var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${listKeys(storageAccountId, '2023-05-01').keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
var linuxFxVersion = '${toUpper(runtimeStack)}|${runtimeVersion}'
var functionAppSettings = concat([
  {
    name: 'AzureWebJobsStorage'
    value: storageConnectionString
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: toLower(runtimeStack)
  }
  {
    name: 'WEBSITE_RUN_FROM_PACKAGE'
    value: '1'
  }
], appSettings)

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: name
  location: solutionLocation
  tags: tags
  kind: 'functionapp,linux'
  identity: functionAppIdentity
  properties: {
    serverFarmId: serverFarmId
    siteConfig: {
      linuxFxVersion: linuxFxVersion
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: functionAppSettings
    }
    httpsOnly: true
  }
}

@description('The name of the Function App.')
output name string = functionApp.name

@description('The resource ID of the Function App.')
output id string = functionApp.id

@description('The default host name of the Function App.')
output defaultHostName string = functionApp.properties.defaultHostName

@description('The principal ID of the system-assigned managed identity, if enabled.')
output principalId string = contains(identityType, 'SystemAssigned') ? functionApp.identity.principalId : ''

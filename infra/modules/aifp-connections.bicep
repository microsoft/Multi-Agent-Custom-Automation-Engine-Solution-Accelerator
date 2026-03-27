@description('Name of the AI Foundry search connection')
param aifSearchConnectionName string

@description('Name of the Azure AI Search service')
param searchServiceName string

@description('Resource ID of the Azure AI Search service')
param searchServiceResourceId string

@description('Location/region of the Azure AI Search service')
param searchServiceLocation string

@description('Name of the AI Foundry account')
param aiFoundryName string

@description('Name of the AI Foundry project')
param aiFoundryProjectName string

@description('Optional. Name of the AI Foundry storage connection')
param aifStorageConnectionName string = ''

@description('Optional. Resource ID of the Azure Storage account')
param storageAccountResourceId string = ''

@description('Optional. Location/region of the Azure Storage account')
param storageAccountLocation string = ''

@description('Optional. Blob storage endpoint of the Azure Storage account')
param blobstorageEndpoint string = ''

@description('Optional. Name of the AI Foundry Cosmos DB connection')
param aifCosmosConnectionName string = ''

@description('Optional. Resource ID of the Azure Cosmos DB account')
param cosmosAccountResourceId string = ''

@description('Optional. Location/region of the Azure Cosmos DB account')
param cosmosAccountLocation string = ''

@description('Optional. Endpoint of the Azure Cosmos DB account')
param cosmosDbEndpoint string = ''

@description('Optional. Enable private networking for applicable resources.')
param enablePrivateNetworking bool = false

resource aiSearchFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${aifSearchConnectionName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net'
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceResourceId
      location: searchServiceLocation
    }
  }
}

resource storageFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (enablePrivateNetworking) {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${aifStorageConnectionName}'
  properties: {
    category: 'AzureStorageAccount'
    target: blobstorageEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: storageAccountResourceId
      location: storageAccountLocation
    }
  }
}

resource cosmosFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (enablePrivateNetworking) {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${aifCosmosConnectionName}'
  properties: {
    category: 'CosmosDB'
    target: cosmosDbEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: cosmosAccountResourceId
      location: cosmosAccountLocation
    }
  }
}

output aiSearchFoundryConnectionName string = aiSearchFoundryConnection.name
output storageFoundryConnectionName string = enablePrivateNetworking ? storageFoundryConnection.name : ''
output cosmosFoundryConnectionName string = enablePrivateNetworking ? cosmosFoundryConnection.name : ''

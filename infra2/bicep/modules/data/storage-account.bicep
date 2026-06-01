// ========== Storage Account for AI Foundry Workshop ========== //
targetScope = 'resourceGroup'

@minLength(3)
@description('The name of the solution, used as a base for naming all resources.')
param solutionName string

@description('The Azure region where storage resources will be deployed.')
param solutionLocation string

@description('Tags to apply to all resources.')
param tags object = {}

var storageName = take('st${toLower(replace(solutionName, '-', ''))}', 24)

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-08-01' = {
  name: storageName
  location: solutionLocation
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
      requireInfrastructureEncryption: true
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-08-01' = {
  parent: storageAccount
  name: 'default'
}

resource defaultContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-08-01' = {
  parent: blobService
  name: 'default'
  properties: {
    publicAccess: 'None'
  }
}

@description('The resource ID of the storage account.')
output storageAccountId string = storageAccount.id

@description('The name of the storage account.')
output storageAccountName string = storageAccount.name

@description('The primary blob endpoint of the storage account.')
output storageBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob

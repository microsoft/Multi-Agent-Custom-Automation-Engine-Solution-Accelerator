// Creates Azure dependent resources for Azure AI studio
param solutionName string
param solutionLocation string
param keyVaultName string
param gptModelName string
param gptModelVersion string
param managedIdentityObjectId string
param aiServicesEndpoint string
param aiServicesKey string
param aiServicesId string

// Load the abbrevations file required to name the azure resources.
var abbrs = loadJsonContent('./abbreviations.json')

var storageName = '${abbrs.storage.storageAccount}${solutionName}hub'
var storageSkuName = 'Standard_LRS'
var aiServicesName = '${abbrs.ai.aiServices}${solutionName}'
var workspaceName = '${abbrs.managementGovernance.logAnalyticsWorkspace}${solutionName}hub'
//var keyvaultName = '${abbrs.security.keyVault}${solutionName}'
var location = solutionLocation 
var aiHubName = '${abbrs.ai.aiHub}${solutionName}'
var aiHubFriendlyName = aiHubName
var aiHubDescription = 'AI Hub for MACAE template'
var aiProjectName = '${abbrs.ai.aiHubProject}${solutionName}'
var aiProjectFriendlyName = aiProjectName
var aiSearchName = '${abbrs.ai.aiSearch}${solutionName}'


resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' existing = {
  name: keyVaultName
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: {}
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}


var storageNameCleaned = replace(storageName, '-', '')


resource storage 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageNameCleaned
  location: location
  sku: {
    name: storageSkuName
  }
  kind: 'StorageV2'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    encryption: {
      keySource: 'Microsoft.Storage'
      requireInfrastructureEncryption: false
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
        file: {
          enabled: true
          keyType: 'Account'
        }
        queue: {
          enabled: true
          keyType: 'Service'
        }
        table: {
          enabled: true
          keyType: 'Service'
        }
      }
    }
    isHnsEnabled: false
    isNfsV3Enabled: false
    keyPolicy: {
      keyExpirationPeriodInDays: 7
    }
    largeFileSharesState: 'Disabled'
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
  }
}

@description('This is the built-in Storage Blob Data Contributor.')
resource blobDataContributor 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: subscription()
  name: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
}

resource storageroleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, managedIdentityObjectId, blobDataContributor.id)
  scope: storage
  properties: {
    principalId: managedIdentityObjectId
    roleDefinitionId: blobDataContributor.id
    principalType: 'ServicePrincipal'
  }
}

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: aiHubName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // organization
    friendlyName: aiHubFriendlyName
    description: aiHubDescription

    // dependent resources
    keyVault: keyVault.id
    storageAccount: storage.id
  }
  kind: 'hub'

  resource aiServicesConnection 'connections@2024-07-01-preview' = {
    name: '${aiHubName}-connection-AzureOpenAI'
    properties: {
      category: 'AIServices'
      target: aiServicesEndpoint
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: aiServicesId
      }
    }
  }
}

resource aiHubProject 'Microsoft.MachineLearningServices/workspaces@2024-01-01-preview' = {
  name: aiProjectName
  location: location
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiProjectFriendlyName
    hubResourceId: aiHub.id
  }
}

resource aiDeveloper 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '64702f94-c441-49e6-a78b-ef80e0188fee'
}

resource aiDevelopertoAIProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiHubProject.id, aiDeveloper.id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: aiDeveloper.id
    principalId: aiHubProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource tenantIdEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'TENANT-ID'
  properties: {
    value: subscription().tenantId
  }
}

resource azureOpenAIInferenceEndpoint 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPENAI-INFERENCE-ENDPOINT'
  properties: {
    value:''
  }
}

resource azureOpenAIInferenceKey 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPENAI-INFERENCE-KEY'
  properties: {
    value:''
  }
}

resource azureOpenAIApiKeyEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPENAI-KEY'
  properties: {
    value: aiServicesKey //aiServices_m.listKeys().key1
  }
}

resource azureOpenAIDeploymentModel 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPEN-AI-DEPLOYMENT-MODEL'
  properties: {
    value: gptModelName
  }
}

resource azureOpenAIApiVersionEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPENAI-PREVIEW-API-VERSION'
  properties: {
    value: gptModelVersion  //'2024-02-15-preview'
  }
}

resource azureOpenAIEndpointEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPENAI-ENDPOINT'
  properties: {
    value: aiServicesEndpoint//aiServices_m.properties.endpoint
  }
}

resource azureAIProjectConnectionStringEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-AI-PROJECT-CONN-STRING'
  properties: {
    value: '${split(aiHubProject.properties.discoveryUrl, '/')[2]};${subscription().subscriptionId};${resourceGroup().name};${aiHubProject.name}'
  }
}

resource azureOpenAICUApiVersionEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-OPENAI-CU-VERSION'
  properties: {
    value: '?api-version=2024-12-01-preview'
  }
}

resource azureSearchIndexEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-SEARCH-INDEX'
  properties: {
    value: 'transcripts_index'
  }
}

resource cogServiceEndpointEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'COG-SERVICES-ENDPOINT'
  properties: {
    value: aiServicesEndpoint
  }
}

resource cogServiceKeyEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'COG-SERVICES-KEY'
  properties: {
    value: aiServicesKey
  }
}

resource cogServiceNameEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'COG-SERVICES-NAME'
  properties: {
    value: aiServicesName
  }
}

resource azureSubscriptionIdEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-SUBSCRIPTION-ID'
  properties: {
    value: subscription().subscriptionId
  }
}

resource resourceGroupNameEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-RESOURCE-GROUP'
  properties: {
    value: resourceGroup().name
  }
}

resource azureLocatioEntry 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: keyVault
  name: 'AZURE-LOCATION'
  properties: {
    value: solutionLocation
  }
}

output keyvaultName string = keyVaultName
output keyvaultId string = keyVault.id

output aiServicesName string = aiServicesName 
output aiSearchName string = aiSearchName
output aiProjectName string = aiHubProject.name

output storageAccountName string = storageNameCleaned

output logAnalyticsId string = logAnalytics.id
output storageAccountId string = storage.id

output projectConnectionString string = '${split(aiHubProject.properties.discoveryUrl, '/')[2]};${subscription().subscriptionId};${resourceGroup().name};${aiHubProject.name}'

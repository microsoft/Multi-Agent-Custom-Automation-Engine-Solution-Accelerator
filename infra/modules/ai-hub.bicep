@description('Required. Name of the AI Hub resource')
param name string
@description('Required. Tags for the AI Hub resource')
param tags object
@description('Required. Location for the AI Hub resource')
param location string
@description('Required. SKU for the AI Hub resource')
param sku string
@description('Required. Resource ID of the Key Vault to associate with the AI Hub')
param storageAccountResourceId string
@description('Required. Resource ID of the Log Analytics Workspace for diagnostic settings')
param logAnalyticsWorkspaceResourceId string
@description('Required. Resource ID of the Application Insights for telemetry')
param applicationInsightsResourceId string
@description('Required. Name of the AI Foundry AI Services resource')
param aiFoundryAiServicesName string
@description('Required. Flag to enable telemetry')
param enableTelemetry bool
@description('Required. Flag to enable virtual network integration')
param virtualNetworkEnabled bool
import { privateEndpointSingleServiceType } from 'br/public:avm/utl/types/avm-common-types:0.4.0'
@description('Required. List of private endpoints to associate with the AI Hub')
param privateEndpoints privateEndpointSingleServiceType[]

resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: aiFoundryAiServicesName
}

module aiFoundryAiHub 'br/public:avm/res/machine-learning-services/workspace:0.10.1' = {
  name: take('avm.res.machine-learning-services.workspace.${name}', 64)
  params: {
    name: name
    tags: tags
    location: location
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }]
    kind: 'Hub'
    sku: sku
    description: 'AI Hub for Multi Agent Custom Automation Engine Solution Accelerator template'
    //associatedKeyVaultResourceId: keyVaultResourceId
    associatedStorageAccountResourceId: storageAccountResourceId
    associatedApplicationInsightsResourceId: applicationInsightsResourceId
    connections: [
      {
        name: 'connection-AzureOpenAI'
        category: 'AIServices'
        target: aiServices.properties.endpoint
        isSharedToAll: true
        metadata: {
          ApiType: 'Azure'
          ResourceId: aiServices.id
        }
        connectionProperties: {
          authType: 'ApiKey'
          credentials: {
            key: aiServices.listKeys().key1
          }
        }
      }
    ]
    //publicNetworkAccess: virtualNetworkEnabled ? 'Disabled' : 'Enabled'
    publicNetworkAccess: 'Enabled' //TODO: connection via private endpoint is not working from containers network. Change this when fixed
    managedNetworkSettings: virtualNetworkEnabled
      ? {
          isolationMode: 'AllowInternetOutbound'
          outboundRules: null //TODO: Refine this
        }
      : null
    privateEndpoints: privateEndpoints
  }
}

@description('Resource ID of the AI Hub')
output resourceId string = aiFoundryAiHub.outputs.resourceId

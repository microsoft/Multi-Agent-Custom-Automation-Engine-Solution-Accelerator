// ============================================================================
// main.bicep — AVM Orchestrator for MACAE
// Description: Modular AVM-based orchestrator for the Multi-Agent Custom
//              Automation Engine accelerator. This preserves the existing
//              infra\main.bicep deployment contract while replacing inline
//              registry references with local module wrappers under ./modules.
// ============================================================================
targetScope = 'resourceGroup'

metadata name = 'Multi-Agent Custom Automation Engine - AVM'
metadata description = 'AVM orchestrator for the Multi-Agent Custom Automation Engine accelerator. Deploys the same logical resources and preserves the same outputs as infra\\main.bicep using local AVM wrapper modules.'

// ============================================================================
// Parameters — Core
// ============================================================================

@description('Optional. A unique application/solution name for all resources in this deployment. This should be 3-16 characters long.')
@minLength(3)
@maxLength(16)
param solutionName string = 'macae'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = take(uniqueString(subscription().id, resourceGroup().name, solutionName), 5)

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services. Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios.')
@allowed([
  'australiaeast'
  'centralus'
  'eastasia'
  'eastus2'
  'japaneast'
  'northeurope'
  'southeastasia'
  'uksouth'
])
param location string

@description('Optional. The tags to apply to all deployed Azure resources.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Tag, Created by user name')
param createdBy string = contains(deployer(), 'userPrincipalName')
  ? split(deployer().userPrincipalName, '@')[0]
  : deployer().objectId

// ============================================================================
// Parameters — AI
// ============================================================================

@allowed(['australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus', 'westus3', 'polandcentral', 'uaenorth'])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1, 150'
      'OpenAI.GlobalStandard.o4-mini, 50'
      'OpenAI.GlobalStandard.gpt4.1-mini, 50'
      'OpenAI.GlobalStandard.gpt-image-1.5, 5'
    ]
  }
})
@description('Required. Location for all AI service resources. This should be one of the supported Azure AI Service locations.')
param azureAiServiceLocation string

@minLength(1)
@description('Optional. Name of the GPT model to deploy.')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the GPT model to deploy. Defaults to 2025-04-14.')
param gptModelVersion string = '2025-04-14'

@minLength(1)
@description('Optional. Name of the GPT RAI model to deploy.')
param gpt4_1ModelName string = 'gpt-4.1'

@description('Optional. Version of the GPT RAI model to deploy. Defaults to 2025-04-14.')
param gpt4_1ModelVersion string = '2025-04-14'

@minLength(1)
@description('Optional. Name of the GPT reasoning model to deploy.')
param gptReasoningModelName string = 'o4-mini'

@description('Optional. Version of the GPT reasoning model to deploy. Defaults to 2025-04-16.')
param gptReasoningModelVersion string = '2025-04-16'

@minLength(1)
@description('Optional. Name of the image-generation model to deploy. Defaults to gpt-image-1.5.')
param gptImageModelName string = 'gpt-image-1.5'

@description('Optional. Version of the image-generation model to deploy. Defaults to 2025-12-16.')
param gptImageModelVersion string = '2025-12-16'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT model deployment type. Defaults to GlobalStandard.')
param deploymentType string = 'GlobalStandard'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT 4.1 model deployment type. Defaults to GlobalStandard.')
param gpt4_1ModelDeploymentType string = 'GlobalStandard'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT reasoning model deployment type. Defaults to GlobalStandard.')
param gptReasoningModelDeploymentType string = 'GlobalStandard'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT image model deployment type. Defaults to GlobalStandard.')
param gptImageModelDeploymentType string = 'GlobalStandard'

@description('Optional. AI model deployment token capacity. Defaults to 50 for optimal performance.')
param gptDeploymentCapacity int = 50

@description('Optional. AI model deployment token capacity. Defaults to 150 for optimal performance.')
param gpt4_1ModelCapacity int = 150

@description('Optional. AI model deployment token capacity. Defaults to 50 for optimal performance.')
param gptReasoningModelCapacity int = 50

@description('Optional. gpt-image-1.5 deployment capacity (RPM). Defaults to 5 to support concurrent marketing-image generation across multiple sessions.')
param gptImageModelCapacity int = 5

@description('Optional. Version of the Azure OpenAI service to deploy. Defaults to 2024-12-01-preview.')
param azureOpenaiAPIVersion string = '2024-12-01-preview'

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. The Container Registry hostname where the docker images for the backend are located.')
param backendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the backend.')
param backendContainerImageName string = 'macaebackend'

@description('Optional. The Container Image Tag to deploy on the backend.')
param backendContainerImageTag string = 'latest_v4'

@description('Optional. The Container Registry hostname where the docker images for the frontend are located.')
param frontendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the frontend.')
param frontendContainerImageName string = 'macaefrontend'

@description('Optional. The Container Image Tag to deploy on the frontend.')
param frontendContainerImageTag string = 'latest_v4'

@description('Optional. The Container Registry hostname where the docker images for the MCP are located.')
param MCPContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the MCP.')
param MCPContainerImageName string = 'macaemcp'

@description('Optional. The Container Image Tag to deploy on the MCP.')
param MCPContainerImageTag string = 'latest_v4'

// ============================================================================
// Parameters — Feature Flags / WAF
// ============================================================================

@description('Optional. Enable monitoring applicable resources, aligned with the Well Architected Framework recommendations. This setting enables Application Insights and Log Analytics and configures applicable resources to send logs. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false

@secure()
@description('Optional. The user name for the administrator account of the virtual machine. Allows to customize credentials if enablePrivateNetworking is set to true.')
param vmAdminUsername string?

@secure()
@description('Optional. The password for the administrator account of the virtual machine. Allows to customize credentials if enablePrivateNetworking is set to true.')
param vmAdminPassword string?

@description('Optional. The size of the virtual machine. Defaults to Standard_D2s_v5.')
param vmSize string = 'Standard_D2s_v5'

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics Workspace.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing Ai Foundry AI Services resource.')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Parameters — Data
// ============================================================================

@description('Optional. Blob container name for retail customer dataset.')
param storageContainerNameRetailCustomer string = 'retail-dataset-customer'

@description('Optional. Blob container name for retail order dataset.')
param storageContainerNameRetailOrder string = 'retail-dataset-order'

@description('Optional. Blob container name for RFP summary dataset.')
param storageContainerNameRFPSummary string = 'rfp-summary-dataset'

@description('Optional. Blob container name for RFP risk dataset.')
param storageContainerNameRFPRisk string = 'rfp-risk-dataset'

@description('Optional. Blob container name for RFP compliance dataset.')
param storageContainerNameRFPCompliance string = 'rfp-compliance-dataset'

@description('Optional. Blob container name for contract summary dataset.')
param storageContainerNameContractSummary string = 'contract-summary-dataset'

@description('Optional. Blob container name for contract risk dataset.')
param storageContainerNameContractRisk string = 'contract-risk-dataset'

@description('Optional. Blob container name for contract compliance dataset.')
param storageContainerNameContractCompliance string = 'contract-compliance-dataset'

// ============================================================================
// Variables
// ============================================================================

var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId
var deployerPrincipalType = contains(deployerInfo, 'userPrincipalName') ? 'User' : 'ServicePrincipal'

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

var allTags = union({
  'azd-env-name': solutionName
}, tags)
var existingTags = resourceGroup().tags ?? {}
var resourceTags = union(existingTags, allTags, {
  TemplateName: 'MACAE'
  Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
  CreatedBy: createdBy
  DeploymentName: deployment().name
  SolutionSuffix: solutionSuffix
})

var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)
var existingLawSubscription = useExistingLogAnalytics ? split(existingLogAnalyticsWorkspaceId, '/')[2] : ''
var existingLawResourceGroup = useExistingLogAnalytics ? split(existingLogAnalyticsWorkspaceId, '/')[4] : ''
var existingLawName = useExistingLogAnalytics ? split(existingLogAnalyticsWorkspaceId, '/')[8] : ''

var useExistingAIProject = !empty(existingFoundryProjectResourceId)
var aiFoundryAiServicesResourceGroupName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name
var aiFoundryAiServicesSubscriptionId = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var aiFoundryAiServicesResourceName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[8] : 'aif-${solutionSuffix}'
var aiFoundryAiProjectResourceName = useExistingAIProject
  ? (length(split(existingFoundryProjectResourceId, '/')) > 10 ? split(existingFoundryProjectResourceId, '/')[10] : '')
  : 'proj-${solutionSuffix}'

var cosmosDbZoneRedundantHaRegionPairs = {
  australiaeast: 'uksouth'
  centralus: 'eastus2'
  eastasia: 'southeastasia'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'australiaeast'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
}
var cosmosDbHaLocation = cosmosDbZoneRedundantHaRegionPairs[location]

var replicaRegionPairs = {
  australiaeast: 'australiasoutheast'
  centralus: 'westus'
  eastasia: 'japaneast'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'eastasia'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
}
var replicaLocation = replicaRegionPairs[location]

var aiModelDeployments = [
  {
    deploymentName: gptModelName
    modelName: gptModelName
    modelVersion: gptModelVersion
    skuName: deploymentType
    skuCapacity: gptDeploymentCapacity
  }
  {
    deploymentName: gpt4_1ModelName
    modelName: gpt4_1ModelName
    modelVersion: gpt4_1ModelVersion
    skuName: gpt4_1ModelDeploymentType
    skuCapacity: gpt4_1ModelCapacity
  }
  {
    deploymentName: gptReasoningModelName
    modelName: gptReasoningModelName
    modelVersion: gptReasoningModelVersion
    skuName: gptReasoningModelDeploymentType
    skuCapacity: gptReasoningModelCapacity
  }
  {
    deploymentName: gptImageModelName
    modelName: gptImageModelName
    modelVersion: gptImageModelVersion
    skuName: gptImageModelDeploymentType
    skuCapacity: gptImageModelCapacity
  }
]
var supportedModels = [
  gptModelName
  gpt4_1ModelName
  gptReasoningModelName
  gptImageModelName
]

var containerAppName = 'ca-${solutionSuffix}'

var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.documents.azure.com'
  'privatelink.blob.core.windows.net'
  'privatelink.search.windows.net'
]
var dnsZoneIndex = {
  cognitiveServices: 0
  openAI: 1
  aiServices: 2
  cosmosDb: 3
  blob: 4
  search: 5
}
var aiRelatedDnsZoneIndices = [
  dnsZoneIndex.cognitiveServices
  dnsZoneIndex.openAI
  dnsZoneIndex.aiServices
]

var virtualNetworkSubnets = [
  {
    name: 'backend'
    addressPrefixes: ['10.0.0.0/27']
    networkSecurityGroup: {
      name: 'nsg-backend'
      securityRules: [
        {
          name: 'deny-hop-outbound'
          properties: {
            access: 'Deny'
            destinationAddressPrefix: '*'
            destinationPortRanges: [
              '22'
              '3389'
            ]
            direction: 'Outbound'
            priority: 200
            protocol: 'Tcp'
            sourceAddressPrefix: 'VirtualNetwork'
            sourcePortRange: '*'
          }
        }
      ]
    }
  }
  {
    name: 'containers'
    addressPrefixes: ['10.0.2.0/23']
    delegation: 'Microsoft.App/environments'
    privateEndpointNetworkPolicies: 'Enabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
    networkSecurityGroup: {
      name: 'nsg-containers'
      securityRules: [
        {
          name: 'deny-hop-outbound'
          properties: {
            access: 'Deny'
            destinationAddressPrefix: '*'
            destinationPortRanges: [
              '22'
              '3389'
            ]
            direction: 'Outbound'
            priority: 200
            protocol: 'Tcp'
            sourceAddressPrefix: 'VirtualNetwork'
            sourcePortRange: '*'
          }
        }
      ]
    }
  }
  {
    name: 'webserverfarm'
    addressPrefixes: ['10.0.4.0/27']
    delegation: 'Microsoft.Web/serverfarms'
    privateEndpointNetworkPolicies: 'Enabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
    networkSecurityGroup: {
      name: 'nsg-webserverfarm'
      securityRules: [
        {
          name: 'deny-hop-outbound'
          properties: {
            access: 'Deny'
            destinationAddressPrefix: '*'
            destinationPortRanges: [
              '22'
              '3389'
            ]
            direction: 'Outbound'
            priority: 200
            protocol: 'Tcp'
            sourceAddressPrefix: 'VirtualNetwork'
            sourcePortRange: '*'
          }
        }
      ]
    }
  }
  {
    name: 'administration'
    addressPrefixes: ['10.0.0.32/27']
    networkSecurityGroup: {
      name: 'nsg-administration'
      securityRules: [
        {
          name: 'deny-hop-outbound'
          properties: {
            access: 'Deny'
            destinationAddressPrefix: '*'
            destinationPortRanges: [
              '22'
              '3389'
            ]
            direction: 'Outbound'
            priority: 200
            protocol: 'Tcp'
            sourceAddressPrefix: 'VirtualNetwork'
            sourcePortRange: '*'
          }
        }
      ]
    }
  }
  {
    name: 'AzureBastionSubnet'
    addressPrefixes: ['10.0.0.64/26']
    networkSecurityGroup: {
      name: 'nsg-bastion'
      securityRules: [
        {
          name: 'AllowGatewayManager'
          properties: {
            access: 'Allow'
            direction: 'Inbound'
            priority: 2702
            protocol: '*'
            sourcePortRange: '*'
            destinationPortRange: '443'
            sourceAddressPrefix: 'GatewayManager'
            destinationAddressPrefix: '*'
          }
        }
        {
          name: 'AllowHttpsInBound'
          properties: {
            access: 'Allow'
            direction: 'Inbound'
            priority: 2703
            protocol: '*'
            sourcePortRange: '*'
            destinationPortRange: '443'
            sourceAddressPrefix: 'Internet'
            destinationAddressPrefix: '*'
          }
        }
        {
          name: 'AllowSshRdpOutbound'
          properties: {
            access: 'Allow'
            direction: 'Outbound'
            priority: 100
            protocol: '*'
            sourcePortRange: '*'
            destinationPortRanges: ['22', '3389']
            sourceAddressPrefix: '*'
            destinationAddressPrefix: 'VirtualNetwork'
          }
        }
        {
          name: 'AllowAzureCloudOutbound'
          properties: {
            access: 'Allow'
            direction: 'Outbound'
            priority: 110
            protocol: 'Tcp'
            sourcePortRange: '*'
            destinationPortRange: '443'
            sourceAddressPrefix: '*'
            destinationAddressPrefix: 'AzureCloud'
          }
        }
      ]
    }
  }
]

var storageAccountName = replace('st${solutionSuffix}', '-', '')
var cosmosDbResourceName = 'cosmos-${solutionSuffix}'
var cosmosDbDatabaseName = 'macae'
var cosmosDbDatabaseMemoryContainerName = 'memory'
var aiSearchConnectionName = 'aifp-srch-connection-${solutionSuffix}'

var aiSearchIndexNameForContractSummary = 'contract-summary-doc-index'
var aiSearchIndexNameForContractRisk = 'contract-risk-doc-index'
var aiSearchIndexNameForContractCompliance = 'contract-compliance-doc-index'
var aiSearchIndexNameForRetailCustomer = 'macae-retail-customer-index'
var aiSearchIndexNameForRetailOrder = 'macae-retail-order-index'
var aiSearchIndexNameForRFPSummary = 'macae-rfp-summary-index'
var aiSearchIndexNameForRFPRisk = 'macae-rfp-risk-index'
var aiSearchIndexNameForRFPCompliance = 'macae-rfp-compliance-index'

// var aiFoundryRoleIds = {
//   foundryUser: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
//   azureAiDeveloper: '64702f94-c441-49e6-a78b-ef80e0188fee'
//   cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
// }

// var existingAiFoundryManagedIdentityRoles = [
//   {
//     suffix: 'managedidentity-foundry-user'
//     roleDefinitionId: format('/subscriptions/{0}/providers/Microsoft.Authorization/roleDefinitions/{1}', aiFoundryAiServicesSubscriptionId, aiFoundryRoleIds.foundryUser)
//   }
//   {
//     suffix: 'managedidentity-ai-developer'
//     roleDefinitionId: format('/subscriptions/{0}/providers/Microsoft.Authorization/roleDefinitions/{1}', aiFoundryAiServicesSubscriptionId, aiFoundryRoleIds.azureAiDeveloper)
//   }
//   {
//     suffix: 'managedidentity-openai-user'
//     roleDefinitionId: format('/subscriptions/{0}/providers/Microsoft.Authorization/roleDefinitions/{1}', aiFoundryAiServicesSubscriptionId, aiFoundryRoleIds.cognitiveServicesOpenAIUser)
//   }
// ]

// var existingAiFoundryDeployerRoles = [
//   {
//     suffix: 'deployer-foundry-user'
//     roleDefinitionId: format('/subscriptions/{0}/providers/Microsoft.Authorization/roleDefinitions/{1}', aiFoundryAiServicesSubscriptionId, aiFoundryRoleIds.foundryUser)
//   }
//   {
//     suffix: 'deployer-ai-developer'
//     roleDefinitionId: format('/subscriptions/{0}/providers/Microsoft.Authorization/roleDefinitions/{1}', aiFoundryAiServicesSubscriptionId, aiFoundryRoleIds.azureAiDeveloper)
//   }
// ]

// ============================================================================
// Resource Group Tags
// ============================================================================

resource resourceGroupTags 'Microsoft.Resources/tags@2024-11-01' = {
  name: 'default'
  properties: {
    tags: resourceTags
  }
}

// ============================================================================
// Monitoring
// ============================================================================

resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' existing = if (useExistingLogAnalytics) {
  name: existingLawName
  scope: resourceGroup(existingLawSubscription, existingLawResourceGroup)
}

// Container Apps Environment requires a Log Analytics workspace even when
// monitoring-specific features are disabled.
module log_analytics './modules/monitoring/log-analytics.bicep' = if (!useExistingLogAnalytics) {
  name: take('module.log-analytics.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    retentionInDays: 365
    dailyQuotaGb: enableRedundancy ? '150' : null
    replicationLocation: enableRedundancy ? replicaLocation : ''
    enableTelemetry: enableTelemetry
    publicNetworkAccessForIngestion: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    publicNetworkAccessForQuery: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    dataSources: enablePrivateNetworking
      ? [
          {
            tags: tags
            eventLogName: 'Application'
            eventTypes: [
              {
                eventType: 'Error'
              }
              {
                eventType: 'Warning'
              }
              {
                eventType: 'Information'
              }
            ]
            kind: 'WindowsEvent'
            name: 'applicationEvent'
          }
          {
            counterName: '% Processor Time'
            instanceName: '*'
            intervalSeconds: 60
            kind: 'WindowsPerformanceCounter'
            name: 'windowsPerfCounter1'
            objectName: 'Processor'
          }
          {
            kind: 'IISLogs'
            name: 'sampleIISLog1'
            state: 'OnPremiseEnabled'
          }
        ]
      : null
  }
}

var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics ? existingLogAnalyticsWorkspace.id : log_analytics!.outputs.resourceId
var logAnalyticsWorkspaceName = useExistingLogAnalytics ? existingLogAnalyticsWorkspace.name : log_analytics!.outputs.name
var monitoringDiagnosticSettings = enableMonitoring ? [
  {
    workspaceResourceId: logAnalyticsWorkspaceResourceId
  }
] : []

module app_insights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    workspaceResourceId: logAnalyticsWorkspaceResourceId
    retentionInDays: 365
    disableIpMasking: false
    enableTelemetry: enableTelemetry
  }
}

// ============================================================================
// Networking (conditional WAF)
// ============================================================================

module virtualNetwork './modules/networking/virtual-network.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-network.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    addressPrefixes: ['10.0.0.0/8']
    subnets: virtualNetworkSubnets
    tags: tags
    logAnalyticsWorkspaceId: logAnalyticsWorkspaceResourceId
    enableTelemetry: enableTelemetry
    resourceSuffix: solutionSuffix
  }
}

var containerSubnetIndex = enablePrivateNetworking ? indexOf(map(virtualNetwork!.outputs.subnets, subnet => subnet.name), 'containers') : -1
var containerSubnetResourceId = enablePrivateNetworking && containerSubnetIndex >= 0 ? virtualNetwork!.outputs.subnets[containerSubnetIndex].resourceId : ''

module bastionHost './modules/networking/bastion-host.bicep' = if (enablePrivateNetworking) {
  name: take('module.bastion-host.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
    publicIPDiagnosticSettings: enableMonitoring ? monitoringDiagnosticSettings : null
    diagnosticSettings: enableMonitoring ? monitoringDiagnosticSettings : null
  }
}

module maintenanceConfiguration './modules/compute/maintenance-configuration.bicep' = if (enablePrivateNetworking) {
  name: take('module.maintenance-configuration.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

var dataCollectionRulesLocation = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.location
  : log_analytics!.outputs.location
module windowsVmDataCollectionRules './modules/monitoring/data-collection-rule.bicep' = if (enablePrivateNetworking && enableMonitoring) {
  name: take('module.data-collection-rule.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: dataCollectionRulesLocation
    tags: tags
    enableTelemetry: enableTelemetry
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
  }
}

var virtualMachineAvailabilityZone = 1
module proximityPlacementGroup './modules/compute/proximity-placement-group.bicep' = if (enablePrivateNetworking) {
  name: take('module.proximity-placement-group.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    availabilityZone: virtualMachineAvailabilityZone
    vmSizes: [vmSize]
  }
}

module virtualMachine './modules/compute/virtual-machine.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-machine.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    vmSize: vmSize
    adminUsername: vmAdminUsername ?? 'JumpboxAdminUser'
    adminPassword: vmAdminPassword ?? 'JumpboxAdminP@ssw0rd1234!'
    subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId
    diagnosticSettings: enableMonitoring ? monitoringDiagnosticSettings : null
    osType: 'Windows'
    availabilityZone: virtualMachineAvailabilityZone
    maintenanceConfigurationResourceId: maintenanceConfiguration!.outputs.resourceId
    proximityPlacementGroupResourceId: proximityPlacementGroup!.outputs.resourceId
    extensionMonitoringAgentConfig: enableMonitoring ? {
      dataCollectionRuleAssociations: [
        {
          dataCollectionRuleResourceId: windowsVmDataCollectionRules!.outputs.resourceId
          name: 'send-${logAnalyticsWorkspaceName}'
        }
      ]
      enabled: true
      tags: tags
    } : null
  }
}

@batchSize(5)
module privateDnsZoneDeployments './modules/networking/private-dns-zone.bicep' = [for (zone, i) in privateDnsZones: if (enablePrivateNetworking && (!useExistingAIProject || !contains(aiRelatedDnsZoneIndices, i))) {
  name: take('module.private-dns-zone.${split(zone, '.')[1]}.${solutionName}', 64)
  params: {
    name: zone
    tags: tags
    enableTelemetry: enableTelemetry
    virtualNetworkLinks: [
      {
        name: take('vnetlink-${virtualNetwork!.outputs.name}-${split(zone, '.')[1]}', 80)
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}]

// ============================================================================
// Identity
// ============================================================================

module managed_identity './modules/identity/managed-identity.bicep' = {
  name: take('module.managed-identity.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    identityName: 'id-${solutionSuffix}'
    location: location
    tags: tags
  }
}

// ============================================================================
// AI Services + Foundry
// ============================================================================

module existing_project_setup './modules/ai/existing-project-setup.bicep' = if (useExistingAIProject) {
  name: take('module.existing-project-setup.${solutionName}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    name: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectResourceName
  }
}

module ai_foundry_project './modules/ai/ai-foundry-project.bicep' = if (!useExistingAIProject) {
  name: take('module.ai-foundry-project.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: tags
    publicNetworkAccess: 'Enabled' // Always enabled, as MCP KnowledgeBase Connections doesn't work private endpoints
  }
}

// @batchSize(1)
// module existingAiFoundryManagedIdentityRoleAssignments './modules/identity/cross-scope-role-assignment.bicep' = [for role in existingAiFoundryManagedIdentityRoles: if (useExistingAIProject) {
//   name: take('module.existing-aif-mi-${role.suffix}.${solutionName}', 64)
//   scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
//   params: {
//     principalId: managed_identity.outputs.principalId
//     roleDefinitionId: role.roleDefinitionId
//     roleAssignmentName: guid(solutionSuffix, aiFoundryAiServicesResourceName, role.suffix)
//     aiFoundryName: aiFoundryAiServicesResourceName
//     principalType: 'ServicePrincipal'
//   }
// }]

// @batchSize(1)
// module existingAiFoundryDeployerRoleAssignments './modules/identity/cross-scope-role-assignment.bicep' = [for role in existingAiFoundryDeployerRoles: if (useExistingAIProject) {
//   name: take('module.existing-aif-deployer-${role.suffix}.${solutionName}', 64)
//   scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
//   params: {
//     principalId: deployingUserPrincipalId
//     roleDefinitionId: role.roleDefinitionId
//     roleAssignmentName: guid(solutionSuffix, aiFoundryAiServicesResourceName, role.suffix)
//     aiFoundryName: aiFoundryAiServicesResourceName
//     principalType: deployerPrincipalType
//   }
// }]

// module aiFoundryPrivateEndpoint './modules/networking/private-endpoint.bicep' = if (enablePrivateNetworking && !useExistingAIProject) {
//   name: take('module.pe-ai-foundry.${solutionName}', 64)
//   params: {
//     name: 'pep-${aiFoundryAiServicesResourceName}'
//     customNetworkInterfaceName: 'nic-${aiFoundryAiServicesResourceName}'
//     location: location
//     tags: tags
//     subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
//     privateLinkServiceConnections: [
//       {
//         name: 'pep-${aiFoundryAiServicesResourceName}-connection'
//         properties: {
//           privateLinkServiceId: ai_foundry_project!.outputs.resourceId
//           groupIds: ['account']
//         }
//       }
//     ]
//     privateDnsZoneGroup: {
//       privateDnsZoneGroupConfigs: [
//         {
//           name: 'ai-services-dns-zone-cognitiveservices'
//           privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
//         }
//         {
//           name: 'ai-services-dns-zone-openai'
//           privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.openAI]!.outputs.resourceId
//         }
//         {
//           name: 'ai-services-dns-zone-aiservices'
//           privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.aiServices]!.outputs.resourceId
//         }
//       ]
//     }
//   }
// }

var aiFoundryAiProjectName = useExistingAIProject ? existing_project_setup!.outputs.aiProjectName : ai_foundry_project!.outputs.projectName
var aiFoundryAiProjectEndpoint = useExistingAIProject ? existing_project_setup!.outputs.projectEndpoint : ai_foundry_project!.outputs.projectEndpoint
var aiFoundryAiProjectPrincipalId = useExistingAIProject ? existing_project_setup!.outputs.aiProjectPrincipalId : ai_foundry_project!.outputs.projectIdentityPrincipalId
var aiFoundryAiServicesEndpoint = useExistingAIProject ? existing_project_setup!.outputs.aiFoundryEndpoint : ai_foundry_project!.outputs.endpoint
var aiFoundryOpenAIEndpoint = 'https://${aiFoundryAiServicesResourceName}.openai.azure.com/'
var aiFoundryResourceId = useExistingAIProject ? existing_project_setup!.outputs.aiFoundryResourceId : ai_foundry_project!.outputs.resourceId

@batchSize(1)
module model_deployments './modules/ai/ai-foundry-model-deployment.bicep' = [for (deployment, i) in aiModelDeployments: {
  name: take('module.model-deployment-${i}.${solutionName}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    aiServicesAccountName: aiFoundryAiServicesResourceName
    deploymentName: deployment.deploymentName
    modelName: deployment.modelName
    modelVersion: deployment.modelVersion
    raiPolicyName: 'Microsoft.Default'
    skuName: deployment.skuName
    skuCapacity: deployment.skuCapacity
  }
  dependsOn: useExistingAIProject ? [existing_project_setup] : [ai_foundry_project]
}]

module ai_search './modules/ai/ai-search.bicep' = {
  name: take('module.ai-search.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    skuName: enableScalability ? 'standard' : 'basic'
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'Default'
    semanticSearch: 'free'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    enableTelemetry: enableTelemetry
    diagnosticSettings: monitoringDiagnosticSettings
    roleAssignments: [
      {
        roleDefinitionIdOrName: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
        principalId: deployingUserPrincipalId
        principalType: deployerPrincipalType
      }
      {
        principalId: managed_identity.outputs.principalId
        roleDefinitionIdOrName: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
        principalType: 'ServicePrincipal'
      }
      // {
      //   roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
      //   principalId: deployingUserPrincipalId
      //   principalType: deployerPrincipalType
      // }
      {
        principalId: managed_identity.outputs.principalId
        roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
        principalType: 'ServicePrincipal'
      }
      {
        principalId: aiFoundryAiProjectPrincipalId
        roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
        principalType: 'ServicePrincipal'
      }
      {
        principalId: aiFoundryAiProjectPrincipalId
        roleDefinitionIdOrName: '1407120a-92aa-4202-b7e9-c0e197c71c8f'// Search Index Data Reader'
        principalType: 'ServicePrincipal'
      }
    ]
    privateEndpoints: []
  }
}

// Base AI Search connection (CognitiveSearch / AAD).
// Per-KB RemoteTool connections (ProjectManagedIdentity) are created by
// infra/scripts/post-provision/seed_kb_connections.py at post-deploy time because the KB
// names are dynamic and depend on selected content packs.
module aiSearchFoundryConnection './modules/ai/ai-foundry-connection.bicep' = {
  name: take('module.foundry-search-conn.${solutionName}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectName
    connectionName: aiSearchConnectionName
    category: 'CognitiveSearch'
    target: ai_search.outputs.endpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: ai_search.outputs.resourceId
    }
    useWorkspaceManagedIdentity: true
  }
  dependsOn: useExistingAIProject ? [existing_project_setup, ai_search] : [ai_foundry_project, ai_search]
}

// ============================================================================
// Data
// ============================================================================

module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    containers: [
      {
        name: 'default'
        publicAccess: 'None'
      }
    ]
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
        principalId: deployingUserPrincipalId
        principalType: deployerPrincipalType
      }
      {
        principalId: managed_identity.outputs.principalId
        roleDefinitionIdOrName: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
        principalType: 'ServicePrincipal'
      }
    ]
    enablePrivateNetworking: enablePrivateNetworking
    privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''
    privateDnsZoneResourceIds: enablePrivateNetworking ? [
      privateDnsZoneDeployments[dnsZoneIndex.blob]!.outputs.resourceId
    ] : []
  }
}

module cosmosDBModule './modules/data/cosmos-db-nosql.bicep' = {
  name: take('module.cosmos-db.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    databaseName: cosmosDbDatabaseName
    containers: [
      {
        name: cosmosDbDatabaseMemoryContainerName
        partitionKeyPath: '/session_id'
      }
    ]
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    zoneRedundant: enableRedundancy
    enableAutomaticFailover: enableRedundancy
    haLocation: cosmosDbHaLocation
    enablePrivateNetworking: enablePrivateNetworking
    privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''
    privateDnsZoneResourceIds: enablePrivateNetworking ? [
      privateDnsZoneDeployments[dnsZoneIndex.cosmosDb]!.outputs.resourceId
    ] : []
  }
}

// ============================================================================
// Compute
// ============================================================================

module containerAppEnvironment './modules/compute/container-app-environment.bicep' = {
  name: take('module.container-app-environment.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
    infrastructureSubnetId: enablePrivateNetworking ? containerSubnetResourceId : ''
    zoneRedundant: enableRedundancy
    enablePrivateNetworking: enablePrivateNetworking
    enableMonitoring: enableMonitoring
    enableRedundancy: enableRedundancy
    workloadProfiles: enableRedundancy
      ? [
          {
            maximumCount: 3
            minimumCount: 3
            name: 'CAW01'
            workloadProfileType: 'D4'
          }
        ]
      : [
          {
            name: 'Consumption'
            workloadProfileType: 'Consumption'
          }
        ]
  }
}

module containerAppEnvDNSZone './modules/networking/private-dns-zone.bicep' = if (enablePrivateNetworking) {
  name: take('module.ca-env-dns-zone.${solutionName}', 64)
  params: {
    name: containerAppEnvironment.outputs.defaultDomain
    tags: tags
    enableTelemetry: enableTelemetry
    virtualNetworkLinks: [
      {
        name: take('vnetlink-${virtualNetwork!.outputs.name}-caenv', 80)
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
    a: [
      {
        name: '*'
        aRecords: [
          { ipv4Address: containerAppEnvironment.outputs.staticIp }
        ]
        ttl: 300
      }
    ]
  }
}

module containerApp './modules/compute/container-app.bicep' = {
  name: take('module.container-app.${solutionName}', 64)
  params: {
    name: containerAppName
    location: location
    tags: tags
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 8000
    ingressAllowInsecure: false
    enableTelemetry: enableTelemetry
    managedIdentities: {
      userAssignedResourceIds: [managed_identity.outputs.resourceId]
    }
    corsPolicy: {
      allowedOrigins: [
        'https://app-${solutionSuffix}.azurewebsites.net'
        'http://app-${solutionSuffix}.azurewebsites.net'
      ]
      allowedMethods: [
        'GET'
        'POST'
        'PUT'
        'DELETE'
        'OPTIONS'
      ]
    }
    scaleSettings: {
      minReplicas: 1
      maxReplicas: enableScalability ? 3 : 1
    }
    containers: [
      {
        name: 'backend'
        image: '${backendContainerRegistryHostname}/${backendContainerImageName}:${backendContainerImageTag}'
        resources: {
          cpu: '2.0'
          memory: '4.0Gi'
        }
        env: [
          {
            name: 'COSMOSDB_ENDPOINT'
            value: cosmosDBModule.outputs.endpoint
          }
          {
            name: 'COSMOSDB_DATABASE'
            value: cosmosDbDatabaseName
          }
          {
            name: 'COSMOSDB_CONTAINER'
            value: cosmosDbDatabaseMemoryContainerName
          }
          {
            name: 'AZURE_OPENAI_ENDPOINT'
            value: aiFoundryOpenAIEndpoint
          }
          {
            name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
            value: gptModelName
          }
          {
            name: 'AZURE_OPENAI_RAI_DEPLOYMENT_NAME'
            value: gpt4_1ModelName
          }
          {
            name: 'AZURE_OPENAI_API_VERSION'
            value: azureOpenaiAPIVersion
          }
          {
            name: 'APPLICATIONINSIGHTS_INSTRUMENTATION_KEY'
            value: enableMonitoring ? app_insights!.outputs.instrumentationKey : ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? app_insights!.outputs.connectionString : ''
          }
          {
            name: 'AZURE_AI_SUBSCRIPTION_ID'
            value: aiFoundryAiServicesSubscriptionId
          }
          {
            name: 'AZURE_AI_RESOURCE_GROUP'
            value: aiFoundryAiServicesResourceGroupName
          }
          {
            name: 'AZURE_AI_PROJECT_NAME'
            value: aiFoundryAiProjectName
          }
          {
            name: 'FRONTEND_SITE_NAME'
            value: 'https://app-${solutionSuffix}.azurewebsites.net'
          }
          {
            name: 'APP_ENV'
            value: 'Prod'
          }
          // NOTE: AZURE_AI_SEARCH_CONNECTION_NAME intentionally omitted.
          // The app defaults to per-KB RemoteTool connection names (e.g.
          // "macae-retail-customer-kb-mcp") which carry ProjectManagedIdentity
          // auth required by the KB MCP endpoint.
          {
            name: 'AZURE_AI_SEARCH_ENDPOINT'
            value: ai_search.outputs.endpoint
          }
          {
            name: 'AZURE_COGNITIVE_SERVICES'
            value: 'https://cognitiveservices.azure.com/.default'
          }
          {
            name: 'ORCHESTRATOR_MODEL_NAME'
            value: gptReasoningModelName
          }
          {
            name: 'AZURE_OPENAI_IMAGE_DEPLOYMENT'
            value: gptImageModelName
          }
          {
            name: 'MCP_SERVER_ENDPOINT'
            value: 'https://${containerAppMcp.outputs.fqdn}/mcp'
          }
          {
            name: 'MCP_SERVER_NAME'
            value: 'MacaeMcpServer'
          }
          {
            name: 'MCP_SERVER_DESCRIPTION'
            value: 'MCP server with greeting, HR, and planning tools'
          }
          {
            name: 'AZURE_TENANT_ID'
            value: tenant().tenantId
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: managed_identity.outputs.clientId
          }
          {
            name: 'SUPPORTED_MODELS'
            value: string(supportedModels)
          }
          {
            name: 'AZURE_STORAGE_BLOB_URL'
            value: storage_account.outputs.serviceEndpoints.blob
          }
          {
            name: 'AZURE_AI_PROJECT_ENDPOINT'
            value: aiFoundryAiProjectEndpoint
          }
          {
            name: 'AZURE_AI_AGENT_ENDPOINT'
            value: aiFoundryAiProjectEndpoint
          }
          {
            name: 'AZURE_BASIC_LOGGING_LEVEL'
            value: 'INFO'
          }
          {
            name: 'AZURE_PACKAGE_LOGGING_LEVEL'
            value: 'WARNING'
          }
          {
            name: 'AZURE_LOGGING_PACKAGES'
            value: ''
          }
        ]
      }
    ]
  }
}

module containerAppMcp './modules/compute/container-app.bicep' = {
  name: take('module.container-app-mcp.${solutionName}', 64)
  params: {
    name: 'ca-mcp-${solutionSuffix}'
    location: location
    tags: tags
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 9000
    ingressAllowInsecure: false
    enableTelemetry: enableTelemetry
    managedIdentities: {
      userAssignedResourceIds: [managed_identity.outputs.resourceId]
    }
    corsPolicy: {
      allowedOrigins: [
        'https://app-${solutionSuffix}.azurewebsites.net'
        'http://app-${solutionSuffix}.azurewebsites.net'
      ]
    }
    scaleSettings: {
      minReplicas: 1
      maxReplicas: enableScalability ? 3 : 1
    }
    containers: [
      {
        name: 'mcp'
        image: '${MCPContainerRegistryHostname}/${MCPContainerImageName}:${MCPContainerImageTag}'
        resources: {
          cpu: '2.0'
          memory: '4.0Gi'
        }
        env: [
          {
            name: 'HOST'
            value: '0.0.0.0'
          }
          {
            name: 'PORT'
            value: '9000'
          }
          {
            name: 'DEBUG'
            value: 'false'
          }
          {
            name: 'SERVER_NAME'
            value: 'MacaeMcpServer'
          }
          {
            name: 'ENABLE_AUTH'
            value: 'false'
          }
          {
            name: 'TENANT_ID'
            value: tenant().tenantId
          }
          {
            name: 'CLIENT_ID'
            value: managed_identity.outputs.clientId
          }
          {
            name: 'JWKS_URI'
            value: '${environment().authentication.loginEndpoint}/${tenant().tenantId}/discovery/v2.0/keys'
          }
          {
            name: 'ISSUER'
            value: 'https://sts.windows.net/${tenant().tenantId}/'
          }
          {
            name: 'AUDIENCE'
            value: 'api://${managed_identity.outputs.clientId}'
          }
          {
            name: 'DATASET_PATH'
            value: './datasets'
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: managed_identity!.outputs.clientId
          }
          {
            name: 'AZURE_OPENAI_ENDPOINT'
            value: 'https://${aiFoundryAiServicesResourceName}.openai.azure.com/'
          }
          {
            name: 'AZURE_OPENAI_IMAGE_DEPLOYMENT'
            value: gptImageModelName
          }
          {
            name: 'AZURE_STORAGE_BLOB_URL'
            value: storage_account.outputs.blobEndpoint
          }
          {
            name: 'BACKEND_URL'
            value: 'https://${containerAppName}.${containerAppEnvironment.outputs.defaultDomain}'
          }
        ]
      }
    ]
  }
}

module webServerFarm './modules/compute/app-service-plan.bicep' = {
  name: take('module.app-service-plan.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    skuName: enableScalability || enableRedundancy ? 'P1v4' : 'B3'
    skuCapacity: enableScalability ? 3 : 1
    zoneRedundant: enableRedundancy
    diagnosticSettings: monitoringDiagnosticSettings
  }
}

module webSite './modules/compute/app-service.bicep' = {
  name: take('module.app-service-frontend.${solutionName}', 64)
  params: {
    solutionName: 'app-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    serverFarmResourceId: webServerFarm.outputs.resourceId
    linuxFxVersion: 'DOCKER|${frontendContainerRegistryHostname}/${frontendContainerImageName}:${frontendContainerImageTag}'
    appSettings: {
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
      DOCKER_REGISTRY_SERVER_URL: 'https://${frontendContainerRegistryHostname}'
      WEBSITES_PORT: '3000'
      WEBSITES_CONTAINER_START_TIME_LIMIT: '1800'
      BACKEND_API_URL: 'https://${containerApp.outputs.fqdn}'
      AUTH_ENABLED: 'false'
      PROXY_API_REQUESTS: enablePrivateNetworking ? 'true' : 'false'
    }
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webserverfarmSubnetResourceId : ''
    publicNetworkAccess: 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
  }
}

// ============================================================================
// Role Assignments
// ============================================================================

module role_assignments_identity './modules/identity/role-assignments.bicep' = {
  name: take('module.role-assignments.identity.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    useExistingAIProject: useExistingAIProject
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    aiProjectPrincipalId: aiFoundryAiProjectPrincipalId
    aiSearchPrincipalId: ai_search.outputs.identityPrincipalId
    userAssignedManagedIdentityPrincipalId: managed_identity.outputs.principalId
    aiFoundryResourceId: !useExistingAIProject ? aiFoundryResourceId : ''
    aiSearchResourceId: ai_search.outputs.resourceId
    storageAccountResourceId: storage_account.outputs.resourceId
    cosmosDbAccountName: cosmosDBModule.outputs.name
    deployerPrincipalId: deployingUserPrincipalId
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The resource group the resources were deployed into.')
output resourceGroupName string = resourceGroup().name

@description('The default url of the website to connect to the Multi-Agent Custom Automation Engine solution.')
output webSiteDefaultHostname string = webSite.outputs.defaultHostname

output AZURE_STORAGE_BLOB_URL string = storage_account.outputs.serviceEndpoints.blob
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccountName
output AZURE_AI_SEARCH_ENDPOINT string = ai_search.outputs.endpoint
output AZURE_AI_SEARCH_NAME string = ai_search.outputs.name

output COSMOSDB_ENDPOINT string = cosmosDBModule.outputs.endpoint
output COSMOSDB_DATABASE string = cosmosDbDatabaseName
output COSMOSDB_CONTAINER string = cosmosDbDatabaseMemoryContainerName
output AZURE_OPENAI_ENDPOINT string = aiFoundryOpenAIEndpoint
output AZURE_OPENAI_DEPLOYMENT_NAME string = gptModelName
output AZURE_OPENAI_RAI_DEPLOYMENT_NAME string = gpt4_1ModelName
output AZURE_OPENAI_API_VERSION string = azureOpenaiAPIVersion
output AZURE_AI_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_AI_RESOURCE_GROUP string = resourceGroup().name
output AZURE_AI_PROJECT_NAME string = aiFoundryAiProjectName
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = gptModelName
output APP_ENV string = 'Prod'
output AI_FOUNDRY_RESOURCE_ID string = aiFoundryResourceId
output COSMOSDB_ACCOUNT_NAME string = cosmosDbResourceName
output AZURE_SEARCH_ENDPOINT string = ai_search.outputs.endpoint
output AZURE_CLIENT_ID string = managed_identity.outputs.clientId
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_COGNITIVE_SERVICES string = 'https://cognitiveservices.azure.com/.default'
output ORCHESTRATOR_MODEL_NAME string = gptReasoningModelName
output MCP_SERVER_NAME string = 'MacaeMcpServer'
output MCP_SERVER_DESCRIPTION string = 'MCP server with greeting, HR, and planning tools'
output SUPPORTED_MODELS string = string(supportedModels)
output BACKEND_URL string = 'https://${containerApp.outputs.fqdn}'
output AZURE_AI_PROJECT_ENDPOINT string = aiFoundryAiProjectEndpoint
output AZURE_AI_AGENT_ENDPOINT string = aiFoundryAiProjectEndpoint

output AI_SERVICE_NAME string = aiFoundryAiServicesResourceName

output AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER string = storageContainerNameRetailCustomer
output AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER string = storageContainerNameRetailOrder
output AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY string = storageContainerNameRFPSummary
output AZURE_STORAGE_CONTAINER_NAME_RFP_RISK string = storageContainerNameRFPRisk
output AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE string = storageContainerNameRFPCompliance
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY string = storageContainerNameContractSummary
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK string = storageContainerNameContractRisk
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE string = storageContainerNameContractCompliance
output AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER string = aiSearchIndexNameForRetailCustomer
output AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER string = aiSearchIndexNameForRetailOrder
output AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY string = aiSearchIndexNameForRFPSummary
output AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK string = aiSearchIndexNameForRFPRisk
output AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE string = aiSearchIndexNameForRFPCompliance
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY string = aiSearchIndexNameForContractSummary
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK string = aiSearchIndexNameForContractRisk
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE string = aiSearchIndexNameForContractCompliance

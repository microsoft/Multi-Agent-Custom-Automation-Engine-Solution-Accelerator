// ============================================================================
// main.bicep — Orchestrator
// Description: Pure orchestrator for Agentic Applications for UDF
//              All resource names are derived from params — no hardcoded names.
//              This file only calls modules; no inline resource definitions.
//              Supports WAF-aligned deployment via feature flags.
// ============================================================================
targetScope = 'resourceGroup'

// ============================================================================
// Parameters — Core
// ============================================================================

@minLength(3)
@maxLength(20)
@description('Optional. A unique application/solution name used as base for all resource naming.')
param solutionName string = 'agenticappudf'

@maxLength(5)
@description('Optional. A unique text suffix appended to resource names for uniqueness.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@description('Optional. Primary Azure region for resource deployment.')
param location string = resourceGroup().location

@description('Optional. Secondary location for database resources.')
param secondaryLocation string = 'eastus2'

@description('Optional. Tags to apply to all resources.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for AVM modules.')
param enableTelemetry bool = true

// ============================================================================
// Parameters — WAF Feature Flags
// ============================================================================

@description('Optional. Enable monitoring for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

// ============================================================================
// Parameters — VM (applicable when enablePrivateNetworking = true)
// ============================================================================

@secure()
@description('Optional. The user name for the administrator account of the virtual machine. Allows to customize credentials if `enablePrivateNetworking` is set to true.')
param vmAdminUsername string?

@secure()
@description('Optional. The password for the administrator account of the virtual machine. Allows to customize credentials if `enablePrivateNetworking` is set to true.')
param vmAdminPassword string?

@description('Optional. The size of the virtual machine. Defaults to Standard_D2s_v5.')
param vmSize string = 'Standard_D2s_v5'

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@allowed([
  'australiaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'japaneast'
  'swedencentral'
  'uksouth'
  'westus'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1-mini,100'
      'OpenAI.GlobalStandard.text-embedding-3-small,80'
    ]
  }
})
@description('Required. Location for AI Services and model deployments.')
param azureAiServiceLocation string

@description('Optional. Location for AI Search service deployment.')
param searchServiceLocation string = location

@allowed(['Standard', 'GlobalStandard'])
@description('Optional. GPT model deployment type.')
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy.')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the GPT model to deploy.')
param gptModelVersion string = '2025-04-14'

@minValue(10)
@description('Optional. Capacity of the GPT deployment (TPM in thousands).')
param gptDeploymentCapacity int = 150

@description('Optional. Name of the embedding model to deploy.')
@allowed(['text-embedding-3-small'])
param embeddingModel string = 'text-embedding-3-small'

@minValue(10)
@description('Optional. Capacity of the embedding model deployment.')
param embeddingDeploymentCapacity int = 80

@description('Optional. Azure OpenAI API version.')
param azureOpenaiAPIVersion string = '2025-01-01-preview'

@description('Optional. Azure AI Agent API version.')
param azureAiAgentApiVersion string = '2025-05-01'

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. Docker image tag for app deployments.')
param imageTag string = 'latest_v2'

@description('Optional. Name of the Azure Container Registry.')
param containerRegistryName string = 'dataagentscontainerreg'

@allowed(['python', 'dotnet'])
@description('Optional. Backend runtime stack.')
param backendRuntimeStack string = 'python'

@allowed(['F1', 'D1', 'B1', 'B2', 'B3', 'S1', 'S2', 'S3', 'P1', 'P2', 'P3', 'P1v3', 'P1v4'])
@description('Optional. App Service Plan SKU.')
param appServicePlanSku string = 'B2'

// ============================================================================
// Parameters — Feature Flags
// ============================================================================

@description('Optional. Deploy application components (API, Frontend, Cosmos DB).')
param deployApp bool = true

@description('Optional. Enable chat history storage.')
param useChatHistoryEnabled bool = true

@description('Optional. Enable user access token forwarding.')
param useUserAccessToken bool = false

// ============================================================================
// Parameters — Fabric Capacity
// ============================================================================

@description('Optional. Set to true to auto-create a Fabric workspace during post-provision. When false, capacity creation is skipped.')
param createFabricWorkspace bool = false

@description('Optional. Name of an existing Fabric capacity to reuse. If empty, a new capacity is auto-created when conditions are met.')
param azureFabricCapacityName string = ''

@allowed([
  'F2'
  'F4'
  'F8'
  'F16'
  'F32'
  'F64'
  'F128'
  'F256'
  'F512'
  'F1024'
  'F2048'
])
@description('Optional. SKU tier of the Fabric capacity resource.')
param fabricCapacitySku string = 'F2'

@description('Optional. Additional user/service principal object IDs to assign as Fabric Capacity admins.')
param fabricAdminMembers array = []

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics workspace (empty = create new).')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project (empty = create new).')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Parameters — Identity
// ============================================================================

@allowed(['User', 'ServicePrincipal'])
@description('Optional. Principal type of the deploying user.')
param deployingUserPrincipalType string = 'User'

// ============================================================================
// Parameters — App Configuration
// ============================================================================

@description('Optional. Primary title in the web app header.')
param appTitlePrimary string = 'Contoso'

@description('Optional. Secondary title in the web app header.')
param appTitleSecondary string = '| Unified Data Analysis Agents'

// ============================================================================
// Variables
// ============================================================================

var solutionSuffix = toLower(trim(replace(replace(replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''), ' ', ''), '*', '')))
var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId
var createdBy = contains(deployerInfo, 'userPrincipalName') ? split(deployerInfo.userPrincipalName, '@')[0] : deployerInfo.objectId
var shouldDeployApp = deployApp
var useExistingAIProject = !empty(existingFoundryProjectResourceId)
var useChatHistoryEnabledSetting = useChatHistoryEnabled ? 'True' : 'False'
var useUserAccessTokenSetting = useUserAccessToken ? 'True' : 'False'

// Fabric Capacity: create when createFabricWorkspace=true and no existing capacity provided
var useExistingFabricCapacity = !empty(azureFabricCapacityName)
var shouldCreateFabricCapacity = createFabricWorkspace && !useExistingFabricCapacity
var fabricCapacityResourceName = useExistingFabricCapacity ? azureFabricCapacityName : 'fc${solutionSuffix}'
var fabricCapacityDefaultAdmins = contains(deployerInfo, 'userPrincipalName')
  ? [deployerInfo.userPrincipalName]
  : [deployerInfo.objectId]
var fabricTotalAdminMembers = union(fabricCapacityDefaultAdmins, fabricAdminMembers)

// Tags: merge caller-supplied tags with standard metadata (matching old infra)
var existingTags = resourceGroup().tags ?? {}
var resourceTags = union(existingTags, tags, {
  TemplateName: 'Unified Data Analysis Agents'
  CreatedBy: createdBy
  DeploymentName: deployment().name
  Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
})

// WAF: Region pairs for redundancy (Log Analytics replication)
var replicaRegionPairs = {
  australiaeast: 'australiasoutheast'
  eastus: 'centralus'
  eastus2: 'centralus'
  francecentral: 'westeurope'
  japaneast: 'eastasia'
  swedencentral: 'northeurope'
  uksouth: 'westeurope'
  westus: 'centralus'
  westus3: 'centralus'
}
var replicaLocation = replicaRegionPairs[location]

// WAF: Region pairs for Cosmos DB zone-redundant HA
var cosmosDbHaRegionPairs = {
  australiaeast: 'uksouth'
  eastus: 'centralus'
  eastus2: 'centralus'
  francecentral: 'westeurope'
  japaneast: 'australiaeast'
  swedencentral: 'northeurope'
  uksouth: 'westeurope'
  westus: 'centralus'
  westus3: 'centralus'
}
var cosmosDbHaLocation = cosmosDbHaRegionPairs[location]

// WAF: Diagnostic settings helper — reused across modules
var monitoringDiagnosticSettings = enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : []

// WAF: Private DNS zones for private endpoints
var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.documents.azure.com'
  'privatelink.blob.core.windows.net'
  'privatelink.search.windows.net'
  'privatelink.database.windows.net'
]
var dnsZoneIndex = {
  cognitiveServices: 0
  openAI: 1
  aiFoundry: 2
  cosmosDb: 3
  blob: 4
  search: 5
  sqlServer: 6
}

// Resource naming (parameterized — no abbreviations.json dependency)
// Resource names for generic modules are now derived inside each module from solutionName/solutionSuffix.

// Model deployments configuration
var aiModelDeployments = [
  {
    name: gptModelName
    model: gptModelName
    sku: { name: deploymentType, capacity: gptDeploymentCapacity }
    version: gptModelVersion
    raiPolicyName: 'Microsoft.Default'
  }
  {
    name: embeddingModel
    model: embeddingModel
    sku: { name: 'GlobalStandard', capacity: embeddingDeploymentCapacity }
    version: '1'
    raiPolicyName: 'Microsoft.Default'
  }
]

// ============================================================================
// Resource Group Tags (matching old infra)
// ============================================================================

resource resourceGroupTags 'Microsoft.Resources/tags@2024-11-01' = {
  name: 'default'
  properties: {
    tags: resourceTags
  }
}

// ============================================================================
// Module: Fabric Capacity
// ============================================================================

module fabricCapacity './modules/fabric/fabric-capacity.bicep' = if (shouldCreateFabricCapacity) {
  name: take('module.fabric-capacity.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    skuName: fabricCapacitySku
    adminMembers: fabricTotalAdminMembers
    tags: resourceTags
    enableTelemetry: enableTelemetry
  }
}

// ============================================================================
// Module: Monitoring
// ============================================================================

var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)

// Existing workspace reference (for cross-subscription support)
resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' existing = if (useExistingLogAnalytics) {
  name: split(existingLogAnalyticsWorkspaceId, '/')[8]
  scope: resourceGroup(split(existingLogAnalyticsWorkspaceId, '/')[2], split(existingLogAnalyticsWorkspaceId, '/')[4])
}

module log_analytics './modules/monitoring/log-analytics.bicep' = if (enableMonitoring && !useExistingLogAnalytics) {
  name: take('module.log-analytics.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    retentionInDays: 365
    publicNetworkAccessForIngestion: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    publicNetworkAccessForQuery: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    enableReplication: enableRedundancy
    replicationLocation: enableRedundancy ? replicaLocation : ''
    dailyQuotaGb: enableRedundancy ? '150' : ''
    dataSources: enablePrivateNetworking ? [
      {
        tags: tags
        eventLogName: 'Application'
        eventTypes: [{ eventType: 'Error' }, { eventType: 'Warning' }, { eventType: 'Information' }]
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
    ] : []
  }
}

// Resolve workspace resource ID and name — existing or new
var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace.id
  : (enableMonitoring ? log_analytics!.outputs.resourceId : '')
var logAnalyticsWorkspaceName = useExistingLogAnalytics
  ? split(existingLogAnalyticsWorkspaceId, '/')[8]
  : (enableMonitoring ? log_analytics!.outputs.name : '')

module app_insights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: tags
    enableTelemetry: enableTelemetry
    workspaceResourceId: logAnalyticsWorkspaceResourceId
    retentionInDays: 365
    disableIpMasking: false
  }
}

// ============================================================================
// Module: Networking (WAF — conditional on enablePrivateNetworking)
// ============================================================================

module virtualNetwork './modules/networking/virtual-network.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-network.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    addressPrefixes: ['10.0.0.0/8']
    logAnalyticsWorkspaceId: logAnalyticsWorkspaceResourceId
    resourceSuffix: solutionSuffix
  }
}

// Bastion Host — secure access to jumpbox VM
module bastionHost './modules/networking/bastion-host.bicep' = if (enablePrivateNetworking) {
  name: take('module.bastion-host.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
    publicIPDiagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
  }
}

// WAF: Maintenance Configuration for VM patching
module maintenanceConfiguration './modules/compute/maintenance-configuration.bicep' = if (enablePrivateNetworking) {
  name: take('module.maintenance-configuration.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

// WAF: Data Collection Rules for VM monitoring
var dataCollectionRulesLocation = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.location
  : (enableMonitoring ? log_analytics!.outputs.location : location)
module windowsVmDataCollectionRules './modules/monitoring/data-collection-rule.bicep' = if (enablePrivateNetworking && enableMonitoring) {
  name: take('module.data-collection-rule.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: dataCollectionRulesLocation
    tags: tags
    enableTelemetry: enableTelemetry
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
  }
}

// WAF: Proximity Placement Group for VM
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

// Jumpbox VM — administration access when private networking is enabled
module virtualMachine './modules/compute/virtual-machine.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtual-machine.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    vmSize: vmSize
    availabilityZone: virtualMachineAvailabilityZone
    adminUsername: vmAdminUsername ?? 'JumpboxAdmin'
    adminPassword: vmAdminPassword ?? 'JumpboxAdminP@ssw0rd1234!'
    subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
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

// Private DNS Zones — one per service, linked to VNet
@batchSize(5)
module privateDnsZoneDeployments './modules/networking/private-dns-zone.bicep' = [
  for (zone, i) in privateDnsZones: if (enablePrivateNetworking) {
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
  }
]

// ============================================================================
// Module: AI Services (conditional — skip if using existing project)
// ============================================================================

// Existing AI Foundry reference (for cross-subscription support when using existing project)
var aiFoundryResourceGroupName = useExistingAIProject
  ? split(existingFoundryProjectResourceId, '/')[4]
  : resourceGroup().name
var aiFoundrySubscriptionId = useExistingAIProject
  ? split(existingFoundryProjectResourceId, '/')[2]
  : subscription().subscriptionId
var aiFoundryResourceName = useExistingAIProject
  ? split(existingFoundryProjectResourceId, '/')[8]
  : ai_foundry_project!.outputs.name
var aiProjectResourceName = useExistingAIProject
  ? (length(split(existingFoundryProjectResourceId, '/')) > 10 ? split(existingFoundryProjectResourceId, '/')[10] : '')
  : ai_foundry_project!.outputs.projectName

// Construct endpoints from existing resource ID
// Expected format: /subscriptions/.../providers/Microsoft.CognitiveServices/accounts/{account}/projects/{project}
var existingHasProjectSegment = useExistingAIProject && length(split(existingFoundryProjectResourceId, '/')) > 10
var existingOpenAIEndpoint = useExistingAIProject
  ? format('https://{0}.openai.azure.com/', split(existingFoundryProjectResourceId, '/')[8])
  : ''
var existingProjectEndpoint = existingHasProjectSegment
  ? format('https://{0}.services.ai.azure.com/api/projects/{1}', split(existingFoundryProjectResourceId, '/')[8], split(existingFoundryProjectResourceId, '/')[10])
  : ''


// Reference existing AI Foundry project (identity only)
module existing_project_setup './modules/ai/existing-project-setup.bicep' = if (useExistingAIProject) {
  name: take('module.existing-project-setup.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    name: aiFoundryResourceName
    projectName: aiProjectResourceName
  }
}

// Deploy new AI Services account + AI Foundry project (no connections, no deployments)
module ai_foundry_project './modules/ai/ai-foundry-project.bicep' = if (!useExistingAIProject) {
  name: take('module.ai-foundry-project.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: tags
    enableTelemetry: enableTelemetry
    // Temporarily public — AI Search Knowledge Base needs to call the AI Services model endpoint for answer synthesis.
    publicNetworkAccess: 'Enabled'
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
    ]
  }
}

// AI Search connection (single call for both existing and new paths)
module foundry_search_connection './modules/ai/ai-foundry-connection.bicep' = {
  name: take('module.foundry-search-conn.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryResourceName
    projectName: aiProjectResourceName
    category: 'CognitiveSearch'
    target: ai_search!.outputs.endpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: ai_search!.outputs.resourceId
    }
  }
}

// Storage Blob connection (single call for both existing and new paths)
module foundry_storage_connection './modules/ai/ai-foundry-connection.bicep' = {
  name: take('module.foundry-storage-conn.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryResourceName
    projectName: aiProjectResourceName
    category: 'AzureBlob'
    target: storage_account!.outputs.blobEndpoint
    authType: 'AAD'
    metadata: {
      ResourceId: storage_account!.outputs.resourceId
      AccountName: storage_account!.outputs.name
      ContainerName: 'default'
    }
  }
}

// Application Insights connection (skip if using existing Foundry project which already has one)
module foundry_appi_connection './modules/ai/ai-foundry-connection.bicep' = if (enableMonitoring && !useExistingAIProject) {
  name: take('module.foundry-appi-conn.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryResourceName
    projectName: aiProjectResourceName
    category: 'AppInsights'
    target: app_insights!.outputs.resourceId
    authType: 'ApiKey'
    isDefault: true
    credentialsKey: app_insights!.outputs.instrumentationKey
    metadata: {
      ApiType: 'Azure'
      ResourceId: app_insights!.outputs.resourceId
    }
  }
}

// Model deployments (single loop for both existing and new paths)
@batchSize(1)
module model_deployments './modules/ai/ai-foundry-model-deployment.bicep' = [for (deployment, i) in aiModelDeployments: {
  name: take('module.model-deployment-${i}.${solutionName}', 64)
  scope: resourceGroup(aiFoundrySubscriptionId, aiFoundryResourceGroupName)
  params: {
    aiServicesAccountName: aiFoundryResourceName
    deploymentName: deployment.name
    modelName: deployment.model
    modelVersion: deployment.version
    raiPolicyName: deployment.raiPolicyName
    skuName: deployment.sku.name
    skuCapacity: deployment.sku.capacity
  }
}]

// Separate PE for AI Foundry to avoid AccountProvisioningStateInvalid race condition
module aifoundry_private_endpoint './modules/networking/private-endpoint.bicep' = if (!useExistingAIProject && enablePrivateNetworking) {
  name: take('module.pe-ai-foundry.${solutionName}', 64)
  dependsOn: [privateDnsZoneDeployments]
  params: {
    name: 'pep-aif-${solutionSuffix}'
    location: location
    tags: tags
    subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
    privateLinkServiceConnections: [
      {
        name: 'pep-aif-${solutionSuffix}'
        properties: {
          privateLinkServiceId: ai_foundry_project!.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          name: 'dns-zone-cognitiveservices'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
        }
        {
          name: 'dns-zone-openai'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.openAI]!.outputs.resourceId
        }
        {
          name: 'dns-zone-aifoundry'
          privateDnsZoneResourceId: privateDnsZoneDeployments[dnsZoneIndex.aiFoundry]!.outputs.resourceId
        }
      ]
    }
  }
}

module ai_search './modules/ai/ai-search.bicep' = {
  name: take('module.ai-search.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: searchServiceLocation
    tags: tags
    enableTelemetry: enableTelemetry
    // Temporarily public — Foundry Agent runtime runs outside the VNET and cannot resolve private DNS for AI Search.
    publicNetworkAccess: 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    roleAssignments: [
      {
        roleDefinitionIdOrName: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
      {
        roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
    ]
    // Temporarily no private endpoint — Foundry Agent cannot resolve private DNS for AI Search.
    privateEndpoints: []
  }
}

// ============================================================================
// Module: Data 
// ============================================================================

module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: tags
    enableTelemetry: enableTelemetry
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    containers: [
      { name: 'default', publicAccess: 'None' }
    ]
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
        principalId: deployingUserPrincipalId
        principalType: deployingUserPrincipalType
      }
    ]
    enablePrivateNetworking: enablePrivateNetworking
    privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''
    privateDnsZoneResourceIds: enablePrivateNetworking ? [
      privateDnsZoneDeployments[dnsZoneIndex.blob]!.outputs.resourceId
    ] : []
  }
}

module cosmosDBModule './modules/data/cosmos-db-nosql.bicep' = if (shouldDeployApp) {
  name: take('module.cosmos-db-nosql.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    databaseName: 'db_conversation_history'
    containers: [
      { name: 'conversations', partitionKeyPath: '/userId' }
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
// Module: Compute
// ============================================================================

module hostingplan './modules/compute/app-service-plan.bicep' = if (shouldDeployApp) {
  name: take('module.app-service-plan.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    skuName: (enableScalability || enableRedundancy) ? 'P1v4' : appServicePlanSku
    skuCapacity: enableScalability ? 3 : 1
    zoneRedundant: enableRedundancy
    diagnosticSettings: monitoringDiagnosticSettings
  }
}

// Backend API (Python)
module backend_docker './modules/compute/app-service.bicep' = if (shouldDeployApp && backendRuntimeStack == 'python') {
  name: take('module.app-service-pybackend.${solutionName}', 64)
  params: {
    solutionName: 'api-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    serverFarmResourceId: hostingplan!.outputs.resourceId
    linuxFxVersion: 'DOCKER|${containerRegistryName}.azurecr.io/da-api:${imageTag}'
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webserverfarmSubnetResourceId : ''
    publicNetworkAccess: 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    appSettings: {
      AZURE_ENV_GPT_MODEL_NAME: gptModelName
      AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME: embeddingModel
      AZURE_OPENAI_ENDPOINT: useExistingAIProject ? existingOpenAIEndpoint : ai_foundry_project!.outputs.endpoint
      AZURE_ENV_OPENAI_API_VERSION: azureOpenaiAPIVersion
      AZURE_OPENAI_RESOURCE: useExistingAIProject ? aiFoundryResourceName : ai_foundry_project!.outputs.name
      AZURE_AI_AGENT_ENDPOINT: useExistingAIProject ? existingProjectEndpoint : ai_foundry_project!.outputs.projectEndpoint
      AZURE_AI_AGENT_API_VERSION: azureAiAgentApiVersion
      AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: gptModelName
      USE_CHAT_HISTORY_ENABLED: useChatHistoryEnabledSetting
      AZURE_COSMOSDB_ACCOUNT: shouldDeployApp ? cosmosDBModule!.outputs.name : ''
      AZURE_COSMOSDB_CONVERSATIONS_CONTAINER: 'conversations'
      AZURE_COSMOSDB_DATABASE: 'db_conversation_history'
      AZURE_COSMOSDB_ENABLE_FEEDBACK: 'True'
      AZURE_SQLDB_USER_MID: ''
      API_UID: ''
      AZURE_AI_SEARCH_ENDPOINT: ai_search.outputs.endpoint
      AZURE_AI_SEARCH_INDEX: 'knowledge_index'
      AZURE_AI_SEARCH_CONNECTION_NAME: foundry_search_connection.outputs.connectionName
      USE_AI_PROJECT_CLIENT: 'True'
      DISPLAY_CHART_DEFAULT: 'False'
      APPLICATIONINSIGHTS_CONNECTION_STRING: enableMonitoring ? app_insights!.outputs.connectionString : ''
      SOLUTION_NAME: solutionSuffix
      USE_USER_ACCESS_TOKEN: useUserAccessTokenSetting
      APP_ENV: 'Prod'
      AZURE_BASIC_LOGGING_LEVEL: 'INFO'
      AZURE_PACKAGE_LOGGING_LEVEL: 'WARNING'
      AZURE_LOGGING_PACKAGES: ''
      AGENT_NAME_CHAT: ''
      AGENT_NAME_TITLE: ''
      FABRIC_SQL_DATABASE: ''
      FABRIC_SQL_SERVER: ''
      FABRIC_SQL_CONNECTION_STRING: ''
    }
  }
}

// Backend API (C#)
module backend_csapi_docker './modules/compute/app-service.bicep' = if (shouldDeployApp && backendRuntimeStack == 'dotnet') {
  name: take('module.app-service-csbackend.${solutionName}', 64)
  params: {
    solutionName: 'api-cs-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    serverFarmResourceId: hostingplan!.outputs.resourceId
    linuxFxVersion: 'DOCKER|${containerRegistryName}.azurecr.io/da-api-dotnet:${imageTag}'
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webserverfarmSubnetResourceId : ''
    publicNetworkAccess: 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    appSettings: {
      AZURE_ENV_GPT_MODEL_NAME: gptModelName
      AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME: embeddingModel
      AZURE_OPENAI_ENDPOINT: useExistingAIProject ? existingOpenAIEndpoint : ai_foundry_project!.outputs.endpoint
      AZURE_ENV_OPENAI_API_VERSION: azureOpenaiAPIVersion
      AZURE_OPENAI_RESOURCE: useExistingAIProject ? aiFoundryResourceName : ai_foundry_project!.outputs.name
      AZURE_AI_AGENT_ENDPOINT: useExistingAIProject ? existingProjectEndpoint : ai_foundry_project!.outputs.projectEndpoint
      AZURE_AI_AGENT_API_VERSION: azureAiAgentApiVersion
      AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: gptModelName
      USE_CHAT_HISTORY_ENABLED: useChatHistoryEnabledSetting
      AZURE_COSMOSDB_ACCOUNT: shouldDeployApp ? cosmosDBModule!.outputs.name : ''
      AZURE_COSMOSDB_CONVERSATIONS_CONTAINER: 'conversations'
      AZURE_COSMOSDB_DATABASE: 'db_conversation_history'
      AZURE_COSMOSDB_ENABLE_FEEDBACK: 'True'
      API_UID: ''
      AZURE_AI_SEARCH_ENDPOINT: ai_search.outputs.endpoint
      AZURE_AI_SEARCH_INDEX: 'knowledge_index'
      AZURE_AI_SEARCH_CONNECTION_NAME: foundry_search_connection.outputs.connectionName
      USE_AI_PROJECT_CLIENT: 'True'
      DISPLAY_CHART_DEFAULT: 'False'
      APPLICATIONINSIGHTS_CONNECTION_STRING: enableMonitoring ? app_insights!.outputs.connectionString : ''
      SOLUTION_NAME: solutionSuffix
      APP_ENV: 'Prod'
      AGENT_NAME_CHAT: ''
      AGENT_NAME_TITLE: ''
      FABRIC_SQL_DATABASE: ''
      FABRIC_SQL_SERVER: ''
      FABRIC_SQL_CONNECTION_STRING: ''
    }
  }
}

// Frontend
module frontend_docker './modules/compute/app-service.bicep' = if (shouldDeployApp) {
  name: take('module.app-service-frontend.${solutionName}', 64)
  params: {
    solutionName: 'app-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    serverFarmResourceId: hostingplan!.outputs.resourceId
    linuxFxVersion: 'DOCKER|${containerRegistryName}.azurecr.io/da-app:${imageTag}'
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webserverfarmSubnetResourceId : ''
    publicNetworkAccess: 'Enabled'
    diagnosticSettings: monitoringDiagnosticSettings
    appSettings: {
      APP_API_BASE_URL: shouldDeployApp ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.appUrl : backend_csapi_docker!.outputs.appUrl) : ''
      CHAT_LANDING_TEXT: ''
      APP_TITLE_PRIMARY: appTitlePrimary
      APP_TITLE_SECONDARY: appTitleSecondary
      PROXY_API_REQUESTS: enablePrivateNetworking ? 'true' : 'false'
    }
  }
}

// ============================================================================
// Module: Role Assignments (centralized)
// ============================================================================

module role_assignments './modules/identity/role-assignments.bicep' = {
  name: take('module.role-assignments.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    aiProjectPrincipalId: (!useExistingAIProject) ? ai_foundry_project!.outputs.projectIdentityPrincipalId : ''
    aiSearchPrincipalId: ai_search.outputs.identityPrincipalId
    aiSearchResourceId: ai_search.outputs.resourceId
    storageAccountResourceId: storage_account.outputs.resourceId
    cosmosDbAccountName: shouldDeployApp ? cosmosDBModule!.outputs.name : ''
    backendAppServicePrincipalId: shouldDeployApp
      ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.identityPrincipalId : backend_csapi_docker!.outputs.identityPrincipalId)
      : ''
    aiFoundryResourceId: !useExistingAIProject ? ai_foundry_project!.outputs.resourceId : ''
    useExistingAIProject: useExistingAIProject
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    existingAiProjectPrincipalId: useExistingAIProject ? existing_project_setup!.outputs.aiProjectPrincipalId : ''
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Solution suffix used for naming resources.')
output SOLUTION_NAME string = solutionSuffix

@description('Name of the deployed resource group.')
output RESOURCE_GROUP_NAME string = resourceGroup().name

@description('WAF deployment type.')
output DEPLOYMENT_TYPE string = enablePrivateNetworking ? 'WAF' : 'Non-WAF'

@description('Cosmos DB account name.')
output AZURE_COSMOSDB_ACCOUNT string = shouldDeployApp ? cosmosDBModule!.outputs.name : ''

@description('Cosmos DB container name.')
output AZURE_COSMOSDB_CONVERSATIONS_CONTAINER string = 'conversations'

@description('Cosmos DB database name.')
output AZURE_COSMOSDB_DATABASE string = 'db_conversation_history'

@description('GPT model deployment name.')
output AZURE_ENV_GPT_MODEL_NAME string = gptModelName

@description('Azure OpenAI service endpoint URL.')
output AZURE_OPENAI_ENDPOINT string = !useExistingAIProject ? ai_foundry_project!.outputs.endpoint : existingOpenAIEndpoint

@description('Embedding model deployment name.')
output AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME string = embeddingModel

@description('Managed identity client ID for SQL auth.')
output AZURE_SQLDB_USER_MID string = ''

@description('Backend API managed identity client ID.')
output API_UID string = ''

@description('Azure AI Agent endpoint.')
output AZURE_AI_AGENT_ENDPOINT string = !useExistingAIProject ? ai_foundry_project!.outputs.projectEndpoint : existingProjectEndpoint

@description('Model deployment name for AI Agent.')
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = gptModelName

@description('Backend API App Service name.')
output API_APP_NAME string = shouldDeployApp ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.name : backend_csapi_docker!.outputs.name) : ''

@description('Backend API managed identity principal ID.')
output API_PID string = shouldDeployApp
  ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.identityPrincipalId : backend_csapi_docker!.outputs.identityPrincipalId)
  : ''

@description('Backend API managed identity display name.')
output MID_DISPLAY_NAME string = shouldDeployApp
  ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.name : backend_csapi_docker!.outputs.name)
  : ''

@description('Frontend web app resource name.')
output WEB_APP_NAME string = shouldDeployApp ? frontend_docker!.outputs.name : ''

@description('Frontend web application URL.')
output WEB_APP_URL string = shouldDeployApp ? frontend_docker!.outputs.appUrl : ''

@description('Azure AI Search endpoint.')
output AZURE_AI_SEARCH_ENDPOINT string = ai_search.outputs.endpoint

@description('Azure AI Search index name.')
output AZURE_AI_SEARCH_INDEX string = 'knowledge_index'

@description('Azure AI Search service name.')
output AZURE_AI_SEARCH_NAME string = ai_search.outputs.name

@description('Search data folder path.')
output SEARCH_DATA_FOLDER string = 'data/default/documents'

@description('AI Search connection name.')
output AZURE_AI_SEARCH_CONNECTION_NAME string = foundry_search_connection.outputs.connectionName

@description('AI Search connection ID.')
output AZURE_AI_SEARCH_CONNECTION_ID string = foundry_search_connection.outputs.connectionId

@description('AI Foundry project endpoint.')
output AZURE_AI_PROJECT_ENDPOINT string = !useExistingAIProject ? ai_foundry_project!.outputs.projectEndpoint : existingProjectEndpoint

@description('AI Foundry resource ID.')
output AI_FOUNDRY_RESOURCE_ID string = !useExistingAIProject ? ai_foundry_project!.outputs.resourceId : existingFoundryProjectResourceId

@description('AI Foundry project name.')
output AZURE_AI_PROJECT_NAME string = !useExistingAIProject ? ai_foundry_project!.outputs.projectName : (existingHasProjectSegment ? split(existingFoundryProjectResourceId, '/')[10] : '')

@description('AI Services resource name.')
output AI_SERVICE_NAME string = !useExistingAIProject ? ai_foundry_project!.outputs.name : aiFoundryResourceName

@description('AI Project identity principal ID.')
output FOUNDRY_PROJECT_PID string = !useExistingAIProject ? ai_foundry_project!.outputs.projectIdentityPrincipalId : ''

@description('Chat history enabled flag.')
output USE_CHAT_HISTORY_ENABLED string = useChatHistoryEnabledSetting

@description('Backend runtime stack.')
output BACKEND_RUNTIME_STACK string = backendRuntimeStack

@description('User access token forwarding flag.')
output USE_USER_ACCESS_TOKEN string = useUserAccessTokenSetting

@description('The resource ID of the Fabric capacity.')
output AZURE_FABRIC_CAPACITY_RESOURCE_ID string = createFabricWorkspace ? fabricCapacity.outputs.resourceId : ''

@description('The name of the Fabric capacity resource.')
output AZURE_FABRIC_CAPACITY_NAME string = createFabricWorkspace ? fabricCapacityResourceName : ''

@description('The identities assigned as Fabric Capacity Admin members.')
output FABRIC_ADMIN_MEMBERS array = shouldCreateFabricCapacity ? fabricTotalAdminMembers : []

@description('The unique solution suffix of the deployed resources.')
output SOLUTION_SUFFIX string = solutionSuffix

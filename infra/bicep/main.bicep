targetScope = 'resourceGroup'

metadata name = 'Multi-Agent Custom Automation Engine - Vanilla Bicep'
metadata description = 'Vanilla Bicep orchestrator for the Multi-Agent Custom Automation Engine accelerator. This deployment intentionally excludes WAF features such as private networking, scale-out, redundancy, bastion, and VM resources while keeping router-compatible outputs.'

@description('Optional. A unique application/solution name for all resources in this deployment. This should be 3-16 characters long.')
@minLength(3)
@maxLength(16)
param solutionName string = 'macae'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources.')
param solutionUniqueText string = take(uniqueString(subscription().id, resourceGroup().name, solutionName), 5)

@metadata({
  azd: {
    type: 'location'
  }
})
@description('Required. Azure region for app, data, and monitoring resources.')
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

@allowed(['australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus'])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1, 150'
      'OpenAI.GlobalStandard.o4-mini, 50'
      'OpenAI.GlobalStandard.gpt4.1-mini, 50'
    ]
  }
})
@description('Required. Location for Azure AI Services and Azure AI Foundry resources.')
param azureAiServiceLocation string

@description('Optional. Name of the default GPT model deployment.')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the default GPT model deployment.')
param gptModelVersion string = '2025-04-14'

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Deployment type for the default GPT model deployment.')
param deploymentType string = 'GlobalStandard'

@minValue(1)
@description('Optional. Capacity of the default GPT model deployment.')
param gptDeploymentCapacity int = 50

@description('Optional. Name of the RAI GPT model deployment.')
param gpt4_1ModelName string = 'gpt-4.1'

@description('Optional. Version of the RAI GPT model deployment.')
param gpt4_1ModelVersion string = '2025-04-14'

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Deployment type for the RAI GPT model deployment.')
param gpt4_1ModelDeploymentType string = 'GlobalStandard'

@minValue(1)
@description('Optional. Capacity of the RAI GPT model deployment.')
param gpt4_1ModelCapacity int = 150

@description('Optional. Name of the reasoning model deployment.')
param gptReasoningModelName string = 'o4-mini'

@description('Optional. Version of the reasoning model deployment.')
param gptReasoningModelVersion string = '2025-04-16'

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Deployment type for the reasoning model deployment.')
param gptReasoningModelDeploymentType string = 'GlobalStandard'

@minValue(1)
@description('Optional. Capacity of the reasoning model deployment.')
param gptReasoningModelCapacity int = 50

@description('Optional. Azure OpenAI API version.')
param azureOpenaiAPIVersion string = '2024-12-01-preview'

@description('Optional. Azure AI Agent API version.')
param azureAiAgentAPIVersion string = '2025-01-01-preview'

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

@description('Optional. Resource ID of an existing Log Analytics Workspace.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project.')
param existingFoundryProjectResourceId string = ''

@description('Optional. Enable or disable usage telemetry for this module.')
param enableTelemetry bool = true

@description('Optional. Enable or disable monitoring resources such as Application Insights.')
param enableMonitoring bool = true

@description('Optional. Enable or disable AI Search scalability.')
param enableScalability bool = false

@description('Optional. Additional tags to apply to deployed resources.')
param tags object = {}

@description('Optional. Blob container name for retail customer documents.')
param storageContainerNameRetailCustomer string = 'retail-dataset-customer'

@description('Optional. Blob container name for retail order documents.')
param storageContainerNameRetailOrder string = 'retail-dataset-order'

@description('Optional. Blob container name for RFP summary documents.')
param storageContainerNameRFPSummary string = 'rfp-summary-dataset'

@description('Optional. Blob container name for RFP risk documents.')
param storageContainerNameRFPRisk string = 'rfp-risk-dataset'

@description('Optional. Blob container name for RFP compliance documents.')
param storageContainerNameRFPCompliance string = 'rfp-compliance-dataset'

@description('Optional. Blob container name for contract summary documents.')
param storageContainerNameContractSummary string = 'contract-summary-dataset'

@description('Optional. Blob container name for contract risk documents.')
param storageContainerNameContractRisk string = 'contract-risk-dataset'

@description('Optional. Blob container name for contract compliance documents.')
param storageContainerNameContractCompliance string = 'contract-compliance-dataset'

@description('Tag. Created by user name.')
param createdBy string = contains(deployer(), 'userPrincipalName')
  ? split(deployer().userPrincipalName, '@')[0]
  : deployer().objectId

var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId
var deployerPrincipalType = contains(deployerInfo, 'userPrincipalName') ? 'User' : 'ServicePrincipal'
var solutionLocation = location
var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))
var existingTags = resourceGroup().tags ?? {}
var allTags = union({
  'azd-env-name': solutionName
}, tags)

var useExistingAiFoundryAiProject = !empty(existingFoundryProjectResourceId)
var aiFoundryAiServicesSubscriptionId = useExistingAiFoundryAiProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var aiFoundryAiServicesResourceGroupName = useExistingAiFoundryAiProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name
var aiFoundryAiServicesResourceName = useExistingAiFoundryAiProject ? split(existingFoundryProjectResourceId, '/')[8] : 'aif-${solutionSuffix}'
var aiFoundryAiProjectResourceName = useExistingAiFoundryAiProject ? split(existingFoundryProjectResourceId, '/')[10] : 'proj-${solutionSuffix}'
var aiFoundryAiServicesResourceId = useExistingAiFoundryAiProject ? existing_project_setup!.outputs.aiFoundryResourceId : ai_foundry_project!.outputs.resourceId
var aiFoundryOpenAIEndpoint = 'https://${aiFoundryAiServicesResourceName}.openai.azure.com/'
var aiFoundryAiProjectEndpoint = 'https://${aiFoundryAiServicesResourceName}.services.ai.azure.com/api/projects/${aiFoundryAiProjectResourceName}'
var aiSearchConnectionName = 'aifp-srch-connection-${solutionSuffix}'
var aiStorageConnectionName = 'aifp-blob-connection-${solutionSuffix}'
var aiAppInsightsConnectionName = 'aifp-appi-connection-${solutionSuffix}'

var cosmosDbResourceName = 'cosmos-${solutionSuffix}'
var cosmosDbDatabaseName = 'macae'
var cosmosDbDatabaseMemoryContainerName = 'memory'
var cosmosDbDatabaseMemoryPartitionKey = '/session_id'

var frontendAppName = 'app-${solutionSuffix}'
var frontendAppUrl = 'https://${frontendAppName}.azurewebsites.net'
var appServicePlanName = 'asp-${solutionSuffix}'
var backendContainerAppName = 'ca-${solutionSuffix}'
var mcpContainerAppName = 'ca-mcp-${solutionSuffix}'
var storageAccountName = take('st${toLower(replace(solutionSuffix, '-', ''))}', 24)
var aiSearchServiceName = 'srch-${solutionSuffix}'

var aiSearchIndexNameForContractSummary = 'contract-summary-doc-index'
var aiSearchIndexNameForContractRisk = 'contract-risk-doc-index'
var aiSearchIndexNameForContractCompliance = 'contract-compliance-doc-index'
var aiSearchIndexNameForRetailCustomer = 'macae-retail-customer-index'
var aiSearchIndexNameForRetailOrder = 'macae-retail-order-index'
var aiSearchIndexNameForRFPSummary = 'macae-rfp-summary-index'
var aiSearchIndexNameForRFPRisk = 'macae-rfp-risk-index'
var aiSearchIndexNameForRFPCompliance = 'macae-rfp-compliance-index'

var mcpServerName = 'MacaeMcpServer'
var mcpServerDescription = 'MCP server with greeting, HR, and planning tools'
var supportedModels = '["o3","o4-mini","gpt-4.1","gpt-4.1-mini"]'
var aiAgentProjectConnectionString = '${aiFoundryAiServicesResourceName}.services.ai.azure.com;${aiFoundryAiServicesSubscriptionId};${aiFoundryAiServicesResourceGroupName};${aiFoundryAiProjectResourceName}'

var azureAIDeveloperRoleDefinitionId = '/subscriptions/${aiFoundryAiServicesSubscriptionId}/providers/Microsoft.Authorization/roleDefinitions/64702f94-c441-49e6-a78b-ef80e0188fee'
var cognitiveServicesOpenAIUserRoleDefinitionId = '/subscriptions/${aiFoundryAiServicesSubscriptionId}/providers/Microsoft.Authorization/roleDefinitions/5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource resourceGroupTags 'Microsoft.Resources/tags@2023-07-01' = {
  name: 'default'
  properties: {
    tags: union(
      existingTags,
      allTags,
      {
        TemplateName: 'MACAE'
        Type: 'Non-WAF'
        CreatedBy: createdBy
        DeploymentName: deployment().name
        SolutionSuffix: solutionSuffix
      }
    )
  }
}

var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)

#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2025-04-01' = if (enableTelemetry) {
  name: '46d3xbcp.ptn.sa-multiagentcustauteng.bicep.${substring(uniqueString(deployment().name, location), 0, 4)}'
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        telemetry: {
          type: 'String'
          value: 'Enabled'
        }
      }
    }
  }
}

module log_analytics './modules/monitoring/log-analytics.bicep' = if (!useExistingLogAnalytics) {
  name: take('module.log-analytics.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
    tags: allTags
  }
}

var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics ? existingLogAnalyticsWorkspaceId : log_analytics!.outputs.resourceId
var logAnalyticsWorkspaceName = useExistingLogAnalytics ? '' : log_analytics!.outputs.name

module app_insights './modules/monitoring/app-insights.bicep' = if (enableMonitoring) {
  name: take('module.app-insights.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
    tags: allTags
    workspaceResourceId: logAnalyticsWorkspaceResourceId
  }
}

module userAssignedIdentity './modules/identity/managed-identity.bicep' = {
  name: take('module.user-assigned-identity.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    identityName: 'id-${solutionSuffix}'
    location: solutionLocation
    tags: allTags
  }
}

module ai_foundry_project './modules/ai/ai-foundry-project.bicep' = if (!useExistingAiFoundryAiProject) {
  name: take('module.ai-foundry-project.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    solutionName: solutionSuffix
    name: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectResourceName
    location: azureAiServiceLocation
  }
}

module existing_project_setup './modules/ai/existing-project-setup.bicep' = if (useExistingAiFoundryAiProject) {
  name: take('module.existing-project-setup.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    name: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectResourceName
  }
}

var aiFoundryAiProjectPrincipalId = useExistingAiFoundryAiProject
  ? existing_project_setup!.outputs.aiProjectPrincipalId
  : ai_foundry_project!.outputs.projectIdentityPrincipalId

module gpt_model_deployment './modules/ai/ai-foundry-model-deployment.bicep' = {
  name: take('module.gpt-model-deployment.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  dependsOn: useExistingAiFoundryAiProject ? [existing_project_setup] : [ai_foundry_project!]
  params: {
    aiServicesAccountName: aiFoundryAiServicesResourceName
    deploymentName: gptModelName
    modelName: gptModelName
    modelVersion: gptModelVersion
    raiPolicyName: 'Microsoft.Default'
    skuName: deploymentType
    skuCapacity: gptDeploymentCapacity
  }
}

module gpt4_1_model_deployment './modules/ai/ai-foundry-model-deployment.bicep' = {
  name: take('module.gpt41-model-deployment.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  dependsOn: [gpt_model_deployment]
  params: {
    aiServicesAccountName: aiFoundryAiServicesResourceName
    deploymentName: gpt4_1ModelName
    modelName: gpt4_1ModelName
    modelVersion: gpt4_1ModelVersion
    raiPolicyName: 'Microsoft.Default'
    skuName: gpt4_1ModelDeploymentType
    skuCapacity: gpt4_1ModelCapacity
  }
}

module reasoning_model_deployment './modules/ai/ai-foundry-model-deployment.bicep' = {
  name: take('module.reasoning-model-deployment.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  dependsOn: [gpt4_1_model_deployment]
  params: {
    aiServicesAccountName: aiFoundryAiServicesResourceName
    deploymentName: gptReasoningModelName
    modelName: gptReasoningModelName
    modelVersion: gptReasoningModelVersion
    raiPolicyName: 'Microsoft.Default'
    skuName: gptReasoningModelDeploymentType
    skuCapacity: gptReasoningModelCapacity
  }
}

module ai_search './modules/ai/ai-search.bicep' = {
  name: take('module.ai-search.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
    tags: allTags
    skuName: enableScalability ? 'standard' : 'basic'
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'Default'
    semanticSearch: 'free'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
    tags: allTags
    containers: [
      {
        name: storageContainerNameRetailCustomer
        publicAccess: 'None'
      }
      {
        name: storageContainerNameRetailOrder
        publicAccess: 'None'
      }
      {
        name: storageContainerNameRFPSummary
        publicAccess: 'None'
      }
      {
        name: storageContainerNameRFPRisk
        publicAccess: 'None'
      }
      {
        name: storageContainerNameRFPCompliance
        publicAccess: 'None'
      }
      {
        name: storageContainerNameContractSummary
        publicAccess: 'None'
      }
      {
        name: storageContainerNameContractRisk
        publicAccess: 'None'
      }
      {
        name: storageContainerNameContractCompliance
        publicAccess: 'None'
      }
    ]
  }
}

resource storageAccountResource 'Microsoft.Storage/storageAccounts@2025-08-01' existing = {
  name: storageAccountName
}

module cosmosDBModule './modules/data/cosmos-db-nosql.bicep' = {
  name: take('module.cosmos-db.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    name: cosmosDbResourceName
    location: solutionLocation
    tags: allTags
    databaseName: cosmosDbDatabaseName
    containers: [
      {
        name: cosmosDbDatabaseMemoryContainerName
        partitionKeyPath: cosmosDbDatabaseMemoryPartitionKey
      }
    ]
  }
}

module container_app_environment './modules/compute/container-app-environment.bicep' = {
  name: take('module.container-app-environment.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
    tags: allTags
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
  }
}

module foundry_search_connection './modules/ai/ai-foundry-connection.bicep' = {
  name: take('module.foundry-search-connection.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  dependsOn: [gpt_model_deployment, gpt4_1_model_deployment, reasoning_model_deployment]
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectResourceName
    connectionName: aiSearchConnectionName
    category: 'CognitiveSearch'
    target: ai_search.outputs.endpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: ai_search.outputs.resourceId
    }
  }
}

module foundry_storage_connection './modules/ai/ai-foundry-connection.bicep' = {
  name: take('module.foundry-storage-connection.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  dependsOn: [gpt_model_deployment, gpt4_1_model_deployment, reasoning_model_deployment]
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectResourceName
    connectionName: aiStorageConnectionName
    category: 'AzureBlob'
    target: storage_account.outputs.blobEndpoint
    authType: 'AAD'
    metadata: {
      ResourceId: storage_account.outputs.resourceId
      AccountName: storage_account.outputs.name
      ContainerName: 'default'
    }
  }
}

module foundry_appi_connection './modules/ai/ai-foundry-connection.bicep' = if (!useExistingAiFoundryAiProject) {
  name: take('module.foundry-appi-connection.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  dependsOn: [gpt_model_deployment, gpt4_1_model_deployment, reasoning_model_deployment]
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryAiServicesResourceName
    projectName: aiFoundryAiProjectResourceName
    connectionName: aiAppInsightsConnectionName
    category: 'AppInsights'
    target: app_insights.outputs.resourceId
    authType: 'ApiKey'
    isDefault: true
    credentialsKey: app_insights.outputs.instrumentationKey
    metadata: {
      ApiType: 'Azure'
      ResourceId: app_insights.outputs.resourceId
    }
  }
}

module backend_container_app './modules/compute/container-app.bicep' = {
  name: take('module.backend-container-app.${solutionSuffix}', 64)
  params: {
    name: backendContainerAppName
    location: solutionLocation
    tags: allTags
    environmentResourceId: container_app_environment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 8000
    managedIdentities: {
      userAssignedResourceIds: [userAssignedIdentity.outputs.resourceId]
    }
    corsPolicy: {
      allowedOrigins: [
        frontendAppUrl
        'http://${frontendAppName}.azurewebsites.net'
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
      maxReplicas: 1
    }
    containers: [
      {
        name: 'backend'
        image: '${backendContainerRegistryHostname}/${backendContainerImageName}:${backendContainerImageTag}'
        resources: {
          cpu: 2
          memory: '4Gi'
        }
        env: [
          {
            name: 'COSMOSDB_ENDPOINT'
            value: 'https://${cosmosDBModule.outputs.name}.documents.azure.com:443/'
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
            name: 'AZURE_OPENAI_MODEL_NAME'
            value: gpt_model_deployment.outputs.name
          }
          {
            name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
            value: gpt_model_deployment.outputs.name
          }
          {
            name: 'AZURE_OPENAI_RAI_DEPLOYMENT_NAME'
            value: gpt4_1_model_deployment.outputs.name
          }
          {
            name: 'AZURE_OPENAI_API_VERSION'
            value: azureOpenaiAPIVersion
          }
          {
            name: 'APPLICATIONINSIGHTS_INSTRUMENTATION_KEY'
            value: app_insights.outputs.instrumentationKey
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: app_insights.outputs.connectionString
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
            value: aiFoundryAiProjectResourceName
          }
          {
            name: 'FRONTEND_SITE_NAME'
            value: frontendAppUrl
          }
          {
            name: 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
            value: gpt_model_deployment.outputs.name
          }
          {
            name: 'APP_ENV'
            value: 'Prod'
          }
          {
            name: 'AZURE_AI_SEARCH_CONNECTION_NAME'
            value: aiSearchConnectionName
          }
          {
            name: 'AZURE_AI_SEARCH_ENDPOINT'
            value: ai_search.outputs.endpoint
          }
          {
            name: 'AZURE_COGNITIVE_SERVICES'
            value: 'https://cognitiveservices.azure.com/.default'
          }
          {
            name: 'AZURE_BING_CONNECTION_NAME'
            value: 'binggrnd'
          }
          {
            name: 'BING_CONNECTION_NAME'
            value: 'binggrnd'
          }
          {
            name: 'REASONING_MODEL_NAME'
            value: reasoning_model_deployment.outputs.name
          }
          {
            name: 'MCP_SERVER_ENDPOINT'
            value: 'https://${mcp_container_app.outputs.fqdn}/mcp'
          }
          {
            name: 'MCP_SERVER_NAME'
            value: mcpServerName
          }
          {
            name: 'MCP_SERVER_DESCRIPTION'
            value: mcpServerDescription
          }
          {
            name: 'AZURE_TENANT_ID'
            value: tenant().tenantId
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: userAssignedIdentity.outputs.clientId
          }
          {
            name: 'SUPPORTED_MODELS'
            value: supportedModels
          }
          {
            name: 'AZURE_STORAGE_BLOB_URL'
            value: storage_account.outputs.blobEndpoint
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
            name: 'AZURE_AI_AGENT_API_VERSION'
            value: azureAiAgentAPIVersion
          }
          {
            name: 'AZURE_AI_AGENT_PROJECT_CONNECTION_STRING'
            value: aiAgentProjectConnectionString
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

module mcp_container_app './modules/compute/container-app.bicep' = {
  name: take('module.mcp-container-app.${solutionSuffix}', 64)
  params: {
    name: mcpContainerAppName
    location: solutionLocation
    tags: allTags
    environmentResourceId: container_app_environment.outputs.resourceId
    ingressExternal: true
    ingressTargetPort: 9000
    managedIdentities: {
      userAssignedResourceIds: [userAssignedIdentity.outputs.resourceId]
    }
    corsPolicy: {
      allowedOrigins: [
        frontendAppUrl
        'http://${frontendAppName}.azurewebsites.net'
      ]
    }
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 1
    }
    containers: [
      {
        name: 'mcp'
        image: '${MCPContainerRegistryHostname}/${MCPContainerImageName}:${MCPContainerImageTag}'
        resources: {
          cpu: 2
          memory: '4Gi'
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
            value: mcpServerName
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
            value: userAssignedIdentity.outputs.clientId
          }
          {
            name: 'JWKS_URI'
            value: 'https://login.microsoftonline.com/${tenant().tenantId}/discovery/v2.0/keys'
          }
          {
            name: 'ISSUER'
            value: 'https://sts.windows.net/${tenant().tenantId}/'
          }
          {
            name: 'AUDIENCE'
            value: 'api://${userAssignedIdentity.outputs.clientId}'
          }
          {
            name: 'DATASET_PATH'
            value: './datasets'
          }
        ]
      }
    ]
  }
}

module app_service_plan './modules/compute/app-service-plan.bicep' = {
  name: take('module.app-service-plan.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
    tags: allTags
    skuName: 'B3'
    skuCapacity: 1
  }
}

module frontend_app './modules/compute/app-service.bicep' = {
  name: take('module.frontend-app.${solutionSuffix}', 64)
  params: {
    solutionName: frontendAppName
    location: solutionLocation
    tags: allTags
    serverFarmResourceId: app_service_plan.outputs.resourceId
    linuxFxVersion: 'DOCKER|${frontendContainerRegistryHostname}/${frontendContainerImageName}:${frontendContainerImageTag}'
    appSettings: {
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
      DOCKER_REGISTRY_SERVER_URL: 'https://${frontendContainerRegistryHostname}'
      WEBSITES_PORT: '3000'
      WEBSITES_CONTAINER_START_TIME_LIMIT: '1800'
      BACKEND_API_URL: 'https://${backend_container_app.outputs.fqdn}'
      AUTH_ENABLED: 'false'
      PROXY_API_REQUESTS: 'false'
      APPLICATIONINSIGHTS_CONNECTION_STRING: app_insights.outputs.connectionString
      APPINSIGHTS_INSTRUMENTATIONKEY: app_insights.outputs.instrumentationKey
    }
  }
}

module role_assignments './modules/identity/role-assignments.bicep' = {
  name: take('module.role-assignments.${solutionSuffix}', 64)
  params: {
    solutionName: solutionSuffix
    useExistingAIProject: useExistingAiFoundryAiProject
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    aiFoundryResourceId: aiFoundryAiServicesResourceId
    aiSearchResourceId: ai_search.outputs.resourceId
    storageAccountResourceId: storage_account.outputs.resourceId
    aiProjectPrincipalId: aiFoundryAiProjectPrincipalId
    existingAiProjectPrincipalId: useExistingAiFoundryAiProject ? existing_project_setup!.outputs.aiProjectPrincipalId : ''
    aiSearchPrincipalId: ai_search.outputs.identityPrincipalId
    deployerPrincipalId: deployingUserPrincipalId
    deployerPrincipalType: deployerPrincipalType
    backendAppServicePrincipalId: userAssignedIdentity.outputs.principalId
    cosmosDbAccountName: cosmosDBModule.outputs.name
  }
}

module assignBackendAiDeveloperToAiServices './modules/identity/cross-scope-role-assignment.bicep' = {
  name: take('module.backend-ai-developer.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: azureAIDeveloperRoleDefinitionId
    roleAssignmentName: guid(solutionSuffix, 'backend-uai', aiFoundryAiServicesResourceName, azureAIDeveloperRoleDefinitionId)
    aiFoundryName: aiFoundryAiServicesResourceName
  }
}

module assignBackendOpenAiUserToAiServices './modules/identity/cross-scope-role-assignment.bicep' = {
  name: take('module.backend-openai-user.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cognitiveServicesOpenAIUserRoleDefinitionId
    roleAssignmentName: guid(solutionSuffix, 'backend-uai', aiFoundryAiServicesResourceName, cognitiveServicesOpenAIUserRoleDefinitionId)
    aiFoundryName: aiFoundryAiServicesResourceName
  }
}

resource storageBlobDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
}

resource searchIndexDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
}

resource aiSearchResource 'Microsoft.Search/searchServices@2025-05-01' existing = {
  name: aiSearchServiceName
}

resource backendStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, 'backend-uai-storage-blob-contributor', solutionSuffix)
  scope: storageAccountResource
  properties: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: storageBlobDataContributor.id
    principalType: 'ServicePrincipal'
  }
}

resource backendSearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, 'backend-uai-search-index-contributor', solutionSuffix)
  scope: aiSearchResource
  properties: {
    principalId: userAssignedIdentity.outputs.principalId
    roleDefinitionId: searchIndexDataContributor.id
    principalType: 'ServicePrincipal'
  }
}

@description('The resource group the resources were deployed into.')
output resourceGroupName string = resourceGroup().name

@description('The default hostname of the frontend web app.')
output webSiteDefaultHostname string = replace(frontend_app.outputs.appUrl, 'https://', '')

output AZURE_STORAGE_BLOB_URL string = storage_account.outputs.blobEndpoint
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccountName
output AZURE_AI_SEARCH_ENDPOINT string = ai_search.outputs.endpoint
output AZURE_AI_SEARCH_NAME string = aiSearchServiceName

output COSMOSDB_ENDPOINT string = 'https://${cosmosDbResourceName}.documents.azure.com:443/'
output COSMOSDB_DATABASE string = cosmosDbDatabaseName
output COSMOSDB_CONTAINER string = cosmosDbDatabaseMemoryContainerName
output AZURE_OPENAI_ENDPOINT string = aiFoundryOpenAIEndpoint
output AZURE_OPENAI_MODEL_NAME string = gpt_model_deployment.outputs.name
output AZURE_OPENAI_DEPLOYMENT_NAME string = gpt_model_deployment.outputs.name
output AZURE_OPENAI_RAI_DEPLOYMENT_NAME string = gpt4_1_model_deployment.outputs.name
output AZURE_OPENAI_API_VERSION string = azureOpenaiAPIVersion
output AZURE_AI_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_AI_RESOURCE_GROUP string = resourceGroup().name
output AZURE_AI_PROJECT_NAME string = aiFoundryAiProjectResourceName
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = gpt_model_deployment.outputs.name
output APP_ENV string = 'Prod'
output AI_FOUNDRY_RESOURCE_ID string = useExistingAiFoundryAiProject ? existingFoundryProjectResourceId : ai_foundry_project!.outputs.resourceId
output COSMOSDB_ACCOUNT_NAME string = cosmosDbResourceName
output AZURE_SEARCH_ENDPOINT string = ai_search.outputs.endpoint
output AZURE_CLIENT_ID string = userAssignedIdentity.outputs.clientId
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_AI_SEARCH_CONNECTION_NAME string = foundry_search_connection.outputs.connectionName
output AZURE_COGNITIVE_SERVICES string = 'https://cognitiveservices.azure.com/.default'
output REASONING_MODEL_NAME string = reasoning_model_deployment.outputs.name
output MCP_SERVER_NAME string = mcpServerName
output MCP_SERVER_DESCRIPTION string = mcpServerDescription
output SUPPORTED_MODELS string = supportedModels
output BACKEND_URL string = 'https://${backend_container_app.outputs.fqdn}'
output AZURE_AI_PROJECT_ENDPOINT string = aiFoundryAiProjectEndpoint
output AZURE_AI_AGENT_ENDPOINT string = aiFoundryAiProjectEndpoint
output AZURE_AI_AGENT_API_VERSION string = azureAiAgentAPIVersion
output AZURE_AI_AGENT_PROJECT_CONNECTION_STRING string = aiAgentProjectConnectionString

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

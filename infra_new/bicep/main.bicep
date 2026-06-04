// ========== main.bicep ========== //
targetScope = 'resourceGroup'

// ============================================================================
// Parameters
// ============================================================================

// ── Core ──

@minLength(3)
@maxLength(20)
@description('Optional. A unique application/solution name for all resources in this deployment.')
param solutionName string = 'agenticappudf'

@maxLength(5)
@description('Optional. A unique text suffix appended to resource names for uniqueness.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@description('Optional. Primary Azure region for resource deployment. Defaults to resource group location.')
param location string = ''

@description('Optional. Secondary location for database resources (example: eastus2).')
param secondaryLocation string = 'eastus2'

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
@description('Required. Location for AI Foundry and model deployments.')
param azureAiServiceLocation string

@description('Optional. Location for AI Search service deployment. Defaults to resource group location.')
param searchServiceLocation string = resourceGroup().location

// ── AI Configuration ──

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT model deployment type.')
param deploymentType string = 'GlobalStandard'

@description('Optional. Name of the GPT model to deploy.')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the GPT model to deploy.')
param gptModelVersion string = '2025-04-14'

@description('Optional. Azure OpenAI API version.')
param azureOpenaiAPIVersion string = '2025-01-01-preview'

@description('Optional. Azure AI Agent API version.')
param azureAiAgentApiVersion string = '2025-05-01'

@minValue(10)
@description('Optional. Capacity of the GPT deployment (TPM in thousands).')
param gptDeploymentCapacity int = 150

@allowed([
  'text-embedding-3-small'
])
@description('Optional. Name of the Text Embedding model to deploy.')
param embeddingModel string = 'text-embedding-3-small'

@minValue(10)
@description('Optional. Capacity of the Embedding Model deployment.')
param embeddingDeploymentCapacity int = 80

// ── Compute ──

@description('Optional. Docker image tag for app deployments.')
param imageTag string = 'latest_v2'

@description('Optional. Name of the Azure Container Registry.')
param containerRegistryName string = 'dataagentscontainerreg'

@allowed([
  'python'
  'dotnet'
])
@description('Optional. Backend runtime stack.')
param backendRuntimeStack string = 'python'

// ── Feature Flags ──

@description('Optional. Deploy the application components (Cosmos DB, API, Frontend).')
param deployApp bool = true

@description('Optional. Enable chat history storage.')
param useChatHistoryEnabled bool = true

@description('Optional. Enable user access token forwarding to the API.')
param useUserAccessToken bool = false

// ── Existing Resources ──

@description('Optional. Resource ID of an existing Log Analytics workspace. Empty creates a new one.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project. Empty creates a new one.')
param existingFoundryProjectResourceId string = ''

// ── Identity ──

@allowed(['User', 'ServicePrincipal'])
@description('Optional. Principal type of the deploying user. Use ServicePrincipal for CI/CD pipelines with OIDC.')
param deployingUserPrincipalType string = 'User'

@description('Optional. Created by user name for resource tagging.')
param createdBy string = contains(deployer(), 'userPrincipalName') ? split(deployer().userPrincipalName, '@')[0] : deployer().objectId

// ── App Configuration ──

@description('Optional. Primary title displayed in the header of the web app.')
param appTitlePrimary string = 'Contoso'

@description('Optional. Secondary title displayed in the header of the web app.')
param appTitleSecondary string = '| Unified Data Analysis Agents'

// ── Fabric Capacity ──

@description('Optional. Set to true to auto-create a Fabric workspace during post-provision.')
param createFabricWorkspace bool = false

@description('Optional. Name of an existing Fabric capacity to reuse. Empty auto-creates when conditions are met.')
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
// Variables
// ============================================================================

var solutionLocation = empty(location) ? resourceGroup().location : location

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId
var existingTags = resourceGroup().tags ?? {}

var useChatHistoryEnabledSetting = useChatHistoryEnabled ? 'True' : 'False'
var useUserAccessTokenSetting = useUserAccessToken ? 'True' : 'False'
var shouldDeployApp = deployApp

var useExistingFabricCapacity = !empty(azureFabricCapacityName)
var shouldCreateFabricCapacity = createFabricWorkspace && !useExistingFabricCapacity
var fabricCapacityResourceName = useExistingFabricCapacity ? azureFabricCapacityName : 'fc${solutionSuffix}'
var fabricCapacityDefaultAdmins = contains(deployerInfo, 'userPrincipalName')
  ? [deployerInfo.userPrincipalName]
  : [deployerInfo.objectId]
var fabricTotalAdminMembers = union(fabricCapacityDefaultAdmins, fabricAdminMembers)

// ========== Resource Group Tag ========== //
resource resourceGroupTags 'Microsoft.Resources/tags@2023-07-01' = {
  name: 'default'
  properties: {
   tags: union(
      existingTags,
      {
        TemplateName: 'Unified Data Analysis Agents'
        CreatedBy: createdBy
        DeploymentName: deployment().name
        Type: 'Non-WAF'
      }
    )
  }
}

// ========== Fabric Capacity ========== //
module fabricCapacity './modules/fabric/fabric-capacity.bicep' = if (shouldCreateFabricCapacity) {
  name: take('module.fabric-capacity.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: fabricCapacityResourceName
    location: solutionLocation
    skuName: fabricCapacitySku
    adminMembers: fabricTotalAdminMembers
    tags: union(existingTags, {
      TemplateName: 'Unified Data Analysis Agents'
      CreatedBy: createdBy
    })
  }
}

// ========== Monitoring (Log Analytics + Application Insights) ========== //
var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)

// ========== Log Analytics module ========== //
module log_analytics './modules/monitoring/log-analytics.bicep' = if (!useExistingLogAnalytics) {
  name: take('module.log-analytics.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
  }
  scope: resourceGroup(resourceGroup().name)
}

var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspaceId
  : log_analytics!.outputs.resourceId

// ========== Application Insights module ========== //
module app_insights './modules/monitoring/app-insights.bicep' = {
  name: take('module.app-insights.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    workspaceResourceId: logAnalyticsWorkspaceResourceId
  }
  scope: resourceGroup(resourceGroup().name)
}

// ==========AI Foundry and related resources ========== //
var aiModelDeployments = [
  {
    name: gptModelName
    model: gptModelName
    sku: {
      name: deploymentType
      capacity: gptDeploymentCapacity
    }
    version: gptModelVersion
    raiPolicyName: 'Microsoft.Default'
  }
  {
    name: embeddingModel
    model: embeddingModel
    sku: {
      name: 'GlobalStandard'
      capacity: embeddingDeploymentCapacity
    }
    version: '1'
    raiPolicyName: 'Microsoft.Default'
  }
]

// Deploy new AI Services account + AI Foundry project (no connections, no deployments)
module ai_foundry_project './modules/ai/ai-foundry-project.bicep' = if (empty(existingFoundryProjectResourceId)) {
  name: take('module.ai-foundry-project.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Unified AI Foundry resource name vars ========== //
var useExistingAIProject = !empty(existingFoundryProjectResourceId)
var aiFoundryResourceName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[8] : ai_foundry_project!.outputs.name
var aiProjectResourceName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[10] : ai_foundry_project!.outputs.projectName
var aiServiceSubscription = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var aiServiceResourceGroup = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name

// Reference existing AI Foundry project (identity only)
module existing_project_setup './modules/ai/existing-project-setup.bicep' = if (useExistingAIProject) {
  name: take('module.existing-project-setup.${solutionName}', 64)
  scope: resourceGroup(aiServiceSubscription, aiServiceResourceGroup)
  params: {
    name: aiFoundryResourceName
    projectName: aiProjectResourceName
  }
}

// AI Search connection (single call for both existing and new paths)
module foundry_search_connection './modules/ai/ai-foundry-connection.bicep' = {
  name: take('module.foundry-search-conn.${solutionName}', 64)
  scope: resourceGroup(aiServiceSubscription, aiServiceResourceGroup)
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
  scope: resourceGroup(aiServiceSubscription, aiServiceResourceGroup)
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
module foundry_appi_connection './modules/ai/ai-foundry-connection.bicep' = if (!useExistingAIProject) {
  name: take('module.foundry-appi-conn.${solutionName}', 64)
  scope: resourceGroup(aiServiceSubscription, aiServiceResourceGroup)
  params: {
    solutionName: solutionSuffix
    aiServicesAccountName: aiFoundryResourceName
    projectName: aiProjectResourceName
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

// Model deployments (single loop for both existing and new paths)
@batchSize(1)
module model_deployments './modules/ai/ai-foundry-model-deployment.bicep' = [for (deployment, i) in aiModelDeployments: {
  name: take('module.model-deployment-${i}.${solutionName}', 64)
  scope: resourceGroup(aiServiceSubscription, aiServiceResourceGroup)
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

module ai_search './modules/ai/ai-search.bicep' = {
  name: take('module.ai-search.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: searchServiceLocation
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== AI outputs (ternary: existing vs new) ========== //
var aiFoundryEndpoint = useExistingAIProject ? existing_project_setup!.outputs.aiFoundryEndpoint : ai_foundry_project!.outputs.endpoint
var projectEndpoint = useExistingAIProject ? existing_project_setup!.outputs.projectEndpoint : ai_foundry_project!.outputs.projectEndpoint
var aiFoundryName = useExistingAIProject ? existing_project_setup!.outputs.aiServicesAccountName : ai_foundry_project!.outputs.name
var aiProjectName = useExistingAIProject ? existing_project_setup!.outputs.aiProjectName : ai_foundry_project!.outputs.projectName
var aiFoundryResourceId = useExistingAIProject ? existing_project_setup!.outputs.aiFoundryResourceId : ai_foundry_project!.outputs.resourceId
var aiProjectPrincipalId = useExistingAIProject ? existing_project_setup!.outputs.aiProjectPrincipalId : ai_foundry_project!.outputs.projectIdentityPrincipalId
var aiSearchConnectionId = foundry_search_connection.outputs.connectionId

// ========== Storage Account module ========== //
module storage_account './modules/data/storage-account.bicep' = {
  name: take('module.storage-account.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: azureAiServiceLocation
    tags: {}
    containers: [
      { name: 'default', publicAccess: 'None' }
    ]
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Cosmos DB module ========== //
module cosmosDBModule './modules/data/cosmos-db-nosql.bicep' = if (deployApp) {
  name: take('module.cosmos-db-nosql.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'cosmos-${solutionSuffix}'
    location: secondaryLocation
    databaseName: 'db_conversation_history'
    containers: [
      { name: 'conversations', partitionKeyPath: '/userId' }
    ]
  }
  scope: resourceGroup(resourceGroup().name)
}

module hostingplan './modules/compute/app-service-plan.bicep' = if (shouldDeployApp) {
  name: take('module.app-service-plan.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    location: solutionLocation
  }
}

// ========== Compute image names ========== //
var backendApiImageName = 'DOCKER|${containerRegistryName}.azurecr.io/da-api:${imageTag}'
var backendCsApiImageName = 'DOCKER|${containerRegistryName}.azurecr.io/da-api-dotnet:${imageTag}'
var frontendImageName = 'DOCKER|${containerRegistryName}.azurecr.io/da-app:${imageTag}'
var reactAppLayoutConfig = '''{
  "appConfig": {
      "CHAT_CHATHISTORY": {
        "CHAT": 70,
        "CHATHISTORY": 30
      }
    }
  }
}'''

// ========== Backend Deployment (Python) ========== //
module backend_docker './modules/compute/app-service.bicep' = if (shouldDeployApp && backendRuntimeStack == 'python') {
  name: take('module.app-service-pybackend.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'api-${solutionSuffix}'
    location: solutionLocation
    serverFarmResourceId: hostingplan!.outputs.resourceId
    linuxFxVersion: backendApiImageName
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: app_insights.outputs.instrumentationKey
      REACT_APP_LAYOUT_CONFIG: reactAppLayoutConfig
      AZURE_ENV_GPT_MODEL_NAME: gptModelName
      AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME: embeddingModel
      AZURE_OPENAI_ENDPOINT: aiFoundryEndpoint
      AZURE_ENV_OPENAI_API_VERSION: azureOpenaiAPIVersion
      AZURE_OPENAI_RESOURCE: aiFoundryName
      AZURE_AI_AGENT_ENDPOINT: projectEndpoint
      AZURE_AI_AGENT_API_VERSION: azureAiAgentApiVersion
      AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: gptModelName
      USE_CHAT_HISTORY_ENABLED: useChatHistoryEnabledSetting
      AZURE_COSMOSDB_ACCOUNT: cosmosDBModule!.outputs.name
      AZURE_COSMOSDB_CONVERSATIONS_CONTAINER: cosmosDBModule!.outputs.containerName
      AZURE_COSMOSDB_DATABASE: cosmosDBModule!.outputs.databaseName
      AZURE_COSMOSDB_ENABLE_FEEDBACK: 'True'
      AZURE_SQLDB_USER_MID: ''
      API_UID: ''
      AZURE_AI_SEARCH_ENDPOINT: ai_search.outputs.endpoint
      AZURE_AI_SEARCH_INDEX: 'knowledge_index'
      AZURE_AI_SEARCH_CONNECTION_NAME: foundry_search_connection.outputs.connectionName

      USE_AI_PROJECT_CLIENT: 'True'
      DISPLAY_CHART_DEFAULT: 'False'
      APPLICATIONINSIGHTS_CONNECTION_STRING: app_insights.outputs.connectionString
      DUMMY_TEST: 'True'
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
  scope: resourceGroup(resourceGroup().name)
}

// ========== Backend Deployment (C#) ========== //
module backend_csapi_docker './modules/compute/app-service.bicep' = if (shouldDeployApp && backendRuntimeStack == 'dotnet') {
  name: take('module.app-service-csbackend.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'api-cs-${solutionSuffix}'
    location: solutionLocation
    serverFarmResourceId: hostingplan!.outputs.resourceId
    linuxFxVersion: backendCsApiImageName
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: app_insights.outputs.instrumentationKey
      REACT_APP_LAYOUT_CONFIG: reactAppLayoutConfig
      AZURE_ENV_GPT_MODEL_NAME: gptModelName
      AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME: embeddingModel
      AZURE_OPENAI_ENDPOINT: aiFoundryEndpoint
      AZURE_ENV_OPENAI_API_VERSION: azureOpenaiAPIVersion
      AZURE_OPENAI_RESOURCE: aiFoundryName
      AZURE_AI_AGENT_ENDPOINT: projectEndpoint
      AZURE_AI_AGENT_API_VERSION: azureAiAgentApiVersion
      AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: gptModelName
      USE_CHAT_HISTORY_ENABLED: useChatHistoryEnabledSetting
      AZURE_COSMOSDB_ACCOUNT: cosmosDBModule!.outputs.name
      AZURE_COSMOSDB_CONVERSATIONS_CONTAINER: cosmosDBModule!.outputs.containerName
      AZURE_COSMOSDB_DATABASE: cosmosDBModule!.outputs.databaseName
      AZURE_COSMOSDB_ENABLE_FEEDBACK: 'True'
      API_UID: ''
      AZURE_AI_SEARCH_ENDPOINT: ai_search.outputs.endpoint
      AZURE_AI_SEARCH_INDEX: 'knowledge_index'
      AZURE_AI_SEARCH_CONNECTION_NAME: foundry_search_connection.outputs.connectionName

      USE_AI_PROJECT_CLIENT: 'True'
      DISPLAY_CHART_DEFAULT: 'False'
      APPLICATIONINSIGHTS_CONNECTION_STRING: app_insights.outputs.connectionString
      DUMMY_TEST: 'True'
      SOLUTION_NAME: solutionSuffix 
      APP_ENV: 'Prod'

      AGENT_NAME_CHAT: ''
      AGENT_NAME_TITLE: ''

      FABRIC_SQL_DATABASE: ''
      FABRIC_SQL_SERVER: ''
      FABRIC_SQL_CONNECTION_STRING: ''
    }
  }
  scope: resourceGroup(resourceGroup().name)
}

// ========== Frontend Deployment ========== //
module frontend_docker './modules/compute/app-service.bicep' = if (shouldDeployApp) {
  name: take('module.app-service-frontend.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    name: 'app-${solutionSuffix}'
    location: solutionLocation
    serverFarmResourceId: hostingplan!.outputs.resourceId
    linuxFxVersion: frontendImageName
    appSettings: {
      APPINSIGHTS_INSTRUMENTATIONKEY: app_insights.outputs.instrumentationKey
      APP_API_BASE_URL: backendRuntimeStack == 'python' ? backend_docker!.outputs.appUrl : backend_csapi_docker!.outputs.appUrl
      CHAT_LANDING_TEXT: ''
      APP_TITLE_PRIMARY: appTitlePrimary
      APP_TITLE_SECONDARY: appTitleSecondary
    }
  }
  scope: resourceGroup(resourceGroup().name)
}

module role_assignments './modules/identity/role-assignments.bicep' = {
  name: take('module.role-assignments.${solutionName}', 64)
  params: {
    solutionName: solutionSuffix
    useExistingAIProject: useExistingAIProject
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    aiFoundryResourceId: !useExistingAIProject ? aiFoundryResourceId : ''
    aiSearchResourceId: ai_search.outputs.resourceId
    storageAccountResourceId: storage_account.outputs.resourceId
    aiProjectPrincipalId: aiProjectPrincipalId
    aiSearchPrincipalId: ai_search.outputs.identityPrincipalId
    deployerPrincipalId: deployingUserPrincipalId
    deployerPrincipalType: deployingUserPrincipalType
    backendAppServicePrincipalId: shouldDeployApp
      ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.identityPrincipalId : backend_csapi_docker!.outputs.identityPrincipalId)
      : ''
    cosmosDbAccountName: shouldDeployApp ? cosmosDBModule!.outputs.name : ''
    existingAiProjectPrincipalId: !empty(existingFoundryProjectResourceId) ? existing_project_setup!.outputs.aiProjectPrincipalId : ''
  }
  scope: resourceGroup(resourceGroup().name)
}

// ============================================================================
// Outputs
// ============================================================================

@description('Solution suffix used for naming resources')
output SOLUTION_NAME string = solutionSuffix

@description('Name of the deployed resource group')
output RESOURCE_GROUP_NAME string = resourceGroup().name

@description('Cosmos DB account name for conversation history storage')
output AZURE_COSMOSDB_ACCOUNT string = shouldDeployApp ? cosmosDBModule!.outputs.name : ''

@description('Cosmos DB container name for storing conversations')
output AZURE_COSMOSDB_CONVERSATIONS_CONTAINER string = 'conversations'

@description('Cosmos DB database name for conversation history')
output AZURE_COSMOSDB_DATABASE string = 'db_conversation_history'

@description('GPT model deployment name (e.g., gpt-4o-mini)')
output AZURE_ENV_GPT_MODEL_NAME string = gptModelName

@description('Azure OpenAI service endpoint URL')
output AZURE_OPENAI_ENDPOINT string = aiFoundryEndpoint

@description('Embedding model deployment name for vector search')
output AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME string = embeddingModel

@description('Managed identity client ID for SQL authentication')
output AZURE_SQLDB_USER_MID string = ''

@description('Backend API managed identity client ID (system-assigned, resolved at runtime)')
output API_UID string = ''

@description('Azure AI Agent service endpoint URL')
output AZURE_AI_AGENT_ENDPOINT string = projectEndpoint

@description('Model deployment name used by Azure AI Agent')
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = gptModelName

@description('Backend API App Service name')
output API_APP_NAME string = shouldDeployApp ? (backendRuntimeStack == 'python' ? 'api-${solutionSuffix}' : 'api-cs-${solutionSuffix}') : ''

@description('Backend API managed identity object/principal ID (system-assigned)')
output API_PID string = shouldDeployApp ? (backendRuntimeStack == 'python' ? backend_docker!.outputs.identityPrincipalId : backend_csapi_docker!.outputs.identityPrincipalId) : ''

@description('Backend API App Service name')
output MID_DISPLAY_NAME string = shouldDeployApp ? (backendRuntimeStack == 'python' ? 'api-${solutionSuffix}' : 'api-cs-${solutionSuffix}') : ''

@description('Frontend web app resource name')
output WEB_APP_NAME string = shouldDeployApp ? 'app-${solutionSuffix}' : ''

@description('Frontend web application URL')
output WEB_APP_URL string = shouldDeployApp ? frontend_docker!.outputs.appUrl : ''

@description('Azure AI Search service endpoint URL')
output AZURE_AI_SEARCH_ENDPOINT string = ai_search.outputs.endpoint

@description('Azure AI Search index name for document search')
output AZURE_AI_SEARCH_INDEX string = 'knowledge_index'

@description('Azure AI Search service resource name')
output AZURE_AI_SEARCH_NAME string = ai_search.outputs.name

@description('Local path to documents folder for search indexing')
output SEARCH_DATA_FOLDER string = 'data/default/documents'

@description('AI Foundry connection name for Azure AI Search')
output AZURE_AI_SEARCH_CONNECTION_NAME string = foundry_search_connection.outputs.connectionName

@description('AI Foundry connection ID for Azure AI Search')
output AZURE_AI_SEARCH_CONNECTION_ID string = aiSearchConnectionId

@description('Azure AI Foundry project endpoint URL')
output AZURE_AI_PROJECT_ENDPOINT string = projectEndpoint

@description('Azure AI Foundry resource ID for role assignments')
output AI_FOUNDRY_RESOURCE_ID string = aiFoundryResourceId

@description('Azure AI Foundry project name')
output AZURE_AI_PROJECT_NAME string = aiProjectName

@description('Azure AI Services resource name')
output AI_SERVICE_NAME string = aiFoundryName

@description('Azure AI Foundry project managed identity principal ID')
output FOUNDRY_PROJECT_PID string = aiProjectPrincipalId

@description('Flag indicating whether chat history storage is enabled')
output USE_CHAT_HISTORY_ENABLED string = useChatHistoryEnabledSetting

@description('Backend runtime stack (python or dotnet)')
output BACKEND_RUNTIME_STACK string = backendRuntimeStack

@description('Flag indicating whether user access token forwarding is enabled')
output USE_USER_ACCESS_TOKEN string = useUserAccessTokenSetting

@description('The resource ID of the Fabric capacity.')
output AZURE_FABRIC_CAPACITY_RESOURCE_ID string = createFabricWorkspace ? fabricCapacity.outputs.resourceId : ''

@description('The name of the Fabric capacity resource.')
output AZURE_FABRIC_CAPACITY_NAME string = createFabricWorkspace ? fabricCapacityResourceName : ''

@description('The identities assigned as Fabric Capacity Admin members.')
output FABRIC_ADMIN_MEMBERS array = shouldCreateFabricCapacity ? fabricTotalAdminMembers : []

@description('The unique solution suffix of the deployed resources.')
output SOLUTION_SUFFIX string = solutionSuffix

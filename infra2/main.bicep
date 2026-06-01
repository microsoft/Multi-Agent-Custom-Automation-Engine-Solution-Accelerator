// ============================================================================
// main.bicep — Deployment Router
// Description: Routes deployment to the appropriate infrastructure flavor.
//   - 'bicep'   → Vanilla Bicep modules (Docker deployment)
//   - 'avm'     → AVM-based modules (non-WAF)
//   - 'avm-waf' → AVM-based modules with WAF-aligned features
//              (monitoring, private networking, scalability, redundancy)
// ============================================================================
targetScope = 'resourceGroup'

// ============================================================================
// Routing Parameter
// ============================================================================

@allowed(['bicep', 'avm', 'avm-waf'])
@description('Required. Deployment flavor: bicep (vanilla Docker), avm (AVM non-WAF), or avm-waf (AVM WAF-aligned).')
param deploymentFlavor string

// ============================================================================
// Parameters — Core (shared across all flavors)
// ============================================================================

@minLength(3)
@maxLength(20)
@description('Optional. A unique application/solution name used as base for all resource naming.')
param solutionName string = 'macae'

@maxLength(5)
@description('Optional. A unique text suffix appended to resource names for uniqueness.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services. Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).')
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

@description('Optional. Secondary location for database resources (example: eastus2).')
param secondaryLocation string = 'eastus2'

var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId

// Restricting deployment to only supported Azure OpenAI regions validated with GPT-4o model
@allowed(['australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus','westus3'])
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
@description('Required. Location for all AI service resources. This should be one of the supported Azure AI Service locations.')
param azureAiServiceLocation string

// @description('Optional. Location for AI Search service deployment.')
// param searchServiceLocation string = location

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@minLength(1)
@description('Optional. Name of the GPT model to deploy:')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the GPT model to deploy. Defaults to 2025-04-14.')
param gptModelVersion string = '2025-04-14'

@minLength(1)
@description('Optional. Name of the GPT model to deploy:')
param gpt4_1ModelName string = 'gpt-4.1'

@description('Optional. Version of the GPT model to deploy. Defaults to 2025-04-14.')
param gpt4_1ModelVersion string = '2025-04-14'

@minLength(1)
@description('Optional. Name of the GPT Reasoning model to deploy:')
param gptReasoningModelName string = 'o4-mini'

@description('Optional. Version of the GPT Reasoning model to deploy. Defaults to 2025-04-16.')
param gptReasoningModelVersion string = '2025-04-16'

@description('Optional. Version of the Azure OpenAI service to deploy. Defaults to 2024-12-01-preview.')
param azureOpenaiAPIVersion string = '2024-12-01-preview'

@description('Optional. Version of the Azure AI Agent API version. Defaults to 2025-01-01-preview.')
param azureAiAgentAPIVersion string = '2025-01-01-preview'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT model deployment type. Defaults to GlobalStandard.')
param gpt4_1ModelDeploymentType string = 'GlobalStandard'

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
@description('Optional. GPT model deployment type. Defaults to GlobalStandard.')
param gptReasoningModelDeploymentType string = 'GlobalStandard'

@description('Optional. AI model deployment token capacity. Defaults to 50 for optimal performance.')
param gptDeploymentCapacity int = 50

@description('Optional. AI model deployment token capacity. Defaults to 150 for optimal performance.')
param gpt4_1ModelCapacity int = 150

@description('Optional. AI model deployment token capacity. Defaults to 50 for optimal performance.')
param gptReasoningModelCapacity int = 50

// ============================================================================
// Parameters — Compute
// ============================================================================


// These parameters are changed for testing - please reset as part of publication

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
param MCPContainerImageTag string = 'latest_v4'x

// ============================================================================
// Parameters — Existing Resources
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics workspace. Empty creates a new one.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project. Empty creates a new one.')
param existingFoundryProjectResourceId string = ''

// ============================================================================
// Parameters — Identity
// ============================================================================

@allowed(['User', 'ServicePrincipal'])
@description('Optional. Principal type of the deploying user. Use ServicePrincipal for CI/CD pipelines with OIDC.')
param deployingUserPrincipalType string = contains(deployer(), 'userPrincipalName') ? 'User' : 'ServicePrincipal'

// ============================================================================
// Parameters — App Configuration
// ============================================================================



// ============================================================================
// Parameters — AVM-specific (ignored when deploymentFlavor = 'bicep')
// ============================================================================

// @description('Optional. Tags to apply to all resources (AVM only).')
// param tags object = {}

@description('Optional. The tags to apply to all deployed Azure resources.')
param tags resourceInput<'Microsoft.Resources/resourceGroups@2025-04-01'>.tags = {}

@description('Optional. Enable monitoring applicable resources, aligned with the Well Architected Framework recommendations. This setting enables Application Insights and Log Analytics and configures all the resources applicable resources to send logs. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false



@secure()
@description('Optional. VM admin username (AVM-WAF only, when private networking is enabled).')
param vmAdminUsername string?

@secure()
@description('Optional. VM admin password (AVM-WAF only, when private networking is enabled).')
param vmAdminPassword string?

@description('Optional. VM size for jumpbox (AVM-WAF only). Defaults to Standard_D2s_v5.')
param vmSize string = 'Standard_D2s_v5'

// ============================================================================
// Derived Variables
// ============================================================================

var isAvm = deploymentFlavor == 'avm' || deploymentFlavor == 'avm-waf'
var isBicep = deploymentFlavor == 'bicep'

// ============================================================================
// Module: AVM Deployment (non-WAF and WAF)
// Activated when deploymentFlavor = 'avm' or 'avm-waf'
// WAF features (monitoring, private networking, scalability, redundancy)
// are enabled automatically for 'avm-waf'.
// ============================================================================

module avmDeployment './avm/main.bicep' = if (isAvm) {
  name: take('module.avm.${solutionName}', 64)
  params: {
    solutionName: solutionName
    solutionUniqueText: solutionUniqueText
    location: location
    secondaryLocation: secondaryLocation
    tags: tags
    enableTelemetry: enableTelemetry
    enableMonitoring: enableMonitoring
    enablePrivateNetworking: enablePrivateNetworking
    enableScalability: enableScalability
    enableRedundancy: enableRedundancy
    vmAdminUsername: vmAdminUsername
    vmAdminPassword: vmAdminPassword
    vmSize: vmSize
    azureAiServiceLocation: azureAiServiceLocation
    searchServiceLocation: searchServiceLocation
    deploymentType: deploymentType
    gptModelName: gptModelName
    gptModelVersion: gptModelVersion
    gptDeploymentCapacity: gptDeploymentCapacity
    embeddingModel: embeddingModel
    embeddingDeploymentCapacity: embeddingDeploymentCapacity
    azureOpenaiAPIVersion: azureOpenaiAPIVersion
    azureAiAgentApiVersion: azureAiAgentApiVersion
    imageTag: imageTag
    containerRegistryName: containerRegistryName
    backendRuntimeStack: backendRuntimeStack
    appServicePlanSku: appServicePlanSku
    deployApp: deployApp
    azureEnvOnly: azureEnvOnly
    useChatHistoryEnabled: useChatHistoryEnabled
    useUserAccessToken: useUserAccessToken
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    deployingUserPrincipalType: deployingUserPrincipalType
    usecase: usecase
    appTitlePrimary: appTitlePrimary
    appTitleSecondary: appTitleSecondary
    createFabricWorkspace: createFabricWorkspace
    azureFabricCapacityName: azureFabricCapacityName
    fabricCapacitySku: fabricCapacitySku
    fabricAdminMembers: fabricAdminMembers
  }
}

// ============================================================================
// Module: Vanilla Bicep Deployment (Docker)
// Activated when deploymentFlavor = 'bicep'
// ============================================================================

module bicepDeployment './bicep/main.bicep' = if (isBicep) {
  name: take('module.bicep.${solutionName}', 64)
  params: {
    solutionName: solutionName
    solutionUniqueText: solutionUniqueText
    location: location
    secondaryLocation: secondaryLocation
    azureAiServiceLocation: azureAiServiceLocation
    searchServiceLocation: searchServiceLocation
    deploymentType: deploymentType  
    gptModelName: gptModelName
    gptModelVersion: gptModelVersion
    gptDeploymentCapacity: gptDeploymentCapacity
    embeddingModel: embeddingModel
    embeddingDeploymentCapacity: embeddingDeploymentCapacity
    azureOpenaiAPIVersion: azureOpenaiAPIVersion
    azureAiAgentApiVersion: azureAiAgentApiVersion
    imageTag: imageTag
    containerRegistryName: containerRegistryName
    backendRuntimeStack: backendRuntimeStack
    deployApp: deployApp
    azureEnvOnly: azureEnvOnly
    useChatHistoryEnabled: useChatHistoryEnabled
    useUserAccessToken: useUserAccessToken
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    deployingUserPrincipalType: deployingUserPrincipalType
    usecase: usecase
    appTitlePrimary: appTitlePrimary
    appTitleSecondary: appTitleSecondary
    createFabricWorkspace: createFabricWorkspace
    azureFabricCapacityName: azureFabricCapacityName
    fabricCapacitySku: fabricCapacitySku
    fabricAdminMembers: fabricAdminMembers
  }
}

// ============================================================================
// Outputs — Coalesced from whichever flavor was deployed
// ============================================================================

@description('Solution suffix used for naming resources.')
output SOLUTION_NAME string = isAvm ? avmDeployment!.outputs.SOLUTION_NAME : bicepDeployment!.outputs.SOLUTION_NAME

@description('Name of the deployed resource group.')
output RESOURCE_GROUP_NAME string = resourceGroup().name

@description('Deployment flavor used.')
output DEPLOYMENT_FLAVOR string = deploymentFlavor

@description('WAF deployment type (AVM only).')
output DEPLOYMENT_TYPE string = isAvm ? avmDeployment!.outputs.DEPLOYMENT_TYPE : 'N/A'

@description('Cosmos DB account name.')
output AZURE_COSMOSDB_ACCOUNT string = isAvm ? avmDeployment!.outputs.AZURE_COSMOSDB_ACCOUNT : bicepDeployment!.outputs.AZURE_COSMOSDB_ACCOUNT

@description('Cosmos DB container name.')
output AZURE_COSMOSDB_CONVERSATIONS_CONTAINER string = isAvm ? avmDeployment!.outputs.AZURE_COSMOSDB_CONVERSATIONS_CONTAINER : bicepDeployment!.outputs.AZURE_COSMOSDB_CONVERSATIONS_CONTAINER

@description('Cosmos DB database name.')
output AZURE_COSMOSDB_DATABASE string = isAvm ? avmDeployment!.outputs.AZURE_COSMOSDB_DATABASE : bicepDeployment!.outputs.AZURE_COSMOSDB_DATABASE

@description('GPT model deployment name.')
output AZURE_ENV_GPT_MODEL_NAME string = isAvm ? avmDeployment!.outputs.AZURE_ENV_GPT_MODEL_NAME : bicepDeployment!.outputs.AZURE_ENV_GPT_MODEL_NAME

@description('Azure OpenAI service endpoint URL.')
output AZURE_OPENAI_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_OPENAI_ENDPOINT : bicepDeployment!.outputs.AZURE_OPENAI_ENDPOINT

@description('Embedding model deployment name.')
output AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME : bicepDeployment!.outputs.AZURE_ENV_EMBEDDING_DEPLOYMENT_NAME

@description('Azure SQL database name (Azure-only mode).')
output AZURE_SQLDB_DATABASE string = isAvm ? avmDeployment!.outputs.AZURE_SQLDB_DATABASE : bicepDeployment!.outputs.AZURE_SQLDB_DATABASE

@description('Azure SQL server FQDN (Azure-only mode).')
output AZURE_SQLDB_SERVER string = isAvm ? avmDeployment!.outputs.AZURE_SQLDB_SERVER : bicepDeployment!.outputs.AZURE_SQLDB_SERVER

@description('Managed identity client ID for SQL auth.')
output AZURE_SQLDB_USER_MID string = isAvm ? avmDeployment!.outputs.AZURE_SQLDB_USER_MID : bicepDeployment!.outputs.AZURE_SQLDB_USER_MID

@description('Backend API managed identity client ID.')
output API_UID string = isAvm ? avmDeployment!.outputs.API_UID : bicepDeployment!.outputs.API_UID

@description('Azure AI Agent endpoint.')
output AZURE_AI_AGENT_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_AI_AGENT_ENDPOINT : bicepDeployment!.outputs.AZURE_AI_AGENT_ENDPOINT

@description('Model deployment name for AI Agent.')
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME : bicepDeployment!.outputs.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME

@description('Backend API App Service name.')
output API_APP_NAME string = isAvm ? avmDeployment!.outputs.API_APP_NAME : bicepDeployment!.outputs.API_APP_NAME

@description('Backend API managed identity principal ID.')
output API_PID string = isAvm ? avmDeployment!.outputs.API_PID : bicepDeployment!.outputs.API_PID

@description('Backend API managed identity display name.')
output MID_DISPLAY_NAME string = isAvm ? avmDeployment!.outputs.MID_DISPLAY_NAME : bicepDeployment!.outputs.MID_DISPLAY_NAME

@description('Frontend web application URL.')
output WEB_APP_URL string = isAvm ? avmDeployment!.outputs.WEB_APP_URL : bicepDeployment!.outputs.WEB_APP_URL

@description('Deployed use case identifier.')
output USE_CASE string = isAvm ? avmDeployment!.outputs.USE_CASE : bicepDeployment!.outputs.USE_CASE

@description('Azure AI Search endpoint.')
output AZURE_AI_SEARCH_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_ENDPOINT : bicepDeployment!.outputs.AZURE_AI_SEARCH_ENDPOINT

@description('Azure AI Search index name.')
output AZURE_AI_SEARCH_INDEX string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX

@description('Azure AI Search service name.')
output AZURE_AI_SEARCH_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_NAME : bicepDeployment!.outputs.AZURE_AI_SEARCH_NAME

@description('Search data folder path.')
output SEARCH_DATA_FOLDER string = isAvm ? avmDeployment!.outputs.SEARCH_DATA_FOLDER : bicepDeployment!.outputs.SEARCH_DATA_FOLDER

@description('AI Search connection name.')
output AZURE_AI_SEARCH_CONNECTION_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_CONNECTION_NAME : bicepDeployment!.outputs.AZURE_AI_SEARCH_CONNECTION_NAME

@description('AI Search connection ID.')
output AZURE_AI_SEARCH_CONNECTION_ID string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_CONNECTION_ID : bicepDeployment!.outputs.AZURE_AI_SEARCH_CONNECTION_ID

@description('AI Foundry project endpoint.')
output AZURE_AI_PROJECT_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_AI_PROJECT_ENDPOINT : bicepDeployment!.outputs.AZURE_AI_PROJECT_ENDPOINT

@description('AI Foundry resource ID.')
output AI_FOUNDRY_RESOURCE_ID string = isAvm ? avmDeployment!.outputs.AI_FOUNDRY_RESOURCE_ID : bicepDeployment!.outputs.AI_FOUNDRY_RESOURCE_ID

@description('AI Foundry project name.')
output AZURE_AI_PROJECT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_PROJECT_NAME : bicepDeployment!.outputs.AZURE_AI_PROJECT_NAME

@description('AI Services resource name.')
output AI_SERVICE_NAME string = isAvm ? avmDeployment!.outputs.AI_SERVICE_NAME : bicepDeployment!.outputs.AI_SERVICE_NAME

@description('AI Project identity principal ID.')
output FOUNDRY_PROJECT_PID string = isAvm ? avmDeployment!.outputs.FOUNDRY_PROJECT_PID : bicepDeployment!.outputs.FOUNDRY_PROJECT_PID

@description('Chat history enabled flag.')
output USE_CHAT_HISTORY_ENABLED string = isAvm ? avmDeployment!.outputs.USE_CHAT_HISTORY_ENABLED : bicepDeployment!.outputs.USE_CHAT_HISTORY_ENABLED

@description('Backend runtime stack.')
output BACKEND_RUNTIME_STACK string = isAvm ? avmDeployment!.outputs.BACKEND_RUNTIME_STACK : bicepDeployment!.outputs.BACKEND_RUNTIME_STACK

@description('Deploy app flag.')
output AZURE_ENV_DEPLOY_APP bool = isAvm ? avmDeployment!.outputs.AZURE_ENV_DEPLOY_APP : bicepDeployment!.outputs.AZURE_ENV_DEPLOY_APP

@description('Azure-only mode flag.')
output AZURE_ENV_ONLY bool = isAvm ? avmDeployment!.outputs.AZURE_ENV_ONLY : bicepDeployment!.outputs.AZURE_ENV_ONLY

@description('User access token forwarding flag.')
output USE_USER_ACCESS_TOKEN string = isAvm ? avmDeployment!.outputs.USE_USER_ACCESS_TOKEN : bicepDeployment!.outputs.USE_USER_ACCESS_TOKEN

@description('The resource ID of the Fabric capacity.')
output AZURE_FABRIC_CAPACITY_RESOURCE_ID string = isAvm ? avmDeployment!.outputs.AZURE_FABRIC_CAPACITY_RESOURCE_ID : bicepDeployment!.outputs.AZURE_FABRIC_CAPACITY_RESOURCE_ID

@description('The name of the Fabric capacity resource.')
output AZURE_FABRIC_CAPACITY_NAME string = isAvm ? avmDeployment!.outputs.AZURE_FABRIC_CAPACITY_NAME : bicepDeployment!.outputs.AZURE_FABRIC_CAPACITY_NAME

@description('The identities assigned as Fabric Capacity Admin members.')
output FABRIC_ADMIN_MEMBERS array = isAvm ? avmDeployment!.outputs.FABRIC_ADMIN_MEMBERS : bicepDeployment!.outputs.FABRIC_ADMIN_MEMBERS

@description('The unique solution suffix of the deployed resources.')
output SOLUTION_SUFFIX string = isAvm ? avmDeployment!.outputs.SOLUTION_SUFFIX : bicepDeployment!.outputs.SOLUTION_SUFFIX

@description('Whether Fabric workspace creation is enabled.')
output CREATE_FABRIC_WORKSPACE bool = createFabricWorkspace

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
param solutionName string = 'agenticappudf'

@maxLength(5)
@description('Optional. A unique text suffix appended to resource names for uniqueness.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@description('Optional. Primary Azure region for resource deployment.')
param location string = resourceGroup().location

@description('Optional. Secondary location for database resources (example: eastus2).')
param secondaryLocation string = 'eastus2'

@allowed(['australiaeast', 'eastus', 'eastus2', 'francecentral', 'japaneast', 'swedencentral', 'uksouth', 'westus', 'westus3'])
@metadata({
  azd:{
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1-mini,100'
      'OpenAI.GlobalStandard.text-embedding-3-small,80'
    ]
  }
})
@description('Required. Location for AI Foundry and model deployments.')
param azureAiServiceLocation string

@description('Optional. Location for AI Search service deployment.')
param searchServiceLocation string = location

// ============================================================================
// Parameters — AI Configuration
// ============================================================================

@allowed(['Standard', 'GlobalStandard'])
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

@allowed(['text-embedding-3-small'])
@description('Optional. Name of the Text Embedding model to deploy.')
param embeddingModel string = 'text-embedding-3-small'

@minValue(10)
@description('Optional. Capacity of the Embedding Model deployment.')
param embeddingDeploymentCapacity int = 80

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
@description('Optional. App Service Plan SKU (used by AVM flavors).')
param appServicePlanSku string = 'B2'

// ============================================================================
// Parameters — Feature Flags
// ============================================================================

@description('Optional. Enable chat history storage.')
param useChatHistoryEnabled bool = true

@description('Optional. Enable user access token forwarding.')
param useUserAccessToken bool = false

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
param deployingUserPrincipalType string = 'User'

// ============================================================================
// Parameters — App Configuration
// ============================================================================


@description('Optional. Primary title in the web app header.')
param appTitlePrimary string = 'Contoso'

@description('Optional. Secondary title in the web app header.')
param appTitleSecondary string = '| Unified Data Analysis Agents'

// ============================================================================
// Parameters — AVM-specific (ignored when deploymentFlavor = 'bicep')
// ============================================================================

@description('Optional. Tags to apply to all resources (AVM only).')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for AVM modules.')
param enableTelemetry bool = true

@description('Optional. Enable monitoring (Log Analytics, App Insights, diagnostic settings).')
param enableMonitoring bool = false

@description('Optional. Enable private networking (VNet, private endpoints, DNS zones).')
param enablePrivateNetworking bool = false

@description('Optional. Enable scalability features (zone redundant App Service Plan).')
param enableScalability bool = false

@description('Optional. Enable redundancy (zone redundant Cosmos DB, multi-region failover).')
param enableRedundancy bool = false

// ============================================================================
// Parameters — Fabric Capacity
// ============================================================================

@description('Optional. Existing Fabric Workspace ID to reuse. If empty, a new workspace will be created during post-provision.')
param fabricWorkspaceId string = ''

var createFabricWorkspace = empty(fabricWorkspaceId)

@description('Optional. Name of an existing Fabric capacity to reuse. Empty auto-creates when conditions are met.')
param azureFabricCapacityName string = ''

@allowed(['F2', 'F4', 'F8', 'F16', 'F32', 'F64', 'F128', 'F256', 'F512', 'F1024', 'F2048'])
@description('Optional. SKU tier of the Fabric capacity resource.')
param fabricCapacitySku string = 'F2'

@description('Optional. Additional user/service principal object IDs to assign as Fabric Capacity admins.')
param fabricAdminMembers array = []

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
    useChatHistoryEnabled: useChatHistoryEnabled
    useUserAccessToken: useUserAccessToken
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    deployingUserPrincipalType: deployingUserPrincipalType
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
    useChatHistoryEnabled: useChatHistoryEnabled
    useUserAccessToken: useUserAccessToken
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    deployingUserPrincipalType: deployingUserPrincipalType
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

@description('Frontend web app resource name.')
output WEB_APP_NAME string = isAvm ? avmDeployment!.outputs.WEB_APP_NAME : bicepDeployment!.outputs.WEB_APP_NAME

@description('Frontend web application URL.')
output WEB_APP_URL string = isAvm ? avmDeployment!.outputs.WEB_APP_URL : bicepDeployment!.outputs.WEB_APP_URL

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

@description('The Fabric Workspace ID (passed through or empty if auto-creating).')
output FABRIC_WORKSPACE_ID string = fabricWorkspaceId

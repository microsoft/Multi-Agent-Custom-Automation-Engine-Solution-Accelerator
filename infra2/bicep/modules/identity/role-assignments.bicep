// ============================================================================
// Module: Role Assignments (centralized — all cross-service + data plane RBAC)
// Description: RG-level, cross-service, and data-plane role assignments.
//              One place to audit "who has access to what".
// ============================================================================
targetScope = 'resourceGroup'

// ============================================================================
// Parameters
// ============================================================================

@description('The name of the solution, used as a base for naming all resources.')
param solutionName string

@description('The resource ID of an existing Azure AI Foundry project. If provided, the existing project will be used instead of creating a new one.')
param existingFoundryProjectResourceId string = ''

@description('The name of the Azure AI Services account.')
param aiFoundryName string = ''

@description('The name of the Azure AI Search service.')
param aiSearchName string = ''

@description('The name of the storage account.')
param storageAccountName string = ''

@description('The principal ID of the AI Foundry project managed identity for newly created projects.')
param aiProjectPrincipalId string = ''

@description('The principal ID of the AI Foundry project managed identity for existing projects (from identity setup).')
param existingAiProjectPrincipalId string = ''

@description('The principal ID of the AI Search system-assigned managed identity.')
param searchPrincipalId string = ''

@description('The principal ID of the deploying user.')
param deployingUserPrincipalId string = ''

@description('The principal type of the deploying user. Use ServicePrincipal for CI/CD pipelines with OIDC.')
@allowed(['User', 'ServicePrincipal'])
param deployingUserPrincipalType string = 'User'

@description('The system-assigned principal ID of the backend API App Service (Python).')
param backendAppPrincipalId string = ''

@description('The system-assigned principal ID of the backend CSAPI App Service (.NET).')
param backendCsApiPrincipalId string = ''

@description('The name of the Cosmos DB account (for chat history).')
param cosmosAccountName string = ''

// ============================================================================
// Derived Variables
// ============================================================================

var useExistingProject = !empty(existingFoundryProjectResourceId)
var existingAIServicesName = useExistingProject ? split(existingFoundryProjectResourceId, '/')[8] : ''
var existingAIProjectName = useExistingProject ? split(existingFoundryProjectResourceId, '/')[10] : ''
var existingAIServiceSubscription = useExistingProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var existingAIServiceResourceGroup = useExistingProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name

// Resolve the active backend principal ID (whichever runtime is deployed)
var activeBackendPrincipalId = !empty(backendAppPrincipalId) ? backendAppPrincipalId : backendCsApiPrincipalId

// ============================================================================
// Existing Resource References
// ============================================================================

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = if (!empty(aiFoundryName) && !useExistingProject) {
  name: aiFoundryName
}

resource aiSearch 'Microsoft.Search/searchServices@2025-05-01' existing = if (!empty(aiSearchName)) {
  name: aiSearchName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-08-01' existing = if (!empty(storageAccountName)) {
  name: storageAccountName
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2025-10-15' existing = if (!empty(cosmosAccountName)) {
  name: cosmosAccountName
}

resource cosmosContributorRoleDef 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2025-10-15' existing = if (!empty(cosmosAccountName)) {
  parent: cosmos
  name: '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
}

// ╔══════════════════════════════════════════════════════════════╗
// ║  ROLE DEFINITIONS                                           ║
// ╚══════════════════════════════════════════════════════════════╝

resource azureAIUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
}

resource cognitiveServicesOpenAIUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
}

resource cognitiveServicesUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
}

resource searchIndexDataReader 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '1407120a-92aa-4202-b7e9-c0e197c71c8f' // Search Index Data Reader
}

resource searchServiceContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
}

resource searchIndexDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
}

resource storageBlobDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
}

resource storageBlobDataReader 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // Storage Blob Data Reader
}

// ╔══════════════════════════════════════════════════════════════╗
// ║  1. AI SERVICES ROLE ASSIGNMENTS                            ║
// ║     Cross-service roles scoped to AI Foundry account        ║
// ╚══════════════════════════════════════════════════════════════╝

// --- AI Search → AI Services (new project, same RG) ---

// AI Search → Cognitive Services OpenAI User on AI Services
resource assignOpenAIRoleToAISearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(searchPrincipalId) && !empty(aiFoundryName)) {
  name: guid(resourceGroup().id, aiServices.id, cognitiveServicesOpenAIUser.id)
  scope: aiServices
  properties: {
    principalId: searchPrincipalId
    roleDefinitionId: cognitiveServicesOpenAIUser.id
    principalType: 'ServicePrincipal'
  }
}

// --- Backend App Service → AI Services (cross-scope, handles both new + existing) ---

// Backend App Service → Foundry User on AI Services (cross-scope)
module assignAiUserToBackend './cross-scope-role-assignment.bicep' = if (!empty(activeBackendPrincipalId)) {
  name: 'assignAiUserRoleToBackend'
  scope: resourceGroup(existingAIServiceSubscription, existingAIServiceResourceGroup)
  params: {
    principalId: activeBackendPrincipalId
    roleDefinitionId: azureAIUser.id
    roleAssignmentName: guid(solutionName, 'backend', useExistingProject ? existingAIServicesName : aiFoundryName, azureAIUser.id)
    aiFoundryName: useExistingProject ? existingAIServicesName : aiFoundryName
  }
}

// --- AI Search → existing AI Services (cross-scope) ---

// AI Search → Cognitive Services OpenAI User on existing AI Services (cross-scope)
module assignOpenAIToSearchExisting './cross-scope-role-assignment.bicep' = if (useExistingProject && !empty(searchPrincipalId) && !empty(aiSearchName)) {
  name: 'assignOpenAIRoleToAISearchExisting'
  scope: resourceGroup(existingAIServiceSubscription, existingAIServiceResourceGroup)
  params: {
    principalId: searchPrincipalId
    roleDefinitionId: cognitiveServicesOpenAIUser.id
    roleAssignmentName: guid(resourceGroup().id, aiSearch.id, cognitiveServicesOpenAIUser.id, 'openai-foundry')
    aiFoundryName: existingAIServicesName
  }
}

// ╔══════════════════════════════════════════════════════════════╗
// ║  2. SEARCH SERVICE ROLE ASSIGNMENTS                         ║
// ║     AI Project and Backend identities → AI Search           ║
// ╚══════════════════════════════════════════════════════════════╝

// --- AI Project (new) → AI Search ---

// AI Project → Search Index Data Reader on AI Search
resource assignSearchIndexDataReaderToAiProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(aiProjectPrincipalId) && !empty(aiSearchName)) {
  name: guid(resourceGroup().id, aiProjectPrincipalId, searchIndexDataReader.id)
  scope: aiSearch
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: searchIndexDataReader.id
    principalType: 'ServicePrincipal'
  }
}

// AI Project → Search Service Contributor on AI Search
resource assignSearchServiceContributorToAiProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(aiProjectPrincipalId) && !empty(aiSearchName)) {
  name: guid(resourceGroup().id, aiProjectPrincipalId, searchServiceContributor.id)
  scope: aiSearch
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: searchServiceContributor.id
    principalType: 'ServicePrincipal'
  }
}

// --- AI Project (existing) → AI Search ---

// Existing AI Project → Search Index Data Reader on AI Search
resource assignSearchIndexDataReaderToExistingAiProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingProject && !empty(aiSearchName)) {
  name: guid(resourceGroup().id, existingAIProjectName, searchIndexDataReader.id, 'Existing')
  scope: aiSearch
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: searchIndexDataReader.id
    principalType: 'ServicePrincipal'
  }
}

// Existing AI Project → Search Service Contributor on AI Search
resource assignSearchServiceContributorToExistingAiProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingProject && !empty(aiSearchName)) {
  name: guid(resourceGroup().id, existingAIProjectName, searchServiceContributor.id, 'Existing')
  scope: aiSearch
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: searchServiceContributor.id
    principalType: 'ServicePrincipal'
  }
}

// --- Backend App Service → AI Search ---

// Backend App Service → Search Index Data Reader on AI Search
resource assignSearchIndexDataReaderToApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(activeBackendPrincipalId) && !empty(aiSearchName)) {
  name: guid(solutionName, aiSearchName, searchIndexDataReader.id, activeBackendPrincipalId)
  scope: aiSearch
  properties: {
    principalId: activeBackendPrincipalId
    roleDefinitionId: searchIndexDataReader.id
    principalType: 'ServicePrincipal'
  }
}

// ╔══════════════════════════════════════════════════════════════╗
// ║  3. STORAGE ROLE ASSIGNMENTS                                ║
// ║     AI Project, AI Search, and Existing Project → Storage   ║
// ╚══════════════════════════════════════════════════════════════╝

// --- AI Project (new) → Storage ---

// AI Project → Storage Blob Data Contributor
resource projectStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(aiProjectPrincipalId) && !empty(storageAccountName)) {
  scope: storageAccount
  name: guid(storageAccount.id, aiProjectPrincipalId, storageBlobDataContributor.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: storageBlobDataContributor.id
    principalType: 'ServicePrincipal'
  }
}

// AI Project → Storage Blob Data Reader
resource projectStorageBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(aiProjectPrincipalId) && !empty(storageAccountName)) {
  scope: storageAccount
  name: guid(storageAccount.id, aiProjectPrincipalId, storageBlobDataReader.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: storageBlobDataReader.id
    principalType: 'ServicePrincipal'
  }
}

// --- AI Project (existing) → Storage ---

// Existing AI Project → Storage Blob Data Contributor
resource existingProjectStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingProject && !empty(storageAccountName)) {
  scope: storageAccount
  name: guid(storageAccount.id, existingAIProjectName, storageBlobDataContributor.id)
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: storageBlobDataContributor.id
    principalType: 'ServicePrincipal'
  }
}

// Existing AI Project → Storage Blob Data Reader
resource existingProjectStorageBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingProject && !empty(storageAccountName)) {
  scope: storageAccount
  name: guid(storageAccount.id, existingAIProjectName, storageBlobDataReader.id)
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: storageBlobDataReader.id
    principalType: 'ServicePrincipal'
  }
}

// --- AI Search → Storage ---

// AI Search → Storage Blob Data Reader
resource searchStorageBlobDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(searchPrincipalId) && !empty(storageAccountName)) {
  scope: storageAccount
  name: guid(storageAccount.id, searchPrincipalId, storageBlobDataReader.id)
  properties: {
    principalId: searchPrincipalId
    roleDefinitionId: storageBlobDataReader.id
    principalType: 'ServicePrincipal'
  }
}

// ╔══════════════════════════════════════════════════════════════╗
// ║  4. COSMOS DB ROLE ASSIGNMENTS                              ║
// ║     Backend App Service → Cosmos DB (data-plane)            ║
// ╚══════════════════════════════════════════════════════════════╝

// Backend App Service → Cosmos DB Built-in Data Contributor
resource backendCosmosContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-10-15' = if (!empty(activeBackendPrincipalId) && !empty(cosmosAccountName)) {
  parent: cosmos
  name: guid(cosmosContributorRoleDef.id, cosmos.id, activeBackendPrincipalId)
  properties: {
    principalId: activeBackendPrincipalId
    roleDefinitionId: cosmosContributorRoleDef.id
    scope: cosmos.id
  }
}

// ╔══════════════════════════════════════════════════════════════╗
// ║  5. DEPLOYER / USER ACCESS ROLE ASSIGNMENTS                 ║
// ║     Deploying user → AI Services, Search, Storage           ║
// ╚══════════════════════════════════════════════════════════════╝

// --- Deployer → AI Services (new project, same RG) ---

// Deploying User → Cognitive Services User on AI Services
resource userAIServicesAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(deployingUserPrincipalId) && !empty(aiFoundryName)) {
  scope: aiServices
  name: guid(aiServices.id, deployingUserPrincipalId, cognitiveServicesUser.id)
  properties: {
    principalId: deployingUserPrincipalId
    roleDefinitionId: cognitiveServicesUser.id
    principalType: deployingUserPrincipalType
  }
}

// Deploying User → Foundry User on AI Services
resource userAzureAIAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingProject && !empty(deployingUserPrincipalId) && !empty(aiFoundryName)) {
  scope: aiServices
  name: guid(aiServices.id, deployingUserPrincipalId, azureAIUser.id)
  properties: {
    principalId: deployingUserPrincipalId
    roleDefinitionId: azureAIUser.id
    principalType: deployingUserPrincipalType
  }
}

// --- Deployer → AI Search ---

// Deploying User → Search Index Data Contributor on AI Search
resource userSearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployingUserPrincipalId) && !empty(aiSearchName)) {
  scope: aiSearch
  name: guid(aiSearch.id, deployingUserPrincipalId, searchIndexDataContributor.id)
  properties: {
    principalId: deployingUserPrincipalId
    roleDefinitionId: searchIndexDataContributor.id
    principalType: deployingUserPrincipalType
  }
}

// Deploying User → Search Service Contributor on AI Search
resource userSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployingUserPrincipalId) && !empty(aiSearchName)) {
  scope: aiSearch
  name: guid(aiSearch.id, deployingUserPrincipalId, searchServiceContributor.id)
  properties: {
    principalId: deployingUserPrincipalId
    roleDefinitionId: searchServiceContributor.id
    principalType: deployingUserPrincipalType
  }
}

// --- Deployer → Storage ---

// Deploying User → Storage Blob Data Contributor
resource userStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployingUserPrincipalId) && !empty(storageAccountName)) {
  scope: storageAccount
  name: guid(storageAccount.id, deployingUserPrincipalId, storageBlobDataContributor.id)
  properties: {
    principalId: deployingUserPrincipalId
    roleDefinitionId: storageBlobDataContributor.id
    principalType: deployingUserPrincipalType
  }
}

// --- Deployer → existing AI Services (cross-scope) ---
// NOTE: These roles are now assigned via 00_build_solution.py to avoid conflicts
// when the deployer already has the roles on the existing AI Foundry.

// ╔══════════════════════════════════════════════════════════════╗
// ║  OUTPUTS                                                    ║
// ╚══════════════════════════════════════════════════════════════╝

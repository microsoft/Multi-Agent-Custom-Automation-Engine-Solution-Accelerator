// ============================================================================
// Module: Role Assignments (centralized — all cross-service + data plane RBAC)
// Description: RG-level, cross-service, and data-plane role assignments.
//              One place to audit "who has access to what".
// ============================================================================

// ============================================================================
// Parameters
// ============================================================================

@description('Solution name suffix for generating unique role assignment GUIDs.')
param solutionName string = ''

@description('Whether to use an existing AI project (true) or create new (false).')
param useExistingAIProject bool = false

@description('Resource ID of the existing AI project (for deriving AI Services name/sub/RG).')
param existingFoundryProjectResourceId string = ''

// --- Identity Principal IDs ---

@description('Principal ID of the AI project identity.')
param aiProjectPrincipalId string = ''

@description('Principal ID of the existing AI project identity (for cross-service roles).')
param existingAiProjectPrincipalId string = ''

@description('Principal ID of the AI Search identity.')
param aiSearchPrincipalId string = ''

@description('Principal ID of the user-assigned managed identity (empty if not deployed).')
param userAssignedManagedIdentityPrincipalId string = ''

@description('Principal ID of the deploying user (for user access roles).')
param deployerPrincipalId string = ''

@description('Principal type of the deploying user.')
@allowed(['User', 'ServicePrincipal'])
param deployerPrincipalType string = 'User'

// --- Resource References ---

@description('Resource ID of the AI Foundry account (empty if not deployed — new project path).')
param aiFoundryResourceId string = ''

@description('Resource ID of the AI Search service (empty if not deployed).')
param aiSearchResourceId string = ''

@description('Resource ID of the Storage Account (empty if not deployed).')
param storageAccountResourceId string = ''

@description('Name of the Cosmos DB account (empty if not deployed).')
param cosmosDbAccountName string = ''

// ============================================================================
// Derived Variables
// ============================================================================

var existingAIFoundryName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[8] : ''
var existingAIFoundrySubscription = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var existingAIFoundryResourceGroup = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name

// ============================================================================
// Role Definitions
// ============================================================================

var roleDefinitions = {
  azureAiUser: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  cognitiveServicesOpenAIContributor: 'a001fd3d-188f-4b5d-821b-7da978bf7442'
  searchIndexDataReader: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  searchIndexDataContributor: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchServiceContributor: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageBlobDataReader: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
}

// ============================================================================
// Existing Resource References
// ============================================================================

resource aiFoundryAccount 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = if (!empty(aiFoundryResourceId)) {
  name: last(split(aiFoundryResourceId, '/'))
}

resource aiSearchService 'Microsoft.Search/searchServices@2025-05-01' existing = if (!empty(aiSearchResourceId)) {
  name: last(split(aiSearchResourceId, '/'))
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-08-01' existing = if (!empty(storageAccountResourceId)) {
  name: last(split(storageAccountResourceId, '/'))
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2025-10-15' existing = if (!empty(cosmosDbAccountName)) {
  name: cosmosDbAccountName
}

resource cosmosContributorRoleDefinition 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2025-10-15' existing = if (!empty(cosmosDbAccountName)) {
  parent: cosmosAccount
  name: '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
}

// ============================================================================
// 1. AI SERVICES ROLE ASSIGNMENTS
//    Cross-service roles scoped to AI Foundry account
// ============================================================================

// AI Search → Cognitive Services OpenAI User on AI Foundry (new project, same RG)
resource assignOpenAIRoleToAISearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiSearchPrincipalId) && !empty(aiFoundryResourceId)) {
  name: guid(resourceGroup().id, aiFoundryAccount.id, roleDefinitions.cognitiveServicesOpenAIUser, 'search-openai')
  scope: aiFoundryAccount
  properties: {
    principalId: aiSearchPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    principalType: 'ServicePrincipal'
  }
}

// AI Search → Cognitive Services OpenAI User on existing AI Foundry (cross-scope)
module assignOpenAIToSearchExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(aiSearchPrincipalId)) {
  name: 'assignOpenAIRoleToAISearchExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: aiSearchPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    roleAssignmentName: guid(solutionName, 'search-openai', existingAIFoundryName, roleDefinitions.cognitiveServicesOpenAIUser)
    aiFoundryName: existingAIFoundryName
  }
}

// User-Assigned Managed Identity → Foundry User on AI Foundry (new project, same RG)
resource userAssignedManagedIdentityAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: guid(resourceGroup().id, userAssignedManagedIdentityPrincipalId, roleDefinitions.azureAiUser, 'user-assigned-managed-identity-ai-user')
  scope: aiFoundryAccount
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: 'ServicePrincipal'
  }
}

// User-Assigned Managed Identity → Cognitive Services OpenAI Contributor on AI Foundry (new project, same RG)
// Extended as per accelerator need
resource userAssignedManagedIdentityOpenAIContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: guid(resourceGroup().id, userAssignedManagedIdentityPrincipalId, roleDefinitions.cognitiveServicesOpenAIContributor, 'user-assigned-managed-identity-openai')
  scope: aiFoundryAccount
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIContributor)
    principalType: 'ServicePrincipal'
  }
}

// User-Assigned Managed Identity → Foundry User on existing AI Foundry (cross-scope)
module userAssignedManagedIdentityAiUserExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: 'assignAiUserRoleToBackendExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    roleAssignmentName: guid(solutionName, 'backend-aiuser', existingAIFoundryName, roleDefinitions.azureAiUser)
    aiFoundryName: existingAIFoundryName
  }
}

// User-Assigned Managed Identity → Cognitive Services OpenAI Contributor on existing AI Foundry (cross-scope)
// Extended as per accelerator need
module userAssignedManagedIdentityOpenAIContributorExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: 'assignOpenAIContributorRoleToBackendExisting'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIContributor)
    roleAssignmentName: guid(solutionName, 'backend-openai', existingAIFoundryName, roleDefinitions.cognitiveServicesOpenAIContributor)
    aiFoundryName: existingAIFoundryName
  }
}

// ============================================================================
// 2. SEARCH SERVICE ROLE ASSIGNMENTS
//    AI Project and Backend identities → AI Search
// ============================================================================

// AI Project → Search Index Data Reader on AI Search (new project)
resource projectSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(aiProjectPrincipalId)) {
  name: guid(resourceGroup().id, aiProjectPrincipalId, roleDefinitions.searchIndexDataReader, 'project-search')
  scope: aiSearchService
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataReader)
    principalType: 'ServicePrincipal'
  }
}

// AI Project → Search Service Contributor on AI Search (new project)
resource projectSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(aiProjectPrincipalId)) {
  name: guid(resourceGroup().id, aiProjectPrincipalId, roleDefinitions.searchServiceContributor, 'project-search')
  scope: aiSearchService
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: 'ServicePrincipal'
  }
}

// Existing AI Project → Search Index Data Reader on AI Search
resource existingProjectSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingAIProject && !empty(aiSearchResourceId) && !empty(existingAiProjectPrincipalId)) {
  name: guid(resourceGroup().id, existingAiProjectPrincipalId, roleDefinitions.searchIndexDataReader, 'existing-project-search')
  scope: aiSearchService
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataReader)
    principalType: 'ServicePrincipal'
  }
}

// Existing AI Project → Search Service Contributor on AI Search
resource existingProjectSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingAIProject && !empty(aiSearchResourceId) && !empty(existingAiProjectPrincipalId)) {
  name: guid(resourceGroup().id, existingAiProjectPrincipalId, roleDefinitions.searchServiceContributor, 'existing-project-search')
  scope: aiSearchService
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: 'ServicePrincipal'
  }
}

// User-Assigned Managed Identity → Search Index Data Reader on AI Search
resource userAssignedManagedIdentitySearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: guid(resourceGroup().id, userAssignedManagedIdentityPrincipalId, roleDefinitions.searchIndexDataReader, 'user-assigned-managed-identity-search')
  scope: aiSearchService
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataReader)
    principalType: 'ServicePrincipal'
  }
}

// User-Assigned Managed Identity → Search Index Data Contributor on AI Search
// Extended as per accelerator need
resource userAssignedManagedIdentitySearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: guid(resourceGroup().id, userAssignedManagedIdentityPrincipalId, roleDefinitions.searchIndexDataContributor, 'user-assigned-managed-identity-search')
  scope: aiSearchService
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// User-Assigned Managed Identity → Search Service Contributor on AI Search
// Extended as per accelerator need
resource userAssignedManagedIdentitySearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: guid(resourceGroup().id, userAssignedManagedIdentityPrincipalId, roleDefinitions.searchServiceContributor, 'user-assigned-managed-identity-search-service')
  scope: aiSearchService
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// 3. STORAGE ROLE ASSIGNMENTS
//    AI Project, AI Search, and Existing Project identities → Storage
// ============================================================================

// AI Project → Storage Blob Data Contributor (new project)
resource projectStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(aiProjectPrincipalId)) {
  name: guid(resourceGroup().id, aiProjectPrincipalId, roleDefinitions.storageBlobDataContributor, 'project-storage')
  scope: storageAccount
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// User-Assigned Managed Identity → Storage Blob Data Contributor on Storage Account
// Extended as per accelerator need
resource userAssignedManagedIdentityStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(userAssignedManagedIdentityPrincipalId)) {
  name: guid(resourceGroup().id, userAssignedManagedIdentityPrincipalId, roleDefinitions.storageBlobDataContributor, 'user-assigned-managed-identity-storage')
  scope: storageAccount
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// AI Project → Storage Blob Data Reader (new project)
resource projectStorageReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(aiProjectPrincipalId)) {
  name: guid(resourceGroup().id, aiProjectPrincipalId, roleDefinitions.storageBlobDataReader, 'project-storage')
  scope: storageAccount
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataReader)
    principalType: 'ServicePrincipal'
  }
}

// Existing AI Project → Storage Blob Data Contributor
resource existingProjectStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingAIProject && !empty(storageAccountResourceId) && !empty(existingAiProjectPrincipalId)) {
  name: guid(resourceGroup().id, existingAiProjectPrincipalId, roleDefinitions.storageBlobDataContributor, 'existing-project-storage')
  scope: storageAccount
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}

// Existing AI Project → Storage Blob Data Reader
resource existingProjectStorageReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (useExistingAIProject && !empty(storageAccountResourceId) && !empty(existingAiProjectPrincipalId)) {
  name: guid(resourceGroup().id, existingAiProjectPrincipalId, roleDefinitions.storageBlobDataReader, 'existing-project-storage')
  scope: storageAccount
  properties: {
    principalId: existingAiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataReader)
    principalType: 'ServicePrincipal'
  }
}

// AI Search → Storage Blob Data Reader
resource searchStorageReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(storageAccountResourceId) && !empty(aiSearchPrincipalId)) {
  name: guid(resourceGroup().id, aiSearchPrincipalId, roleDefinitions.storageBlobDataReader, 'search-storage')
  scope: storageAccount
  properties: {
    principalId: aiSearchPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataReader)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// 4. COSMOS DB ROLE ASSIGNMENTS
//    User-Assigned Managed Identity → Cosmos DB (data-plane, uses sqlRoleAssignments)
// ============================================================================

resource userAssignedManagedIdentityCosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-10-15' = if (!empty(cosmosDbAccountName) && !empty(userAssignedManagedIdentityPrincipalId)) {
  parent: cosmosAccount
  name: guid(cosmosContributorRoleDefinition.id, cosmosAccount.id, userAssignedManagedIdentityPrincipalId)
  properties: {
    principalId: userAssignedManagedIdentityPrincipalId
    roleDefinitionId: cosmosContributorRoleDefinition.id
    scope: cosmosAccount.id
  }
}

// ============================================================================
// 5. DEPLOYER (USER) ROLE ASSIGNMENTS
//    Deploying user → AI Services, Search, Storage (Bicep-only)
// ============================================================================

// Deploying User → Cognitive Services User on AI Services
resource deployerAiServicesAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(deployerPrincipalId) && !empty(aiFoundryResourceId)) {
  scope: aiFoundryAccount
  name: guid(aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.cognitiveServicesUser)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Foundry User on AI Services
resource deployerAzureAIAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(deployerPrincipalId) && !empty(aiFoundryResourceId)) {
  scope: aiFoundryAccount
  name: guid(aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.azureAiUser)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Search Index Data Contributor on AI Search
resource deployerSearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(aiSearchResourceId)) {
  scope: aiSearchService
  name: guid(aiSearchService.id, deployerPrincipalId, roleDefinitions.searchIndexDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Search Service Contributor on AI Search
resource deployerSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(aiSearchResourceId)) {
  scope: aiSearchService
  name: guid(aiSearchService.id, deployerPrincipalId, roleDefinitions.searchServiceContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Storage Blob Data Contributor
resource deployerStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(storageAccountResourceId)) {
  scope: storageAccount
  name: guid(storageAccount.id, deployerPrincipalId, roleDefinitions.storageBlobDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Cosmos DB Contributor (data-plane, uses sqlRoleAssignments)
resource deployerCosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-10-15' = if (!empty(cosmosDbAccountName) && !empty(deployerPrincipalId)) {
  parent: cosmosAccount
  name: guid(cosmosContributorRoleDefinition.id, cosmosAccount.id, deployerPrincipalId)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: cosmosContributorRoleDefinition.id
    scope: cosmosAccount.id
  }
}

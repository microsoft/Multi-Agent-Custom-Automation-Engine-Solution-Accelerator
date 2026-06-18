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

@description('Principal ID of the AI project identity (works for both new and existing projects).')
param aiProjectPrincipalId string = ''

@description('Principal ID of the AI Search identity.')
param aiSearchPrincipalId string = ''

@description('Principal ID of the user-assigned managed identity (empty if not deployed). Kept for backward compatibility; prefer workloadPrincipalIds.')
param userAssignedManagedIdentityPrincipalId string = ''

@description('Optional. List of workload identity principal IDs (e.g. system-assigned identities of backend, MCP, and frontend hosts) that should receive the same data-plane roles previously granted to the UAMI. When non-empty, this list takes precedence over userAssignedManagedIdentityPrincipalId.')
param workloadPrincipalIds array = []

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

@description('Resource ID of the Container Registry (empty if not deployed).')
param containerRegistryResourceId string = ''

// ============================================================================
// Derived Variables
// ============================================================================

var existingAIFoundryName = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[8] : ''
var existingAIFoundrySubscription = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[2] : subscription().subscriptionId
var existingAIFoundryResourceGroup = useExistingAIProject ? split(existingFoundryProjectResourceId, '/')[4] : resourceGroup().name

// Unified workload identity list — supports both:
//   - UAMI flavor (today): caller passes userAssignedManagedIdentityPrincipalId
//   - SAMI flavor (future): caller passes workloadPrincipalIds = [<backend.identity.principalId>, <mcp.identity.principalId>, <frontend.identity.principalId>]
// If workloadPrincipalIds is provided, it wins. Otherwise we wrap the legacy UAMI principal into a single-element list.
var workloadPrincipals = !empty(workloadPrincipalIds) ? workloadPrincipalIds : (empty(userAssignedManagedIdentityPrincipalId) ? [] : [userAssignedManagedIdentityPrincipalId])

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
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
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

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = if (!empty(containerRegistryResourceId)) {
  name: last(split(containerRegistryResourceId, '/'))
}

// ============================================================================
// 1. AI SERVICES ROLE ASSIGNMENTS
//    Cross-service roles scoped to AI Foundry account
// ============================================================================

// AI Search → Cognitive Services OpenAI User on AI Foundry (new project, same RG)
resource assignOpenAIRoleToAISearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiSearchPrincipalId) && !empty(aiFoundryResourceId)) {
  name: guid(solutionName, aiFoundryAccount.id, aiSearchPrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
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
    roleAssignmentName: guid(solutionName, existingAIFoundryName, aiSearchPrincipalId, roleDefinitions.cognitiveServicesOpenAIUser)
    aiFoundryName: existingAIFoundryName
  }
}

// Workload identities (UAMI or SAMI) → Foundry User on AI Foundry (new project, same RG)
resource workloadAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in workloadPrincipals: if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(principalId)) {
  name: guid(solutionName, aiFoundryAccount.id, principalId, roleDefinitions.azureAiUser)
  scope: aiFoundryAccount
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: 'ServicePrincipal'
  }
}]

// Workload identities (UAMI or SAMI) → Cognitive Services OpenAI Contributor on AI Foundry (new project, same RG)
// Extended as per accelerator need
resource workloadOpenAIContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in workloadPrincipals: if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(principalId)) {
  name: guid(solutionName, aiFoundryAccount.id, principalId, roleDefinitions.cognitiveServicesOpenAIContributor)
  scope: aiFoundryAccount
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIContributor)
    principalType: 'ServicePrincipal'
  }
}]

// Workload identities (UAMI or SAMI) → Foundry User on existing AI Foundry (cross-scope)
module workloadAiUserExisting './cross-scope-role-assignment.bicep' = [for (principalId, i) in workloadPrincipals: if (useExistingAIProject && !empty(principalId)) {
  name: 'assignAiUserRoleToWorkloadExisting-${i}'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, principalId, roleDefinitions.azureAiUser)
    aiFoundryName: existingAIFoundryName
  }
}]

// Workload identities (UAMI or SAMI) → Cognitive Services OpenAI Contributor on existing AI Foundry (cross-scope)
// Extended as per accelerator need
module workloadOpenAIContributorExisting './cross-scope-role-assignment.bicep' = [for (principalId, i) in workloadPrincipals: if (useExistingAIProject && !empty(principalId)) {
  name: 'assignOpenAIContributorRoleToWorkloadExisting-${i}'
  scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
  params: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIContributor)
    roleAssignmentName: guid(solutionName, existingAIFoundryName, principalId, roleDefinitions.cognitiveServicesOpenAIContributor)
    aiFoundryName: existingAIFoundryName
  }
}]

// ============================================================================
// 2. SEARCH SERVICE ROLE ASSIGNMENTS
//    AI Project and Backend identities → AI Search
// ============================================================================

// AI Project (New OR Existing) → Search Index Data Reader on AI Search
resource projectSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(aiProjectPrincipalId)) {
  name: guid(solutionName, aiSearchResourceId, aiProjectPrincipalId, roleDefinitions.searchIndexDataReader)
  scope: aiSearchService
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataReader)
    principalType: 'ServicePrincipal'
  }
}

// AI Project (New OR Existing) → Search Service Contributor on AI Search
resource projectSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchResourceId) && !empty(aiProjectPrincipalId)) {
  name: guid(solutionName, aiSearchResourceId, aiProjectPrincipalId, roleDefinitions.searchServiceContributor)
  scope: aiSearchService
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: 'ServicePrincipal'
  }
}

// Workload identities (UAMI or SAMI) → Search Index Data Contributor on AI Search
// Extended as per accelerator need
resource workloadSearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in workloadPrincipals: if (!empty(aiSearchResourceId) && !empty(principalId)) {
  name: guid(solutionName, aiSearchResourceId, principalId, roleDefinitions.searchIndexDataContributor)
  scope: aiSearchService
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataContributor)
    principalType: 'ServicePrincipal'
  }
}]

// Workload identities (UAMI or SAMI) → Search Service Contributor on AI Search
// Extended as per accelerator need
resource workloadSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in workloadPrincipals: if (!empty(aiSearchResourceId) && !empty(principalId)) {
  name: guid(solutionName, aiSearchResourceId, principalId, roleDefinitions.searchServiceContributor)
  scope: aiSearchService
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: 'ServicePrincipal'
  }
}]

// ============================================================================
// 3. STORAGE ROLE ASSIGNMENTS
//    AI Project, AI Search, and Existing Project identities → Storage
// ============================================================================

// Workload identities (UAMI or SAMI) → Storage Blob Data Contributor on Storage Account
// Extended as per accelerator need
resource workloadStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in workloadPrincipals: if (!empty(storageAccountResourceId) && !empty(principalId)) {
  name: guid(solutionName, storageAccountResourceId, principalId, roleDefinitions.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: 'ServicePrincipal'
  }
}]

// ============================================================================
// 4. COSMOS DB ROLE ASSIGNMENTS
//    User-Assigned Managed Identity → Cosmos DB (data-plane, uses sqlRoleAssignments)
// ============================================================================

resource workloadCosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-10-15' = [for principalId in workloadPrincipals: if (!empty(cosmosDbAccountName) && !empty(principalId)) {
  parent: cosmosAccount
  name: guid(solutionName, cosmosContributorRoleDefinition.id, cosmosAccount.id, principalId)
  properties: {
    principalId: principalId
    roleDefinitionId: cosmosContributorRoleDefinition.id
    scope: cosmosAccount.id
  }
}]

// ============================================================================
// 5. DEPLOYER (USER) ROLE ASSIGNMENTS
//    Deploying user → AI Services, Search, Storage (Bicep-only)
// ============================================================================

// Deploying User → Cognitive Services User on AI Services
resource deployerAiServicesAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(deployerPrincipalId) && !empty(aiFoundryResourceId)) {
  scope: aiFoundryAccount
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.cognitiveServicesUser)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Foundry User on AI Services
resource deployerAzureAIAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(deployerPrincipalId) && !empty(aiFoundryResourceId)) {
  scope: aiFoundryAccount
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.azureAiUser)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: deployerPrincipalType
  }
}

// // Deploying User → Cognitive Services User on existing AI Foundry (cross-scope)
// // Extended as per accelerator need
// module deployerAiServicesAccessExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(deployerPrincipalId)) {
//   name: 'deployerCognitiveServicesUserExisting'
//   scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
//   params: {
//     principalId: deployerPrincipalId
//     roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
//     roleAssignmentName: guid(solutionName, 'deployer-cognitive-services-user', existingAIFoundryName, roleDefinitions.cognitiveServicesUser)
//     aiFoundryName: existingAIFoundryName
//     principalType: deployerPrincipalType
//   }
// }

// // Deploying User → Foundry User on existing AI Foundry (cross-scope)
// // Extended as per accelerator need
// module deployerAzureAIAccessExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(deployerPrincipalId)) {
//   name: 'deployerAzureAIUserExisting'
//   scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
//   params: {
//     principalId: deployerPrincipalId
//     roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
//     roleAssignmentName: guid(solutionName, 'deployer-azure-ai-user', existingAIFoundryName, roleDefinitions.azureAiUser)
//     aiFoundryName: existingAIFoundryName
//     principalType: deployerPrincipalType
//   }
// }

// Deploying User → Search Index Data Contributor on AI Search
resource deployerSearchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(aiSearchResourceId)) {
  scope: aiSearchService
  name: guid(solutionName, aiSearchService.id, deployerPrincipalId, roleDefinitions.searchIndexDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Search Service Contributor on AI Search
resource deployerSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(aiSearchResourceId)) {
  scope: aiSearchService
  name: guid(solutionName, aiSearchService.id, deployerPrincipalId, roleDefinitions.searchServiceContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Storage Blob Data Contributor
resource deployerStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId) && !empty(storageAccountResourceId)) {
  scope: storageAccount
  name: guid(solutionName, storageAccount.id, deployerPrincipalId, roleDefinitions.storageBlobDataContributor)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
    principalType: deployerPrincipalType
  }
}

// Deploying User → Cosmos DB Contributor (data-plane, uses sqlRoleAssignments)
resource deployerCosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-10-15' = if (!empty(cosmosDbAccountName) && !empty(deployerPrincipalId)) {
  parent: cosmosAccount
  name: guid(solutionName, cosmosContributorRoleDefinition.id, cosmosAccount.id, deployerPrincipalId)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: cosmosContributorRoleDefinition.id
    scope: cosmosAccount.id
  }
}


// ============================================================================
// 6. ACR ROLE ASSIGNMENTS
// ============================================================================

// Workload identities (UAMI or SAMI) → AcrPull on Container Registry
// NOTE: With system-assigned identities there is a chicken-and-egg with image pull:
// the workload must exist before its SAMI principalId is known, but ACR Pull RBAC
// must propagate before the first successful pull. Plan for a two-pass deploy or a
// post-create restart of the workload when switching to SAMI.
resource workloadAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in workloadPrincipals: if (!empty(containerRegistryResourceId) && !empty(principalId)) {
  name: guid(solutionName, containerRegistry.id, principalId, roleDefinitions.acrPull)
  scope: containerRegistry
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.acrPull)
    principalType: 'ServicePrincipal'
  }
}]


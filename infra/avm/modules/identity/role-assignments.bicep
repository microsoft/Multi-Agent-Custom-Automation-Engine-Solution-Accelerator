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
// 2. COSMOS DB ROLE ASSIGNMENTS
//    User-Assigned Managed Identity → Cosmos DB (data-plane, uses sqlRoleAssignments)
// ============================================================================

resource workloadCosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-10-15' = [for principalId in workloadPrincipals: if (!empty(cosmosDbAccountName) && !empty(principalId)) {
  parent: cosmosAccount
  name: guid(solutionName, cosmosAccount.id, principalId, cosmosContributorRoleDefinition.id)
  properties: {
    principalId: principalId
    roleDefinitionId: cosmosContributorRoleDefinition.id
    scope: cosmosAccount.id
  }
}]

// ============================================================================
// 5. DEPLOYER (USER) ROLE ASSIGNMENTS
// ============================================================================

//Deployer → Cosmos DB Contributor (data-plane, uses sqlRoleAssignments)
resource deployerCosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = if (!empty(cosmosDbAccountName) && !empty(deployerPrincipalId)) {
  parent: cosmosAccount
  name: guid(solutionName, cosmosAccount.id, deployerPrincipalId, cosmosContributorRoleDefinition.id)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: cosmosContributorRoleDefinition.id
    scope: cosmosAccount.id
  }
}

// Deployer → Foundry User on AI Foundry (new project, same RG)
// Extended as per accelerator need
resource deployerAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(aiFoundryResourceId) && !empty(deployerPrincipalId)) {
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.azureAiUser)
  scope: aiFoundryAccount
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
    principalType: 'User'
  }
}

// Deploying User → Cognitive Services User on AI Services
resource deployerAiServicesAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingAIProject && !empty(deployerPrincipalId) && !empty(aiFoundryResourceId)) {
  scope: aiFoundryAccount
  name: guid(solutionName, aiFoundryAccount.id, deployerPrincipalId, roleDefinitions.cognitiveServicesUser)
  properties: {
    principalId: deployerPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalType: 'User'
  }
}

// // Deployer → Foundry User on existing AI Foundry (cross-scope)
// // Extended as per accelerator need
// module deployerAiUserExisting './cross-scope-role-assignment.bicep' = if (useExistingAIProject && !empty(deployerPrincipalId)) {
//   name: 'assignAiUserRoleToDeployerExisting'
//   scope: resourceGroup(existingAIFoundrySubscription, existingAIFoundryResourceGroup)
//   params: {
//     principalId: deployerPrincipalId
//     roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAiUser)
//     roleAssignmentName: guid(solutionName, 'deployer-ai-user', existingAIFoundryName, roleDefinitions.azureAiUser)
//     aiFoundryName: existingAIFoundryName
//     principalType: 'User'
//   }
// }

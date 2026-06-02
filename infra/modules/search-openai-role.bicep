// ========================================================================
// Assigns "Cognitive Services OpenAI User" on an AI Services (Cognitive
// Services) account to the Search service's system-assigned managed identity.
// Deployed at the scope of the AI Services account's resource group so it
// works for both new and existing (cross-RG / cross-subscription) Foundry.
// ========================================================================

param aiFoundryAccountName string
param searchServicePrincipalId string
param roleNameGuidSeed string

resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: aiFoundryAccountName
}

resource searchServiceOpenAIRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServicesAccount.id, roleNameGuidSeed, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  scope: aiServicesAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
    principalId: searchServicePrincipalId
    principalType: 'ServicePrincipal'
  }
}

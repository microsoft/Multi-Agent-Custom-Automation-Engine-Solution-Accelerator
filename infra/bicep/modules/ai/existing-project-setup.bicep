// ============================================================================
// Module: Existing AI Foundry Project Reference — Vanilla Bicep
// Description: References an existing AI Services account and project to
//              retrieve their identities. No deployments, no connections.
//              Use generic ai-foundry-connection and ai-foundry-model-deployment
//              modules for those concerns.
// ============================================================================

@description('The name of the existing AI Services account.')
param aiFoundryName string

@description('The name of the existing AI project.')
param aiProjectName string

// ============================================================================
// Existing Resource References
// ============================================================================

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = {
  name: aiFoundryName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-12-01' existing = {
  parent: aiServices
  name: aiProjectName
}

// ============================================================================
// Outputs
// ============================================================================

@description('The principal ID of the AI Foundry system-assigned managed identity.')
output aiFoundryPrincipalId string = contains(aiServices, 'identity') && contains(aiServices.identity, 'principalId') ? aiServices.identity.principalId : ''

@description('The principal ID of the AI Project system-assigned managed identity.')
output aiProjectPrincipalId string = contains(aiProject, 'identity') && contains(aiProject.identity, 'principalId') ? aiProject.identity.principalId : ''

@description('The name of the AI Services account.')
output aiServicesAccountName string = aiServices.name

@description('The name of the AI project.')
output aiProjectNameOutput string = aiProject.name

@description('The endpoint URL for the Azure OpenAI service.')
output aiFoundryEndpoint string = 'https://${aiFoundryName}.openai.azure.com/'

@description('The endpoint URL for the AI Foundry project.')
output projectEndpoint string = 'https://${aiFoundryName}.services.ai.azure.com/api/projects/${aiProjectName}'

@description('The resource ID of the AI Services account.')
output aiFoundryResourceId string = aiServices.id

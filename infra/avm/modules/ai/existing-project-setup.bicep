// ============================================================================
// Module: Existing AI Foundry Project Reference
// Description: References an existing AI Services account and project to
//              retrieve their identities. No deployments, no connections.
//              Use generic ai-foundry-connection and ai-foundry-model-deployment
//              modules for those concerns.
// ============================================================================

@description('Required. The name of the existing Cognitive Services account.')
param name string

@description('Required. The name of the existing AI project.')
param projectName string

// ============================================================================
// Existing Resource References
// ============================================================================
resource cognitiveService 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = {
  name: name
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-12-01' existing = {
  parent: cognitiveService
  name: projectName
}

// ============================================================================
// Outputs
// ============================================================================
@description('The principal ID of the AI Foundry system-assigned managed identity (empty if none).')
output aiFoundryPrincipalId string = cognitiveService.identity.?principalId ?? ''

@description('The principal ID of the AI Project system-assigned managed identity (empty if none).')
output aiProjectPrincipalId string = aiProject.identity.?principalId ?? ''

@description('The name of the AI Services account.')
output aiServicesAccountName string = cognitiveService.name

@description('The name of the AI project.')
output aiProjectName string = aiProject.name

@description('The endpoint URL for the Azure OpenAI service.')
output aiFoundryEndpoint string = 'https://${name}.openai.azure.com/'

@description('The endpoint URL for the AI Foundry project.')
output projectEndpoint string = 'https://${name}.services.ai.azure.com/api/projects/${projectName}'

@description('The resource ID of the AI Services account.')
output aiFoundryResourceId string = cognitiveService.id


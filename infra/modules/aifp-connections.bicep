// ========================================================================
// Base AI Search connection (CognitiveSearch / AAD).
// Per-KB RemoteTool connections (ProjectManagedIdentity) are created by
// infra/scripts/seed_kb_connections.py at post-deploy time because the KB
// names are dynamic and depend on selected content packs.
// ========================================================================

@description('Name of the AI Foundry search connection')
param aifSearchConnectionName string

@description('Name of the Azure AI Search service')
param searchServiceName string

@description('Resource ID of the Azure AI Search service')
param searchServiceResourceId string

@description('Location/region of the Azure AI Search service')
param searchServiceLocation string

@description('Name of the AI Foundry account')
param aiFoundryName string

@description('Name of the AI Foundry project')
param aiFoundryProjectName string

resource aiSearchFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-12-01' = {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${aifSearchConnectionName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net'
    authType: 'AAD'
    useWorkspaceManagedIdentity: true
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceResourceId
      location: searchServiceLocation
    }
  }
}

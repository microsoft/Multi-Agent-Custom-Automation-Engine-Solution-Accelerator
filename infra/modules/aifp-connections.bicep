// ========================================================================
// Base AI Search connection (CognitiveSearch / AAD).
// Per-KB RemoteTool connections (ProjectManagedIdentity) are created by
// infra/scripts/seed_kb_connections.py at post-deploy time because the KB
// names are dynamic and depend on selected content packs.
// ========================================================================

param aifSearchConnectionName string
param searchServiceName string
param searchServiceResourceId string
param searchServiceLocation string
param aiFoundryName string
param aiFoundryProjectName string

resource aiSearchFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
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

param aifSearchConnectionName string
param searchServiceName string
param searchServiceResourceId string
param searchServiceLocation string
param aiFoundryName string
param aiFoundryProjectName string
@secure()
param searchApiKey string

resource aiSearchFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${aifSearchConnectionName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net'
    authType: 'ApiKey'
    credentials: {
      key: searchApiKey
    }
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceResourceId
      location: searchServiceLocation
    }
  }
}

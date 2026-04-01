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

resource aiSearchFoundryConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${aifSearchConnectionName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net'
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceResourceId
      location: searchServiceLocation
    }
  }
}

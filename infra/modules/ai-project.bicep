@description('Required. Name of the AI Services project.')
param name string

@description('Required. The location of the Project resource.')
param location string = resourceGroup().location

@description('Optional. The description of the AI Foundry project to create. Defaults to the project name.')
param desc string = name

@description('Required. Name of the existing Cognitive Services resource to create the AI Foundry project in.')
param aiServicesName string

@description('Optional. Tags to be applied to the resources.')
param tags object = {}

// Reference to cognitive service in current resource group for new projects
resource cogServiceReference 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: aiServicesName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: cogServiceReference
  name: name
  tags: tags
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: desc
    displayName: name
  }
}

@description('Required. Name of the AI project.')
output name string = aiProject.name

@description('Required. Resource ID of the AI project.')
output resourceId string = aiProject.id

@description('Required. Principal ID of the AI project managed identity.')
output principalId string = aiProject.identity.principalId

@description('Required. API endpoint for the AI project.')
output apiEndpoint string = aiProject!.properties.endpoints['AI Foundry API']

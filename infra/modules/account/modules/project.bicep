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

@description('Optional. Use this parameter to use an existing AI project resource ID from different resource group')
param azureExistingAIProjectResourceId string = ''

// // Extract components from existing AI Project Resource ID if provided
var useExistingProject = !empty(azureExistingAIProjectResourceId)
var existingProjName = useExistingProject ? last(split(azureExistingAIProjectResourceId, '/')) : ''
var existingProjEndpoint = useExistingProject ? format('https://{0}.services.ai.azure.com/api/projects/{1}', aiServicesName, existingProjName) : ''
// Reference to cognitive service in current resource group for new projects
resource cogServiceReference 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiServicesName
}

// Create new AI project only if not reusing existing one
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = if(!useExistingProject) {
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

@description('AI Project metadata including name, resource ID, and API endpoint.')
output aiProjectInfo aiProjectOutputType = {
  name: useExistingProject ? existingProjName : aiProject.name
  resourceId: useExistingProject ? azureExistingAIProjectResourceId : aiProject.id
  apiEndpoint: useExistingProject ? existingProjEndpoint : aiProject.properties.endpoints['AI Foundry API']
}

@export()
@description('Output type representing AI project information.')
type aiProjectOutputType = {
  @description('Required. Name of the AI project.')
  name: string

  @description('Required. Resource ID of the AI project.')
  resourceId: string

  @description('Required. API endpoint for the AI project.')
  apiEndpoint: string
}

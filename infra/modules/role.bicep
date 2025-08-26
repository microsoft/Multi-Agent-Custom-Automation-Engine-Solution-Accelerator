@description('The name of the role assignment resource. Typically generated using `guid()` for uniqueness.')
param name string

@description('The object ID of the principal (user, group, or service principal) to whom the role will be assigned.')
param principalId string

@description('The name of the existing Azure Cognitive Services account.')
param aiServiceName string


@allowed(['Device', 'ForeignGroup', 'Group', 'ServicePrincipal', 'User'])
param principalType string = 'ServicePrincipal'

resource cognitiveServiceExisting 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing =  {
  name: aiServiceName
}

resource aiUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
}

resource aiDeveloper 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '64702f94-c441-49e6-a78b-ef80e0188fee'
}

resource cognitiveServiceOpenAIUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
}

resource aiUserAccessFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(name, 'aiUserAccessFoundry')
  scope: cognitiveServiceExisting
  properties: {
    roleDefinitionId: aiUser.id
    principalId: principalId
    principalType: principalType
  }
}

resource aiDeveloperAccessFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(name, 'aiDeveloperAccessFoundry')
  scope: cognitiveServiceExisting
  properties: {
    roleDefinitionId: aiDeveloper.id
    principalId: principalId
    principalType: principalType
  }
}

resource cognitiveServiceOpenAIUserAccessFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(name, 'cognitiveServiceOpenAIUserAccessFoundry')
  scope: cognitiveServiceExisting
  properties: {
    roleDefinitionId: cognitiveServiceOpenAIUser.id
    principalId: principalId
    principalType: principalType
  }
}

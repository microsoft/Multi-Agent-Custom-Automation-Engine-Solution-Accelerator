@description('Required. Flag to check if the container app exists')
param exists bool

@description('Required. Name of the container app')
param name string

resource existingApp 'Microsoft.App/containerApps@2023-05-02-preview' existing = if (exists) {
  name: name
}

@description('List of container definitions for the container app')
output containers array = exists ? existingApp.properties.template.containers : []

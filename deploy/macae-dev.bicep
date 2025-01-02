@description('Location for all resources.')
param location string = resourceGroup().location

@description('location for Cosmos DB resources.')
// prompt for this as there is often quota restrictions
param cosmosLocation string

@description('Location for OpenAI resources.')
// prompt for this as there is often quota restrictions
param azureOpenAILocation string

@description('A prefix to add to the start of all resource names. Note: A "unique" suffix will also be added')
param prefix string = 'macae'

@description('Tags to apply to all deployed resources')
param tags object = {}

@description('Principal ID to assign to the Cosmos DB contributor & Azure OpenAI user role, leave empty to skip role assignment. This is your ObjectID wihtin Entra ID.')
param developerPrincipalId string

var uniqueNameFormat = '${prefix}-{0}-${uniqueString(resourceGroup().id, prefix)}'
var aoaiApiVersion = '2024-08-01-preview'

resource openai 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: format(uniqueNameFormat, 'openai')
  location: azureOpenAILocation
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: format(uniqueNameFormat, 'openai')
  }
  resource gpt4o 'deployments' = {
    name: 'gpt-4o'
    sku: {
      name: 'GlobalStandard'
      capacity: 15
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: 'gpt-4o'
        version: '2024-08-06'
      }
      versionUpgradeOption: 'NoAutoUpgrade'
    }
  }
}

resource aoaiUserRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-05-01-preview' existing = {
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' //'Cognitive Services OpenAI User'
}

resource devAoaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if(!empty(trim(developerPrincipalId))) {
  name: guid(developerPrincipalId, openai.id, aoaiUserRoleDefinition.id)
  scope: openai
  properties: {
    principalId: developerPrincipalId
    roleDefinitionId: aoaiUserRoleDefinition.id
    principalType: 'User'
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: format(uniqueNameFormat, 'cosmos')
  location: cosmosLocation
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: false
    locations: [
      {
        failoverPriority: 0
        locationName: cosmosLocation
      }
    ]
  }

  resource contributorRoleDefinition 'sqlRoleDefinitions' existing = {
    name: '00000000-0000-0000-0000-000000000002'
  }

  resource devRoleAssignment 'sqlRoleAssignments' = if(!empty(trim(developerPrincipalId))) {
    name: guid(developerPrincipalId, contributorRoleDefinition.id)
    properties: {
      principalId: developerPrincipalId
      roleDefinitionId: contributorRoleDefinition.id
      scope: cosmos.id
    }
  }

  resource autogenDb 'sqlDatabases' = {
    name: 'autogen'
    properties: {
      resource: {
        id: 'autogen'
        createMode: 'Default'
      }
      options: {
        throughput: 400
      }
    }

    resource memoryContainer 'containers' = {
      name: 'memory'
      properties: {
        resource: {
          id: 'memory'
          partitionKey: {
            kind: 'Hash'
            version: 2
            paths: [
              '/session_id'
            ]
          }
        }
      }
    }
  }
}



output COSMOSDB_ENDPOINT string = cosmos.properties.documentEndpoint
output COSMOSDB_DATABASE string = cosmos::autogenDb.name
output COSMOSDB_CONTAINER string = cosmos::autogenDb::memoryContainer.name
output AZURE_OPENAI_ENDPOINT string = openai.properties.endpoint
output AZURE_OPENAI_DEPLOYMENT_NAME string = openai::gpt4o.name
output AZURE_OPENAI_API_VERSION string = aoaiApiVersion


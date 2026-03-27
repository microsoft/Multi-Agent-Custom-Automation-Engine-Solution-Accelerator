param cosmosDBConnection string
param azureStorageConnection string
param aiSearchConnection string
param projectName string
param accountName string
param projectCapHost string
param accountCapHost string
param createAccountCapabilityHost bool = false

@description('Optional. The agent subnet resource ID for VNet injection. When set, capability hosts use this subnet instead of Microsoft-managed networking.')
param customerSubnetResourceId string = ''

var threadConnections = ['${cosmosDBConnection}']
var storageConnections = ['${azureStorageConnection}']
var vectorStoreConnections = ['${aiSearchConnection}']


resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
   name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  name: projectName
  parent: account
}

// Account-level capability host is required before project-level capability host can be created.
// When creating a new AI Services account, the AVM module with networkInjections handles this automatically.
// When using an existing AI Foundry account (e.g. cross-subscription), we must create it explicitly.
resource accountCapabilityHost 'Microsoft.CognitiveServices/accounts/capabilityHosts@2025-04-01-preview' = if (createAccountCapabilityHost) {
  name: accountCapHost
  parent: account
  properties: {
    capabilityHostKind: 'Agents'
    customerSubnet: !empty(customerSubnetResourceId) ? customerSubnetResourceId : null
  }
}

resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  name: projectCapHost
  parent: project
  properties: {
    capabilityHostKind: 'Agents'
    vectorStoreConnections: vectorStoreConnections
    storageConnections: storageConnections
    threadStorageConnections: threadConnections
  }
  dependsOn: [
    accountCapabilityHost
  ]
}

output projectCapHost string = projectCapabilityHost.name

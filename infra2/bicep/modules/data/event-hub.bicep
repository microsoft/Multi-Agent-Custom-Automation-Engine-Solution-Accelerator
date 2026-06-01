targetScope = 'resourceGroup'

@description('The name of the solution, used as the base for resource naming.')
param solutionName string

@description('The Azure region where Event Hub resources will be deployed.')
param solutionLocation string

@description('Tags to apply to the resources.')
param tags object = {}

@description('The SKU tier for the Event Hub namespace.')
param sku string = 'Standard'

@description('The throughput unit or processing unit capacity for the Event Hub namespace.')
param capacity int = 1

@description('The Event Hubs to create in the namespace.')
param eventhubs array = []

var name = 'evhns-${solutionName}'

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: name
  location: solutionLocation
  tags: tags
  sku: {
    name: sku
    tier: sku
    capacity: capacity
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource eventHubResources 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = [for eventhub in eventhubs: {
  name: eventhub.name
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: eventhub.?messageRetentionInDays ?? 1
    partitionCount: eventhub.?partitionCount ?? 2
  }
}]

@description('The name of the Event Hub namespace.')
output name string = eventHubNamespace.name

@description('The resource ID of the Event Hub namespace.')
output id string = eventHubNamespace.id

@description('The service bus endpoint of the Event Hub namespace.')
output serviceBusEndpoint string = eventHubNamespace.properties.serviceBusEndpoint

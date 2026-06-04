// ============================================================================
// Module: Azure Event Grid
// Description: Deploys Azure Event Grid Topic
// API: Microsoft.EventGrid/topics@2024-06-01-preview
// ============================================================================

@description('Solution name suffix used to derive the resource name.')
param solutionName string

@description('Name of the Event Grid topic.')
param name string = 'egt-${solutionName}'

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Public network access setting.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Disable local (key-based) authentication.')
param disableLocalAuth bool = false

@description('Event subscriptions to create on the topic.')
param eventSubscriptions array = []

// ============================================================================
// Resource
// ============================================================================
resource eventGridTopic 'Microsoft.EventGrid/topics@2024-06-01-preview' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
  }
}

// ============================================================================
// Event Subscriptions
// ============================================================================
resource eventGridSubscriptions 'Microsoft.EventGrid/topics/eventSubscriptions@2024-06-01-preview' = [
  for sub in eventSubscriptions: {
    name: sub.name
    parent: eventGridTopic
    properties: {
      destination: sub.destination
      filter: sub.?filter ?? {}
      eventDeliverySchema: sub.?eventDeliverySchema ?? 'EventGridSchema'
    }
  }
]

// ============================================================================
// Outputs
// ============================================================================
@description('Name of the Event Grid topic.')
output name string = eventGridTopic.name

@description('Resource ID of the Event Grid topic.')
output resourceId string = eventGridTopic.id

@description('Endpoint of the Event Grid topic.')
output endpoint string = eventGridTopic.properties.endpoint

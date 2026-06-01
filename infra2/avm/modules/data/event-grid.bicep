// ============================================================================
// Module: Azure Event Grid
// Description: AVM wrapper for Azure Event Grid Topic
// AVM Module: avm/res/event-grid/topic:0.6.1
// ============================================================================

@description('Solution name suffix used to derive the resource name.')
param solutionName string

var topicName = 'egt-${solutionName}'

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Input schema for the Event Grid topic.')
@allowed(['EventGridSchema', 'CustomEventSchema', 'CloudEventSchemaV1_0'])
param inputSchema string = 'EventGridSchema'

@description('Public network access setting.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Disable local (key-based) authentication.')
param disableLocalAuth bool = false

@description('Whether to enable private networking.')
param enablePrivateNetworking bool = false

@description('Subnet resource ID for the private endpoint.')
param privateEndpointSubnetId string = ''

@description('Private DNS zone resource IDs.')
param privateDnsZoneResourceIds array = []

@description('Event subscriptions to create on the topic.')
param eventSubscriptions array = []

@description('Diagnostic settings for monitoring.')
param diagnosticSettings array = []

var privateDnsZoneConfigs = [for (zoneId, i) in privateDnsZoneResourceIds: {
  name: 'dns-zone-${i}'
  privateDnsZoneResourceId: zoneId
}]

// ============================================================================
// AVM Module Deployment
// ============================================================================
module eventGridTopic 'br/public:avm/res/event-grid/topic:0.6.1' = {
  name: take('avm.res.event-grid.topic.${topicName}', 64)
  params: {
    name: topicName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
    diagnosticSettings: !empty(diagnosticSettings) ? diagnosticSettings : []
    eventSubscriptions: eventSubscriptions
    privateEndpoints: enablePrivateNetworking ? [
      {
        name: 'pep-${topicName}'
        customNetworkInterfaceName: 'nic-${topicName}'
        subnetResourceId: privateEndpointSubnetId
        service: 'topic'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: privateDnsZoneConfigs
        }
      }
    ] : []
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('Name of the Event Grid topic.')
output name string = eventGridTopic.outputs.name

@description('Resource ID of the Event Grid topic.')
output resourceId string = eventGridTopic.outputs.resourceId

// ============================================================================
// Module: Azure Container Instance (AVM)
// ============================================================================

@description('Name of the container group.')
param name string

@description('Azure region for deployment.')
param location string

@description('Resource tags.')
param tags object = {}

@description('Enable Azure telemetry collection.')
param enableTelemetry bool = true

@description('Container definitions.')
param containers array

@description('Operating system type.')
@allowed(['Linux', 'Windows'])
param osType string = 'Linux'

@description('Restart policy.')
@allowed(['Always', 'OnFailure', 'Never'])
param restartPolicy string = 'OnFailure'

@description('Managed identity configuration.')
param managedIdentities object = {}

@description('IP address type.')
@allowed(['Public', 'Private'])
param ipAddressType string = 'Public'

@description('Image registry credentials.')
param imageRegistryCredentials array = []

@description('Ports to expose on the IP address.')
param ipAddressPorts array = []

// ============================================================================
// Container Instance (AVM)
// ============================================================================

module containerGroup 'br/public:avm/res/container-instance/container-group:0.4.2' = {
  name: take('avm.res.containerinstance.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    containers: containers
    osType: osType
    restartPolicy: restartPolicy
    managedIdentities: !empty(managedIdentities) ? managedIdentities : {}
    ipAddressType: ipAddressType
    ipAddressPorts: !empty(ipAddressPorts) ? ipAddressPorts : [
      { port: 80, protocol: 'TCP' }
    ]
    imageRegistryCredentials: !empty(imageRegistryCredentials) ? imageRegistryCredentials : []
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the container group.')
output name string = containerGroup.outputs.name

@description('The resource ID of the container group.')
output resourceId string = containerGroup.outputs.resourceId

@description('The IP address of the container group.')
output ipAddress string = containerGroup.outputs.iPv4Address

// ============================================================================
// Module: Azure Container Registry (Bicep)
// ============================================================================

@description('Solution name used for naming convention.')
param solutionName string

@description('Azure region for deployment.')
param solutionLocation string

@description('Resource tags.')
param tags object = {}

@description('SKU for the container registry.')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Premium'

@description('Enable admin user.')
param adminUserEnabled bool = false

@description('Public network access setting.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

// ============================================================================
// Naming
// ============================================================================

var registryName = replace('cr${solutionName}', '-', '')

// ============================================================================
// Container Registry
// ============================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: solutionLocation
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: adminUserEnabled
    publicNetworkAccess: publicNetworkAccess
    dataEndpointEnabled: false
    networkRuleBypassOptions: 'AzureServices'
    policies: {
      retentionPolicy: {
        status: 'enabled'
        days: 7
      }
      trustPolicy: {
        status: 'disabled'
        type: 'Notary'
      }
    }
    zoneRedundancy: 'Disabled'
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the container registry.')
output name string = containerRegistry.name

@description('The login server URL.')
output loginServer string = containerRegistry.properties.loginServer

@description('The resource ID of the container registry.')
output id string = containerRegistry.id
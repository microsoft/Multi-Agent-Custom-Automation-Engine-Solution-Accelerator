// ============================================================================
// Module: Azure Container Registry (AVM public wrapper)
// Description: AVM wrapper for Azure Container Registry with WAF alignment.
//              Deploys the registry unconditionally and, when private
//              networking is enabled, attaches a private endpoint into the
//              backend subnet and wires the privatelink.azurecr.io DNS zone.
// AVM Module: avm/res/container-registry/registry:0.12.0
// Mirrors github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator (infra/main.bicep).
// ============================================================================

@description('Solution name suffix used to derive the resource name.')
param solutionName string

@description('Name of the container registry.')
param name string = take('cr${toLower(replace(solutionName, '-', ''))}', 50)

@description('Azure region for deployment.')
param location string

@description('Resource tags.')
param tags object = {}

@description('SKU for the container registry.')
@allowed(['Basic', 'Standard', 'Premium'])
param acrSku string = 'Basic'

@description('Enable admin user.')
param acrAdminUserEnabled bool = false

@description('Public network access setting.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Default action for the network rule set. Set to Deny for WAF/private networking.')
@allowed(['Allow', 'Deny'])
param networkRuleSetDefaultAction string = 'Allow'

@description('Export policy status.')
param exportPolicyStatus string = 'enabled'

@description('Soft-delete policy status.')
param softDeletePolicyStatus string = 'disabled'

@description('Soft-delete retention in days.')
param softDeletePolicyDays int = 7

@description('Enable Azure AD authentication as ARM policy.')
param azureADAuthenticationAsArmPolicyStatus string = 'enabled'

@description('Network rule bypass options.')
param networkRuleBypassOptions string = 'AzureServices'

@description('Optional. Enable usage telemetry for module.')
param enableTelemetry bool = true

// --- WAF: Private Networking ---
@description('Whether to enable private networking (WAF). Drives Premium SKU, disabled public access, and a private endpoint.')
param enablePrivateNetworking bool = false

@description('Subnet resource ID for the private endpoint. Required when enablePrivateNetworking is true.')
param privateEndpointSubnetId string = ''

@description('Private DNS zone resource IDs for the container registry (privatelink.azurecr.io). Required when enablePrivateNetworking is true.')
param privateDnsZoneResourceIds array = []

var privateDnsZoneConfigs = [for (zoneId, i) in privateDnsZoneResourceIds: {
  name: 'dns-zone-${i}'
  privateDnsZoneResourceId: zoneId
}]

// ============================================================================
// AVM Module Deployment
// ============================================================================
module containerRegistry 'br/public:avm/res/container-registry/registry:0.12.0' = {
  name: take('avm.res.container-registry.registry.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    acrSku: enablePrivateNetworking ? 'Premium' : acrSku
    acrAdminUserEnabled: acrAdminUserEnabled
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : publicNetworkAccess
    networkRuleSetDefaultAction: enablePrivateNetworking ? 'Deny' : networkRuleSetDefaultAction
    exportPolicyStatus: exportPolicyStatus
    softDeletePolicyStatus: softDeletePolicyStatus
    softDeletePolicyDays: softDeletePolicyDays
    azureADAuthenticationAsArmPolicyStatus: azureADAuthenticationAsArmPolicyStatus
    networkRuleBypassOptions: networkRuleBypassOptions
    privateEndpoints: enablePrivateNetworking
      ? [
          {
            name: 'pep-${name}'
            customNetworkInterfaceName: 'nic-${name}'
            subnetResourceId: privateEndpointSubnetId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: privateDnsZoneConfigs
            }
          }
        ]
      : []
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('The name of the container registry.')
output name string = containerRegistry.outputs.name

@description('The login server URL of the container registry.')
output loginServer string = containerRegistry.outputs.loginServer

@description('The resource ID of the container registry.')
output resourceId string = containerRegistry.outputs.resourceId
 
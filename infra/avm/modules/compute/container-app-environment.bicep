// ============================================================================
// Module: Azure Container Apps Environment (AVM)
// ============================================================================

@description('Solution name used for naming convention.')
param solutionName string

@description('Azure region for deployment.')
param location string

@description('Resource tags.')
param tags object = {}

@description('Enable Azure telemetry collection.')
param enableTelemetry bool = true

@description('Resource ID of the Log Analytics workspace.')
param logAnalyticsWorkspaceResourceId string

@description('Subnet resource ID for VNet integration (optional).')
param infrastructureSubnetId string = ''

@description('Enable zone redundancy.')
param zoneRedundant bool = false

// ============================================================================
// Naming
// ============================================================================

var environmentName = 'cae-${solutionName}'

// ============================================================================
// Container Apps Environment (AVM)
// ============================================================================

module managedEnvironment 'br/public:avm/res/app/managed-environment:0.8.1' = {
  name: take('avm.res.app.managedenvironment.${environmentName}', 64)
  params: {
    name: environmentName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
    infrastructureSubnetId: !empty(infrastructureSubnetId) ? infrastructureSubnetId : null
    zoneRedundant: zoneRedundant
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the Container Apps Environment.')
output name string = managedEnvironment.outputs.name

@description('The resource ID of the Container Apps Environment.')
output resourceId string = managedEnvironment.outputs.resourceId

@description('The default domain of the Container Apps Environment.')
output defaultDomain string = managedEnvironment.outputs.defaultDomain

@description('The static IP of the Container Apps Environment.')
output staticIp string = managedEnvironment.outputs.staticIp

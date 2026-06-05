// ============================================================================
// Module: Azure Container Apps Environment (AVM)
// AVM Module: avm/res/app/managed-environment:0.13.3
// ============================================================================

@description('Solution name used for naming convention.')
param solutionName string

@description('Name of the Container Apps Environment.')
param name string = 'cae-${solutionName}'

@description('Azure region for deployment.')
param location string

@description('Resource tags.')
param tags object = {}

@description('Resource ID of the Log Analytics workspace.')
param logAnalyticsWorkspaceResourceId string

@description('Subnet resource ID for VNet integration (optional).')
param infrastructureSubnetId string = ''

@description('Enable zone redundancy.')
param zoneRedundant bool = false

@description('Enable Azure telemetry collection.')
param enableTelemetry bool = true

// ============================================================================
// Container Apps Environment (AVM)
// ============================================================================
module managedEnvironment 'br/public:avm/res/app/managed-environment:0.13.3' = {
  name: take('avm.res.app.managedenvironment.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
    }
    infrastructureSubnetResourceId: !empty(infrastructureSubnetId) ? infrastructureSubnetId : null
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

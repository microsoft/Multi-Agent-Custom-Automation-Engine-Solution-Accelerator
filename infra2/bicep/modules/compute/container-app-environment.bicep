targetScope = 'resourceGroup'

@description('The name of the solution, used as the base for resource naming.')
param solutionName string

@description('The Azure region where the Container Apps environment will be deployed.')
param solutionLocation string

@description('Tags to apply to the resource.')
param tags object = {}

@description('The resource ID of the Log Analytics workspace used for environment logging.')
param logAnalyticsWorkspaceId string

@description('Optional. The subnet resource ID used for Container Apps infrastructure.')
param infrastructureSubnetId string = ''

@description('Indicates whether the Container Apps environment is zone redundant.')
param zoneRedundant bool = false

var name = 'cae-${solutionName}'

resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: solutionLocation
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2023-09-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2023-09-01').primarySharedKey
      }
    }
    vnetConfiguration: empty(infrastructureSubnetId) ? null : {
      infrastructureSubnetId: infrastructureSubnetId
    }
    zoneRedundant: zoneRedundant
  }
}

@description('The name of the Container Apps environment.')
output name string = containerAppEnvironment.name

@description('The resource ID of the Container Apps environment.')
output id string = containerAppEnvironment.id

@description('The default domain of the Container Apps environment.')
output defaultDomain string = containerAppEnvironment.properties.defaultDomain

@description('The static IP address of the Container Apps environment.')
output staticIp string = containerAppEnvironment.properties.staticIp

@description('Required. Name of the container app environment')
param name string

@description('Required. Location for the container app environment')
param location string

@description('Required. Resource ID of the Log Analytics Workspace for diagnostic settings')
param logAnalyticsResourceId string

@description('Required. tags for the container app environment')
param tags object

@description('Required. Public network access setting for the container app environment')
param publicNetworkAccess string

//param vnetConfiguration object
@description('Required. Flag to enable zone redundancy for the container app environment')
param zoneRedundant bool

//param aspireDashboardEnabled bool

@description('Required. Flag to enable telemetry for the container app environment')
param enableTelemetry bool

@description('Required. Subnet resource ID for the container app environment')
param subnetResourceId string

@description('Required. Application Insights connection string for the container app environment')
param applicationInsightsConnectionString string

var logAnalyticsSubscription = split(logAnalyticsResourceId, '/')[2]
var logAnalyticsResourceGroup = split(logAnalyticsResourceId, '/')[4]
var logAnalyticsName = split(logAnalyticsResourceId, '/')[8]

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2020-08-01' existing = {
  name: logAnalyticsName
  scope: resourceGroup(logAnalyticsSubscription, logAnalyticsResourceGroup)
}

// resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2024-08-02-preview' = {
//   name: name
//   location: location
//   tags: tags
//   properties: {
//     //daprAIConnectionString: appInsights.properties.ConnectionString
//     //daprAIConnectionString: applicationInsights.outputs.connectionString
//     appLogsConfiguration: {
//       destination: 'log-analytics'
//       logAnalyticsConfiguration: {
//         customerId: logAnalyticsWorkspace.properties.customerId
//         #disable-next-line use-secure-value-for-secure-inputs
//         sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
//       }
//     }
//     workloadProfiles: [
//       //THIS IS REQUIRED TO ADD PRIVATE ENDPOINTS
//       {
//         name: 'Consumption'
//         workloadProfileType: 'Consumption'
//       }
//     ]
//     publicNetworkAccess: publicNetworkAccess
//     vnetConfiguration: vnetConfiguration
//     zoneRedundant: zoneRedundant
//   }
// }

module containerAppEnvironment 'br/public:avm/res/app/managed-environment:0.11.1' = {
  name: take('avm.res.app.managed-environment.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    //daprAIConnectionString: applicationInsights.outputs.connectionString //Troubleshoot: ContainerAppsConfiguration.DaprAIConnectionString is invalid.  DaprAIConnectionString can not be set when AppInsightsConfiguration has been set, please set DaprAIConnectionString to null. (Code:InvalidRequestParameterWithDetails
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        #disable-next-line use-secure-value-for-secure-inputs
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      //THIS IS REQUIRED TO ADD PRIVATE ENDPOINTS
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    publicNetworkAccess: publicNetworkAccess
    appInsightsConnectionString: applicationInsightsConnectionString
    zoneRedundant: zoneRedundant
    infrastructureSubnetResourceId: subnetResourceId
    internal: false
  }
}

//TODO: FIX when deployed to vnet. This needs access to Azure to work
// resource aspireDashboard 'Microsoft.App/managedEnvironments/dotNetComponents@2024-10-02-preview' = if (aspireDashboardEnabled) {
//   parent: containerAppEnvironment
//   name: 'aspire-dashboard'
//   properties: {
//     componentType: 'AspireDashboard'
//   }
// }

//output resourceId string = containerAppEnvironment.id
@description('Resource ID of the container app environment')
output resourceId string = containerAppEnvironment.outputs.resourceId
//output location string = containerAppEnvironment.location
@description('Location of the container app environment')
output location string = containerAppEnvironment.outputs.location

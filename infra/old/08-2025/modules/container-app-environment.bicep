param name string
param location string
param logAnalyticsResourceId string
param tags object
param publicNetworkAccess string
//param vnetConfiguration object
param zoneRedundant bool
//param aspireDashboardEnabled bool
param enableTelemetry bool
param subnetResourceId string
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
output resourceId string = containerAppEnvironment.outputs.resourceId
//output location string = containerAppEnvironment.location
output location string = containerAppEnvironment.outputs.location

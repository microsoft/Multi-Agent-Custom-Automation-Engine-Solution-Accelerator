// ========== app-insights.bicep ========== //
// Creates an Application Insights instance linked to a Log Analytics workspace.

targetScope = 'resourceGroup'

@description('The name of the solution, used for naming the Application Insights resource.')
param solutionName string

@description('The Azure region where Application Insights will be deployed.')
param solutionLocation string

@description('The resource ID of the Log Analytics workspace to link to.')
param logAnalyticsWorkspaceId string

var applicationInsightsName = 'appi-${solutionName}'

// ========== Application Insights ========== //

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: solutionLocation
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    WorkspaceResourceId: logAnalyticsWorkspaceId
  }
}

// ========== Outputs ========== //

@description('The resource ID of the Application Insights instance.')
output applicationInsightsId string = applicationInsights.id

@description('The connection string for Application Insights.')
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString

@description('The instrumentation key for Application Insights.')
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey

// ========== log-analytics.bicep ========== //
// Creates a new Log Analytics Workspace or references an existing one.

targetScope = 'resourceGroup'

@description('The name of the solution, used for naming the workspace.')
param solutionName string

@description('The Azure region where the workspace will be deployed.')
param solutionLocation string

@description('The resource ID of an existing Log Analytics workspace. If empty, a new one will be created.')
param existingLogAnalyticsWorkspaceId string = ''

var workspaceName = 'log-${solutionName}'
var useExisting = !empty(existingLogAnalyticsWorkspaceId)
var existingLawSubscription = useExisting ? split(existingLogAnalyticsWorkspaceId, '/')[2] : ''
var existingLawResourceGroup = useExisting ? split(existingLogAnalyticsWorkspaceId, '/')[4] : ''
var existingLawName = useExisting ? split(existingLogAnalyticsWorkspaceId, '/')[8] : ''

// ========== Existing Workspace Reference ========== //

resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' existing = if (useExisting) {
  name: existingLawName
  scope: resourceGroup(existingLawSubscription, existingLawResourceGroup)
}

// ========== New Workspace ========== //

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-07-01' = if (!useExisting) {
  name: workspaceName
  location: solutionLocation
  tags: {}
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

// ========== Outputs ========== //

@description('The resource ID of the Log Analytics workspace.')
output logAnalyticsWorkspaceId string = useExisting ? existingLogAnalyticsWorkspace.id : logAnalytics.id

@description('The name of the Log Analytics workspace.')
output logAnalyticsWorkspaceResourceName string = useExisting ? existingLogAnalyticsWorkspace.name : logAnalytics.name

@description('The resource group of the Log Analytics workspace.')
output logAnalyticsWorkspaceResourceGroup string = useExisting ? existingLawResourceGroup : resourceGroup().name

@description('The subscription ID of the Log Analytics workspace.')
output logAnalyticsWorkspaceSubscription string = useExisting ? existingLawSubscription : subscription().subscriptionId

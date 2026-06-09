// ============================================================================
// Module: App Service
// Description: Creates an Azure App Service (Web App)
// API: Microsoft.Web/sites@2025-05-01
// ============================================================================

@description('Solution name suffix used to derive the resource name.')
param solutionName string

@description('Name of the App Service.')
param name string = solutionName

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Resource ID of the App Service Plan.')
param serverFarmResourceId string

@description('Docker image name (e.g., DOCKER|registry.azurecr.io/image:tag).')
param linuxFxVersion string

@description('Application settings key-value pairs.')
param appSettings object = {}

@description('Whether to enable Always On.')
param alwaysOn bool = true

@description('Kind of web app.')
param kind string = 'app,linux'

@description('Subnet resource ID for VNet integration.')
param virtualNetworkSubnetId string = ''

@description('Public network access setting.')
param publicNetworkAccess string = 'Enabled'

// ============================================================================
// Resource Deployment
// ============================================================================
resource appService 'Microsoft.Web/sites@2025-05-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: serverFarmResourceId
    publicNetworkAccess: publicNetworkAccess
    virtualNetworkSubnetId: !empty(virtualNetworkSubnetId) ? virtualNetworkSubnetId : null
    siteConfig: {
      alwaysOn: alwaysOn
      ftpsState: 'Disabled'
      linuxFxVersion: linuxFxVersion
    }
    endToEndEncryptionEnabled: true
  }

  resource basicPublishingCredentialsPoliciesFtp 'basicPublishingCredentialsPolicies' = {
    name: 'ftp'
    properties: {
      allow: false
    }
  }
  resource basicPublishingCredentialsPoliciesScm 'basicPublishingCredentialsPolicies' = {
    name: 'scm'
    properties: {
      allow: false
    }
  }
}

resource configAppSettings 'Microsoft.Web/sites/config@2025-05-01' = {
  name: 'appsettings'
  parent: appService
  properties: appSettings
}

resource configLogs 'Microsoft.Web/sites/config@2025-05-01' = {
  name: 'logs'
  parent: appService
  properties: {
    applicationLogs: { fileSystem: { level: 'Verbose' } }
    detailedErrorMessages: { enabled: true }
    failedRequestsTracing: { enabled: true }
    httpLogs: { fileSystem: { enabled: true, retentionInDays: 1, retentionInMb: 35 } }
  }
  dependsOn: [configAppSettings]
}

// ============================================================================
// Outputs
// ============================================================================
@description('Resource ID of the App Service.')
output resourceId string = appService.id

@description('Name of the App Service.')
output name string = appService.name

@description('Default hostname of the App Service.')
output defaultHostname string = appService.properties.defaultHostName

@description('URL of the App Service.')
output appUrl string = 'https://${appService.properties.defaultHostName}'

@description('System-assigned identity principal ID.')
output identityPrincipalId string = appService.identity.principalId

// ========== Key Vault ========== //
targetScope = 'resourceGroup'

@description('Solution Name')
param solutionName string

@description('Solution Location')
param solutionLocation string

@description('Application settings for the App Service.')
@secure()
param appSettings object = {}

@description('The resource ID of the App Service Plan.')
param appServicePlanId string

@description('The Docker image name to deploy.')
param appImageName string

@description('The resource ID of the user-assigned managed identity. If empty, only system-assigned identity is used.')
param userassignedIdentityId string = ''

resource appService 'Microsoft.Web/sites@2025-05-01' = {
  name: solutionName
  location: solutionLocation
  identity: userassignedIdentityId == '' ? {
    type: 'SystemAssigned'
  } : {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${userassignedIdentityId}': {}
    }
  }  
  properties: {
    serverFarmId: appServicePlanId
    siteConfig: {
      alwaysOn: true
      ftpsState: 'Disabled'
      linuxFxVersion: appImageName
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

@description('The principal ID of the App Service system-assigned managed identity.')
output identityPrincipalId string = appService.identity.principalId

@description('The URL of the deployed App Service.')
output appUrl string = 'https://${solutionName}.azurewebsites.net'


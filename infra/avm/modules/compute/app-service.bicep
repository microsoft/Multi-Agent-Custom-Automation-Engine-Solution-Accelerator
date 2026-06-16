// ============================================================================
// Module: App Service
// Description: AVM wrapper for Azure App Service (Web App)
// AVM Module: avm/res/web/site:0.23.1
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

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Diagnostic settings for monitoring.')
param diagnosticSettings array = []

@description('Subnet resource ID for VNet integration.')
param virtualNetworkSubnetId string = ''

@description('Public network access setting.')
param publicNetworkAccess string = 'Enabled'

@description('Optional. Whether to route all outbound traffic through the virtual network.')
param vnetRouteAllEnabled bool = false

@description('Optional. Whether to route image pull traffic through the virtual network.')
param imagePullTraffic bool = false

@description('Optional. Whether to route content share traffic through the virtual network.')
param contentShareTraffic bool = false

import { privateEndpointSingleServiceType } from 'br/public:avm/utl/types/avm-common-types:0.5.1'
@description('Optional. Configuration details for private endpoints. For security reasons, it is recommended to use private endpoints whenever possible.')
param privateEndpoints privateEndpointSingleServiceType[]?

// ============================================================================
// AVM Module Deployment
// ============================================================================
module appService 'br/public:avm/res/web/site:0.23.1' = {
  name: take('avm.res.web.site.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    kind: kind
    enableTelemetry: enableTelemetry
    serverFarmResourceId: serverFarmResourceId
    managedIdentities: {
      systemAssigned: true
    }
    siteConfig: {
      alwaysOn: alwaysOn
      ftpsState: 'Disabled'
      linuxFxVersion: linuxFxVersion
      minTlsVersion: '1.2'
    }
    e2eEncryptionEnabled: true
    configs: [
      {
        name: 'appsettings'
        properties: appSettings
      }
      {
        name: 'logs'
        properties: {
          applicationLogs: { fileSystem: { level: 'Verbose' } }
          detailedErrorMessages: { enabled: true }
          failedRequestsTracing: { enabled: true }
          httpLogs: { fileSystem: { enabled: true, retentionInDays: 1, retentionInMb: 35 } }
        }
      }
      {
        name:'web'
        properties: {
          vnetRouteAllEnabled: vnetRouteAllEnabled
          }
      }
    ]
    outboundVnetRouting: {
      contentShareTraffic: contentShareTraffic
      imagePullTraffic: imagePullTraffic
    }
    publicNetworkAccess: publicNetworkAccess
    privateEndpoints: privateEndpoints
    virtualNetworkSubnetResourceId: !empty(virtualNetworkSubnetId) ? virtualNetworkSubnetId : null
    basicPublishingCredentialsPolicies: [
      {
        name: 'ftp'
        allow: false
      }
      {
        name: 'scm'
        allow: false
      }
    ]
    diagnosticSettings: !empty(diagnosticSettings) ? diagnosticSettings : []
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('Resource ID of the App Service.')
output resourceId string = appService.outputs.resourceId

@description('Name of the App Service.')
output name string = appService.outputs.name

@description('Default hostname of the App Service.')
output defaultHostname string = appService.outputs.defaultHostname

@description('URL of the App Service.')
output appUrl string = 'https://${appService.outputs.defaultHostname}'

@description('System-assigned identity principal ID.')
output identityPrincipalId string = appService.outputs.?systemAssignedMIPrincipalId ?? ''

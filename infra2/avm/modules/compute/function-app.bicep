// ============================================================================
// Module: Azure Function App (AVM)
// ============================================================================

@description('Name of the function app.')
param name string

@description('Azure region for deployment.')
param location string

@description('Resource tags.')
param tags object = {}

@description('Enable Azure telemetry collection.')
param enableTelemetry bool = true

@description('Resource ID of the App Service Plan.')
param serverFarmResourceId string

@description('Resource ID of the storage account for function app.')
param storageAccountResourceId string

@description('Name of the storage account.')
param storageAccountName string

@description('Managed identity configuration.')
param managedIdentities object = {
  systemAssigned: true
}

@description('App settings as name-value pairs.')
param appSettings array = []

@description('Site configuration object.')
param siteConfig object = {}

@description('Runtime stack.')
param runtimeStack string = 'python'

@description('Runtime version.')
param runtimeVersion string = '3.11'

// ============================================================================
// Function App (AVM)
// ============================================================================

var baseAppSettings = [
  { name: 'AzureWebJobsStorage__accountName', value: storageAccountName }
  { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
  { name: 'FUNCTIONS_WORKER_RUNTIME', value: runtimeStack }
]

var mergedAppSettings = concat(baseAppSettings, appSettings)

module functionApp 'br/public:avm/res/web/site:0.15.0' = {
  name: take('avm.res.web.site.func.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    kind: 'functionapp,linux'
    serverFarmResourceId: serverFarmResourceId
    storageAccountResourceId: storageAccountResourceId
    managedIdentities: managedIdentities
    appSettingsKeyValuePairs: reduce(mergedAppSettings, {}, (cur, next) => union(cur, { '${next.name}': next.value }))
    siteConfig: union({
      linuxFxVersion: '${toUpper(runtimeStack)}|${runtimeVersion}'
    }, siteConfig)
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the function app.')
output name string = functionApp.outputs.name

@description('The resource ID of the function app.')
output resourceId string = functionApp.outputs.resourceId

@description('The default hostname of the function app.')
output defaultHostName string = functionApp.outputs.defaultHostname

@description('The principal ID of the system-assigned managed identity.')
output principalId string = functionApp.outputs.?systemAssignedMIPrincipalId ?? ''

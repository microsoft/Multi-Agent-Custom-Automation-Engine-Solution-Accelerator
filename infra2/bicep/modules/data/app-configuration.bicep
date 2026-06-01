targetScope = 'resourceGroup'

@description('The name of the solution, used as the base for resource naming.')
param solutionName string

@description('The Azure region where App Configuration will be deployed.')
param solutionLocation string

@description('Tags to apply to the resource.')
param tags object = {}

@description('The SKU tier for the App Configuration store.')
param sku string = 'Standard'

@description('Indicates whether local authentication is disabled for the App Configuration store.')
param disableLocalAuth bool = false

@description('Key-values to create in the App Configuration store.')
param keyValues array = []

var name = 'appcs-${solutionName}'

resource appConfiguration 'Microsoft.AppConfiguration/configurationStores@2023-03-01' = {
  name: name
  location: solutionLocation
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    disableLocalAuth: disableLocalAuth
    publicNetworkAccess: 'Enabled'
  }
}

resource configurationKeyValues 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = [for keyValue in keyValues: {
  name: keyValue.name
  parent: appConfiguration
  properties: {
    value: keyValue.value
  }
}]

@description('The name of the App Configuration store.')
output name string = appConfiguration.name

@description('The endpoint of the App Configuration store.')
output endpoint string = appConfiguration.properties.endpoint

@description('The resource ID of the App Configuration store.')
output id string = appConfiguration.id

targetScope = 'resourceGroup'

@description('Short name used to generate resource names.')
@minLength(3)
@maxLength(12)
param solutionName string = 'demoapp'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Linux container image for the App Service.')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Tags to apply to all resources.')
param tags object = {
  SecurityControl: 'Ignore'
}

var nameSuffix = toLower('${replace(solutionName, '-', '')}${uniqueString(resourceGroup().id)}')

module storageAccount './modules/data/storage-account.bicep' = {
  params: {
    solutionName: nameSuffix
    name: take('st${nameSuffix}', 24)
    location: location
    tags: tags
  }
}

module containerRegistry './modules/compute/container-registry.bicep' = {
  params: {
    solutionName: nameSuffix
    name: take('cr${nameSuffix}', 50)
    location: location
    tags: tags
    sku: 'Basic'
  }
}

module appServicePlan './modules/compute/app-service-plan.bicep' = {
  params: {
    solutionName: nameSuffix
    name: 'asp-${nameSuffix}'
    location: location
    tags: tags
    skuName: 'B1'
  }
}

module appService './modules/compute/app-service.bicep' = {
  params: {
    name: 'app-${nameSuffix}'
    location: location
    tags: tags
    serverFarmResourceId: appServicePlan.outputs.resourceId
    linuxFxVersion: 'DOCKER|${containerImage}'
  }
}

module acrPullRoleAssignment './modules/identity/role-assignment.bicep' = {
  params: {
    appServicePrincipalId: appService.outputs.identityPrincipalId
    containerRegistryName: containerRegistry.outputs.name
  }
}

output storageAccountName string = storageAccount.outputs.name
output containerRegistryName string = containerRegistry.outputs.name
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output appServiceName string = appService.outputs.name
output appServiceUrl string = appService.outputs.appUrl

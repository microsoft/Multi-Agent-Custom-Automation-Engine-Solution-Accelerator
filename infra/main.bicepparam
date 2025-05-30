using './main.bicep'

param solutionPrefix = null //Type a string value to customize the prefix for your resource names
param solutionLocation = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param azureOpenAILocation = readEnvironmentVariable('AZURE_ENV_OPENAI_LOCATION', 'eastus2')
param logAnalyticsWorkspaceConfiguration = {
  dataRetentionInDays: 30
}
param applicationInsightsConfiguration = {
  retentionInDays: 30
}
param virtualNetworkConfiguration = {
  enabled: false
}
param aiFoundryStorageAccountConfiguration = {
  sku: 'Standard_LRS'
  allowBlobPublicAccess: false
}
param containerAppEnvironmentConfiguration = {
  zoneRedundant: false
}
param cosmosDbAccountConfiguration = {
  location: 'eastus2'
  // Explicitly disable zonal redundancy to avoid quota/availability issues
}
param webServerFarmConfiguration = {
  skuCapacity: 1
  skuName: 'S1'
}

param aiFoundryAiServicesConfiguration = {
  modelCapacity: 140  // Fix the typo in the property name
}

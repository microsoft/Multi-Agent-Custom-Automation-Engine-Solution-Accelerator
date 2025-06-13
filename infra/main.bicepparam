using './main.bicep'

param solutionPrefix = readEnvironmentVariable('AZURE_ENV_NAME', 'macae')
param solutionLocation = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
param azureOpenAILocation = readEnvironmentVariable('AZURE_ENV_OPENAI_LOCATION', 'swedencentral')
param modelDeploymentType = readEnvironmentVariable('AZURE_ENV_MODEL_DEPLOYMENT_TYPE', 'GlobalStandard')
param gptModelName = readEnvironmentVariable('AZURE_ENV_MODEL_NAME', 'gpt-4o')
param gptModelVersion = readEnvironmentVariable('AZURE_ENV_MODEL_VERSION', '2024-08-06')
param imageTag = readEnvironmentVariable('AZURE_ENV_IMAGETAG', 'latest')
param enableTelemetry = bool(readEnvironmentVariable('AZURE_ENV_ENABLE_TELEMETRY', 'true'))
param logAnalyticsWorkspaceConfiguration = {
  dataRetentionInDays: 30
  existingWorkspaceResourceId: ''
}
param applicationInsightsConfiguration = {
  retentionInDays: 30
}
param virtualNetworkConfiguration = {
  enabled: false
}
// param aiFoundryStorageAccountConfiguration = {
//   sku: 'Standard_LRS'
// }
param webServerFarmConfiguration = {
  skuCapacity: 1
  skuName: 'B2'
}

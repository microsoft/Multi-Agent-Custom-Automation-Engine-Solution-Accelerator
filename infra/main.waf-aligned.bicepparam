using './main.bicep'

param solutionPrefix = null //Type a string value to customize the prefix for your resource names
param solutionLocation = readEnvironmentVariable('AZURE_LOCATION', 'swedencentral')
param azureOpenAILocation = readEnvironmentVariable('AZURE_ENV_OPENAI_LOCATION', 'swedencentral')
param virtualMachineConfiguration = {
  adminUsername: 'adminuser'
  adminPassword: 'P@ssw0rd1234'
}

param logAnalyticsWorkspaceConfiguration = {
  existingWorkspaceResourceId: ''
}

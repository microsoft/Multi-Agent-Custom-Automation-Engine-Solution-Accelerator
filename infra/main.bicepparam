using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'macaetemplate')
param azureOpenAILocation = readEnvironmentVariable('AZURE_ENV_LOCATION', 'eastus2')

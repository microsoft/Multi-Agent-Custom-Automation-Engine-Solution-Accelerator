using './main.bicep'

param azureOpenAILocation = readEnvironmentVariable('AZURE_LOCATION','japaneast')
param prefix = readEnvironmentVariable('AZURE_ENV_NAME','azdtemp')

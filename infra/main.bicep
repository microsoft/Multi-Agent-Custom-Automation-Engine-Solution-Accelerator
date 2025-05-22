targetScope = 'resourceGroup'

@allowed([
  'australiaeast'
  'brazilsouth'
  'canadacentral'
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'germanywestcentral'
  'japaneast'
  'koreacentral'
  'northcentralus'
  'norwayeast'
  'polandcentral'
  'southafricanorth'
  'southcentralus'
  'southindia'
  'swedencentral'
  'switzerlandnorth'
  'uaenorth'
  'uksouth'
  'westeurope'
  'westus'
  'westus3'
])
@description('Location for all Ai services resources. This location can be different from the resource group location.')
param azureOpenAILocation string

@minLength(3)
@maxLength(20)
@description('A unique prefix for all resources in this deployment. This should be 3-20 characters long:')
param environmentName string

@description('Set this if you want to deploy to a different region than the resource group. Otherwise, it will use the resource group location by default.')
param AZURE_LOCATION string=''
var solutionLocation = empty(AZURE_LOCATION) ? resourceGroup().location : AZURE_LOCATION

var uniqueId = toLower(uniqueString(subscription().id, environmentName, solutionLocation))
var solutionPrefix = 'ma${padLeft(take(uniqueId, 12), 12, '0')}'

// Load the abbrevations file required to name the azure resources.
var abbrs = loadJsonContent('./abbreviations.json')

@description('Tags to apply to all deployed resources')
param tags object = {}

@description('The size of the resources to deploy, defaults to a mini size')
param resourceSize {
  gpt4oCapacity: int
  containerAppSize: {
    cpu: string
    memory: string
    minReplicas: int
    maxReplicas: int
  }
} = {
  gpt4oCapacity: 1
  containerAppSize: {
    cpu: '2.0'
    memory: '4.0Gi'
    minReplicas: 1
    maxReplicas: 1
  }
}
param capacity int = 140

var modelVersion = '2024-08-06'
var aiServicesName = '${abbrs.ai.aiServices}${solutionPrefix}'
var deploymentType = 'GlobalStandard'
var gptModelVersion = 'gpt-4o'
var appVersion = 'latest'
var resgistryName = 'biabcontainerreg'
var dockerRegistryUrl = 'https://${resgistryName}.azurecr.io'

@description('URL for frontend docker image')
var backendDockerImageURL = '${resgistryName}.azurecr.io/macaebackend:${appVersion}'
var frontendDockerImageURL = '${resgistryName}.azurecr.io/macaefrontend:${appVersion}'

//var uniqueNameFormat = '${solutionPrefix}-{0}-${uniqueString(resourceGroup().id, solutionPrefix)}'
var aoaiApiVersion = '2025-01-01-preview'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${abbrs.managementGovernance.logAnalyticsWorkspace}${solutionPrefix}'
  location: solutionLocation
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02-preview' = {
  name: '${abbrs.managementGovernance.applicationInsights}${solutionPrefix}'
  location: solutionLocation
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

var aiModelDeployments = [
  {
    name: gptModelVersion
    model: gptModelVersion
    version: modelVersion
    sku: {
      name: deploymentType
      capacity: capacity
    }
    raiPolicyName: 'Microsoft.Default'
  }
]

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: aiServicesName
  location: azureOpenAILocation
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    customSubDomainName: aiServicesName
    apiProperties: {
      //statisticsEnabled: false
    }
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource aiServicesDeployments 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [
  for aiModeldeployment in aiModelDeployments: {
    parent: aiServices //aiServices_m
    name: aiModeldeployment.name
    properties: {
      model: {
        format: 'OpenAI'
        name: aiModeldeployment.model
        version: aiModeldeployment.version
      }
      raiPolicyName: aiModeldeployment.raiPolicyName
    }
    sku: {
      name: aiModeldeployment.sku.name
      capacity: aiModeldeployment.sku.capacity
    }
  }
]

module kvault 'deploy_keyvault.bicep' = {
  name: 'deploy_keyvault'
  params: {
    solutionLocation: solutionLocation
    managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
    keyvaultName: '${abbrs.security.keyVault}${solutionPrefix}'
  }
  scope: resourceGroup(resourceGroup().name)
}

// First, add this section to store the AI Services key in Key Vault


// Then modify the aifoundry module to reference the secret securely
module aifoundry 'deploy_ai_foundry.bicep' = {
  name: 'deploy_ai_foundry'
  params: {
    solutionName: solutionPrefix
    solutionLocation: azureOpenAILocation
    keyVaultName: kvault.outputs.keyvaultName
    gptModelName: gptModelVersion
    gptModelVersion: gptModelVersion
    managedIdentityObjectId: managedIdentityModule.outputs.managedIdentityOutput.objectId
    aiServicesEndpoint: aiServices.properties.endpoint
    aiServicesKey: aiServices.listKeys().key1
    aiServicesId: aiServices.id
  }
  scope: resourceGroup(resourceGroup().name)
}

resource aoaiUserRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-05-01-preview' existing = {
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' //'Cognitive Services OpenAI User'
}

resource acaAoaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerApp.id, aiServices.id, aoaiUserRoleDefinition.id)
  scope: aiServices
  properties: {
    principalId: containerApp.identity.principalId
    roleDefinitionId: aoaiUserRoleDefinition.id
    principalType: 'ServicePrincipal'
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${abbrs.databases.cosmosDBDatabase}${solutionPrefix}'
  location: solutionLocation
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: false
    locations: [
      {
        failoverPriority: 0
        locationName: solutionLocation
      }
    ]
    capabilities: [{ name: 'EnableServerless' }]
    disableLocalAuth: true
  }

  resource contributorRoleDefinition 'sqlRoleDefinitions' existing = {
    name: '00000000-0000-0000-0000-000000000002'
  }

  resource macaeDb 'sqlDatabases' = {
    name: 'macae'
    properties: {
      resource: {
        id: 'macae'
        createMode: 'Default'
      }
    }

    resource memoryContainer 'containers' = {
      name: 'memory'
      properties: {
        resource: {
          id: 'memory'
          partitionKey: {
            kind: 'Hash'
            version: 2
            paths: [
              '/session_id'
            ]
          }
        }
      }
    }
  }
}
// Define existing ACR resource

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: '${abbrs.security.managedIdentity}${solutionPrefix}-containerapp-pull'
  location: solutionLocation
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${abbrs.containers.containerAppsEnvironment}${solutionPrefix}'
  location: solutionLocation
  tags: tags
  properties: {
    daprAIConnectionString: appInsights.properties.ConnectionString
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
  resource aspireDashboard 'dotNetComponents@2024-02-02-preview' = {
    name: 'aspire-dashboard'
    properties: {
      componentType: 'AspireDashboard'
    }
  }
}

resource acaCosomsRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  name: guid(containerApp.id, cosmos::contributorRoleDefinition.id)
  parent: cosmos
  properties: {
    principalId: containerApp.identity.principalId
    roleDefinitionId: cosmos::contributorRoleDefinition.id
    scope: cosmos.id
  }
}

@description('')
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${abbrs.containers.containerApp}${solutionPrefix}-backend'
  location: solutionLocation
  tags: tags
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        targetPort: 8000
        external: true
        corsPolicy: {
          allowedOrigins: [
            'https://${abbrs.compute.webApp}${solutionPrefix}-frontend.azurewebsites.net'
            'http://${abbrs.compute.webApp}${solutionPrefix}-frontend.azurewebsites.net'
          ]
        }
      }
      activeRevisionsMode: 'Single'
    }
    template: {
      scale: {
        minReplicas: resourceSize.containerAppSize.minReplicas
        maxReplicas: resourceSize.containerAppSize.maxReplicas
        rules: [
          {
            name: 'http-scaler'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
      containers: [
        {
          name: 'backend'
          image: backendDockerImageURL
          resources: {
            cpu: json(resourceSize.containerAppSize.cpu)
            memory: resourceSize.containerAppSize.memory
          }
          env: [
            {
              name: 'COSMOSDB_ENDPOINT'
              value: cosmos.properties.documentEndpoint
            }
            {
              name: 'COSMOSDB_DATABASE'
              value: cosmos::macaeDb.name
            }
            {
              name: 'COSMOSDB_CONTAINER'
              value: cosmos::macaeDb::memoryContainer.name
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: replace(aiServices.properties.endpoint, 'cognitiveservices.azure.com', 'openai.azure.com')
            }
            {
              name: 'AZURE_OPENAI_MODEL_NAME'
              value: gptModelVersion
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
              value: gptModelVersion
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: aoaiApiVersion
            }
            {
              name: 'APPLICATIONINSIGHTS_INSTRUMENTATION_KEY'
              value: appInsights.properties.InstrumentationKey
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
            {
              name: 'AZURE_AI_AGENT_PROJECT_CONNECTION_STRING'
              value: aifoundry.outputs.projectConnectionString
            }
            {
              name: 'AZURE_AI_SUBSCRIPTION_ID'
              value: subscription().subscriptionId
            }
            {
              name: 'AZURE_AI_RESOURCE_GROUP'
              value: resourceGroup().name
            }
            {
              name: 'AZURE_AI_PROJECT_NAME'
              value: aifoundry.outputs.aiProjectName
            }
            {
              name: 'FRONTEND_SITE_NAME'
              value: 'https://${abbrs.compute.webApp}${solutionPrefix}-frontend.azurewebsites.net'
            }
          ]
        }
      ]
    }
  }
}
resource frontendAppServicePlan 'Microsoft.Web/serverfarms@2021-02-01' = {
  name: '${abbrs.compute.appServicePlan}${solutionPrefix}-frontend'
  location: solutionLocation
  tags: tags
  sku: {
    name: 'B2'
    capacity: 1
    tier: 'Basic'
  }
  properties: {
    reserved: true
  }
  kind: 'linux' // Add this line to support Linux containers
}

resource frontendAppService 'Microsoft.Web/sites@2021-02-01' = {
  name: '${abbrs.compute.webApp}${solutionPrefix}-frontend'
  location: solutionLocation
  tags: tags
  kind: 'app,linux,container'
  properties: {
    serverFarmId: frontendAppServicePlan.id
    reserved: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${frontendDockerImageURL}'
      appSettings: [
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: dockerRegistryUrl
        }
        {
          name: 'WEBSITES_PORT'
          value: '3000'
        }
        {
          name: 'WEBSITES_CONTAINER_START_TIME_LIMIT'
          value: '1800'
        }
        {
          name: 'BACKEND_API_URL'
          value: 'https://${containerApp.properties.configuration.ingress.fqdn}'
        }
        {
          name: 'AUTH_ENABLED'
          value: 'false'
        }
      ]
    }
  }
  dependsOn: [containerApp]
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity.id}': {}
    }
  }
}

resource aiHubProject 'Microsoft.MachineLearningServices/workspaces@2024-01-01-preview' existing = {
  name: '${abbrs.ai.aiHubProject}${solutionPrefix}' // aiProjectName must be calculated - available at main start.
}

resource aiDeveloper 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: '64702f94-c441-49e6-a78b-ef80e0188fee'
}

resource aiDeveloperAccessProj 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerApp.name, aiHubProject.id, aiDeveloper.id)
  scope: aiHubProject
  properties: {
    roleDefinitionId: aiDeveloper.id
    principalId: containerApp.identity.principalId
  }
}

var cosmosAssignCli = 'az cosmosdb sql role assignment create --resource-group "${resourceGroup().name}" --account-name "${cosmos.name}" --role-definition-id "${cosmos::contributorRoleDefinition.id}" --scope "${cosmos.id}" --principal-id "${containerApp.identity.principalId}"'

module managedIdentityModule 'deploy_managed_identity.bicep' = {
  name: 'deploy_managed_identity'
  params: {
    //solutionLocation: location
    managedIdentityId: pullIdentity.id
    managedIdentityPropPrin: pullIdentity.properties.principalId
    managedIdentityLocation: pullIdentity.location
    miName: '${abbrs.security.managedIdentity}${solutionPrefix}'
  }
  scope: resourceGroup(resourceGroup().name)
}

module deploymentScriptCLI 'br/public:avm/res/resources/deployment-script:0.5.1' = {
  name: 'deploymentScriptCLI'
  params: {
    // Required parameters
    kind: 'AzureCLI'
    name: 'rdsmin001'
    // Non-required parameters
    azCliVersion: '2.69.0'
    location: solutionLocation
    managedIdentities: {
      userAssignedResourceIds: [
        managedIdentityModule.outputs.managedIdentityId
      ]
    }
    scriptContent: cosmosAssignCli
  }
}

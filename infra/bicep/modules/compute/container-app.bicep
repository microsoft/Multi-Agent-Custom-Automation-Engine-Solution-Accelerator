targetScope = 'resourceGroup'

@description('The name of the Container App.')
param name string

@description('The Azure region where the Container App will be deployed.')
param solutionLocation string

@description('Tags to apply to the resource.')
param tags object = {}

@description('The resource ID of the Container Apps environment.')
param environmentId string

@description('The containers to deploy in the Container App template.')
param containers array

@description('Indicates whether the Container App ingress is externally accessible.')
param ingressExternal bool = true

@description('The ingress target port exposed by the Container App.')
param ingressTargetPort int

@description('The ingress transport protocol for the Container App.')
param ingressTransport string = 'auto'

@description('Container registry definitions for pulling container images.')
param registries array = []

@description('Secrets available to the Container App.')
param secrets array = []

@description('The managed identity type assigned to the Container App.')
param identityType string = 'SystemAssigned'

@description('The user-assigned identities to associate with the Container App when applicable.')
param userAssignedIdentities object = {}

@description('The CORS policy to apply to ingress when needed.')
param corsPolicy object = {}

@description('The minimum number of replicas for the Container App.')
param scaleMinReplicas int = 0

@description('The maximum number of replicas for the Container App.')
param scaleMaxReplicas int = 10

var containerAppIdentity = identityType == 'None' ? null : {
  type: identityType
  userAssignedIdentities: contains(identityType, 'UserAssigned') ? userAssignedIdentities : null
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: solutionLocation
  tags: tags
  identity: containerAppIdentity
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      ingress: {
        external: ingressExternal
        targetPort: ingressTargetPort
        transport: ingressTransport
        allowInsecure: false
        corsPolicy: empty(corsPolicy) ? null : corsPolicy
      }
      registries: registries
      secrets: secrets
    }
    template: {
      containers: containers
      scale: {
        minReplicas: scaleMinReplicas
        maxReplicas: scaleMaxReplicas
      }
    }
  }
}

@description('The name of the Container App.')
output name string = containerApp.name

@description('The resource ID of the Container App.')
output id string = containerApp.id

@description('The fully qualified domain name of the Container App ingress endpoint.')
output fqdn string = containerApp.properties.configuration.ingress.fqdn

@description('The principal ID of the system-assigned managed identity, if enabled.')
output principalId string = contains(identityType, 'SystemAssigned') ? containerApp.identity.principalId : ''

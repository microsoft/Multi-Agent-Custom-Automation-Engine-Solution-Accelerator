// ============================================================================
// Module: Azure Container App (AVM)
// ============================================================================

@description('Name of the container app.')
param name string

@description('Azure region for deployment.')
param location string

@description('Resource tags.')
param tags object = {}

@description('Enable Azure telemetry collection.')
param enableTelemetry bool = true

@description('Resource ID of the Container Apps Environment.')
param environmentResourceId string

@description('Container definitions.')
param containers array

@description('Enable external ingress.')
param ingressExternal bool = true

@description('Target port for ingress.')
param ingressTargetPort int

@description('Ingress transport protocol.')
@allowed(['auto', 'http', 'http2', 'tcp'])
param ingressTransport string = 'auto'

@description('Whether to allow insecure ingress connections.')
param ingressAllowInsecure bool = false

@description('Container registry configurations.')
param registries array = []

@description('Secret definitions.')
param secrets array = []

@description('Managed identity configuration.')
param managedIdentities object = {}

@description('CORS policy configuration. Must include allowedOrigins if provided.')
param corsPolicy object = {}

@description('Whether to apply CORS policy.')
var applyCorsPolicy = !empty(corsPolicy)

@description('Minimum number of replicas.')
param scaleMinReplicas int = 0

@description('Maximum number of replicas.')
param scaleMaxReplicas int = 10

// ============================================================================
// Container App (AVM)
// ============================================================================

module containerApp 'br/public:avm/res/app/container-app:0.12.0' = {
  name: take('avm.res.app.containerapp.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    environmentResourceId: environmentResourceId
    containers: containers
    ingressExternal: ingressExternal
    ingressTargetPort: ingressTargetPort
    ingressTransport: ingressTransport
    ingressAllowInsecure: ingressAllowInsecure
    registries: !empty(registries) ? registries : []
    managedIdentities: !empty(managedIdentities) ? managedIdentities : {}
    corsPolicy: applyCorsPolicy ? corsPolicy : null
    scaleMinReplicas: scaleMinReplicas
    scaleMaxReplicas: scaleMaxReplicas
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the container app.')
output name string = containerApp.outputs.name

@description('The resource ID of the container app.')
output resourceId string = containerApp.outputs.resourceId

@description('The FQDN of the container app.')
output fqdn string = containerApp.outputs.fqdn

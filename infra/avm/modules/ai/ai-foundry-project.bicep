// ============================================================================
// Module: AI Foundry Project (Account + Project)
// Description: AVM wrapper for Azure AI Services account creation and
//              AI Foundry project provisioning. Generic, reusable across GSAs.
// AVM Module: avm/res/cognitive-services/account
// WAF: https://learn.microsoft.com/azure/well-architected/service-guides/azure-openai
// ============================================================================

@description('Required. Solution name suffix used to generate resource names.')
param solutionName string

@description('Optional. Override name for the AI Services account. Defaults to aif-{solutionName}.')
param name string = 'aif-${solutionName}'

@description('Optional. Override name for the AI Foundry project. Defaults to proj-{solutionName}.')
param projectName string = 'proj-${solutionName}'

@description('Required. Azure region for the resources.')
param location string

@description('Optional. Tags to apply to resources.')
param tags object = {}

@description('Optional. SKU name for the AI Services account.')
param skuName string = 'S0'

@description('Optional. Whether to disable local (key-based) authentication.')
param disableLocalAuth bool = true

@description('Optional. Whether to allow project management (AI Foundry hub).')
param allowProjectManagement bool = true

@description('Optional. Public network access setting.')
param publicNetworkAccess string = 'Enabled'

@description('Optional. Managed identity type for the resources.')
@allowed(['SystemAssigned', 'UserAssigned', 'SystemAssigned, UserAssigned', 'None'])
param identityType string = 'SystemAssigned'

@description('Optional. Network ACLs default action.')
@allowed(['Allow', 'Deny'])
param networkAclsDefaultAction string = 'Allow'

// --- WAF: Monitoring ---
@description('Optional. Diagnostic settings for the resource.')
param diagnosticSettings array?

// --- WAF: Telemetry ---
@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

// --- Role Assignments ---
@description('Optional. Array of role assignments to create on the AI Services account.')
param roleAssignments array?

// ============================================================================
// AI Services Account (AVM Module)
// ============================================================================
module aiServicesAccount 'br/public:avm/res/cognitive-services/account:0.14.2' = {
  name: take('avm.res.cognitive-services.account.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    sku: skuName
    kind: 'AIServices'
    disableLocalAuth: disableLocalAuth
    allowProjectManagement: allowProjectManagement
    customSubDomainName: name
    networkAcls: {
      defaultAction: networkAclsDefaultAction
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: publicNetworkAccess
    managedIdentities: {
      systemAssigned: true
    }
    diagnosticSettings: diagnosticSettings
    deployments: []
    roleAssignments: roleAssignments
    // Private endpoints deployed separately to avoid AccountProvisioningStateInvalid
    privateEndpoints: []
  }
}

// ============================================================================
// AI Foundry Project
// ============================================================================
resource aiServicesResource 'Microsoft.CognitiveServices/accounts@2025-12-01' existing = {
  name: name
  dependsOn: [aiServicesAccount]
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-12-01' = {
  parent: aiServicesResource
  name: projectName
  location: location
  tags: tags
  kind: 'AIServices'
  identity: {
    type: identityType
  }
  properties: {}
  dependsOn: [aiServicesAccount]
}

// ============================================================================
// Outputs
// ============================================================================

@description('Resource ID of the AI Services account.')
output resourceId string = aiServicesAccount.outputs.resourceId

@description('Name of the AI Services account.')
output name string = aiServicesAccount.outputs.name

@description('Endpoint of the AI Services account.')
output endpoint string = aiServicesAccount.outputs.endpoint

@description('System-assigned identity principal ID of the AI Services account.')
output principalId string = aiServicesAccount.outputs.systemAssignedMIPrincipalId

@description('Resource ID of the AI Foundry project.')
output projectResourceId string = aiProject.id

@description('Name of the AI Foundry project.')
output projectName string = aiProject.name

@description('AI Foundry project endpoint.')
output projectEndpoint string = aiProject.properties.endpoints['AI Foundry API']

@description('System-assigned identity principal ID of the project.')
output projectIdentityPrincipalId string = aiProject.identity.principalId

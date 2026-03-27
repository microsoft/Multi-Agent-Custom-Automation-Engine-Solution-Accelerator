// ========================================================================
// AI Services Account Networking Update
// ========================================================================
// Updates networking properties on an existing AI Services account for
// WAF-aligned private networking support. Used when deploying with an
// existing AI Foundry project (same or cross subscription) and
// enablePrivateNetworking is true.
//
// This module performs a PUT on the existing account, preserving critical
// writable properties while adding networkInjections and updating
// publicNetworkAccess. Child resources (deployments, projects) are
// unaffected by the account-level PUT.
//
// Prerequisites:
//   - The deploying identity must have Cognitive Services Contributor
//     (or equivalent) on the existing account.
//   - For cross-subscription, the AI Services account must have permission
//     to join the agent subnet (Microsoft.Network/virtualNetworks/subnets/join/action).
// ========================================================================

@description('Required. The name of the existing Cognitive Services account.')
param name string

@description('Required. The location of the account.')
param location string

@description('Required. The kind of the account (e.g., AIServices).')
param kind string

@description('Required. The SKU name of the account (e.g., S0).')
param skuName string

@description('Required. The custom subdomain name (must be preserved — cannot be unset once configured).')
param customSubDomainName string

@description('Optional. Whether local auth is disabled on the account.')
param disableLocalAuth bool = true

@description('Optional. Whether project management is allowed on the account.')
param allowProjectManagement bool = true

@description('Required. The agent subnet resource ID for network injection.')
param agentSubnetResourceId string

@description('Optional. Public network access setting. Defaults to Disabled for WAF alignment.')
param publicNetworkAccess string = 'Disabled'

@description('Optional. Network ACLs configuration preserved from the existing account.')
param networkAcls object = { defaultAction: 'Allow', virtualNetworkRules: [], ipRules: [] }

@description('Optional. The identity type of the account (e.g., SystemAssigned, UserAssigned, SystemAssigned,UserAssigned).')
param identityType string = 'SystemAssigned'

@description('Optional. The user-assigned identity resource IDs to preserve on the account.')
param userAssignedIdentityResourceIds string[] = []

@description('Optional. Tags to preserve on the resource.')
param tags object = {}

// Construct the identity object preserving existing configuration.
// Uses the same reduce+map+union pattern as web-sites.bicep for building
// the userAssignedIdentities dictionary from an array of resource IDs.
var formattedUserAssignedIdentities = reduce(
  map(userAssignedIdentityResourceIds, (id) => { '${id}': {} }),
  {},
  (cur, next) => union(cur, next)
)

var identityConfig = {
  type: identityType
  userAssignedIdentities: !empty(formattedUserAssignedIdentities) ? formattedUserAssignedIdentities : null
}

// Redeclare the existing account with networking configuration.
// Critical writable properties are preserved via parameters sourced from
// the existing resource reference in the calling template.
resource accountNetworkingUpdate 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  kind: kind
  sku: { name: skuName }
  identity: identityConfig
  tags: tags
  properties: {
    customSubDomainName: customSubDomainName
    disableLocalAuth: disableLocalAuth
    allowProjectManagement: allowProjectManagement
    networkAcls: networkAcls
    publicNetworkAccess: publicNetworkAccess
    networkInjections: [
      {
        scenario: 'agent'
        subnetArmId: agentSubnetResourceId
        useMicrosoftManagedNetwork: false
      }
    ]
  }
}

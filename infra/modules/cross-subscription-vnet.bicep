// ========================================================================
// Cross-Subscription VNet for AI Foundry Agent Network Injection
// ========================================================================
// Creates a VNet with an agent subnet in the Foundry's subscription so
// that networkInjections can be used for AI Foundry agents. The subnet
// must reside in the same subscription as the AI Services account.
//
// This VNet is peered (Foundry-side) back to the deployment VNet so
// that agent compute injected into this subnet can reach private
// endpoints (Cosmos DB, Storage, Search, etc.) in the deployment VNet.
// ========================================================================

@description('Required. Name for the VNet in the Foundry subscription.')
param name string

@description('Required. Azure region for the VNet (should match AI Services region or support peering).')
param location string

@description('Required. Address space for the Foundry VNet. Must NOT overlap with the deployment VNet.')
param addressPrefixes array

@description('Required. Address prefix for the agent subnet.')
param agentSubnetAddressPrefix string

@description('Required. Address prefix for the backend subnet (used for private endpoints).')
param backendSubnetAddressPrefix string

@description('Required. Resource ID of the deployment VNet (remote side) for peering.')
param remoteVirtualNetworkId string

@description('Optional. Tags to apply to resources.')
param tags object = {}

// NSG for the agent subnet
resource agentNsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-agent-${name}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'deny-hop-outbound'
        properties: {
          access: 'Deny'
          destinationAddressPrefix: '*'
          destinationPortRanges: [
            '22'
            '3389'
          ]
          direction: 'Outbound'
          priority: 200
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
        }
      }
    ]
  }
}

// NSG for the backend subnet (private endpoints)
resource backendNsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-backend-${name}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'deny-hop-outbound'
        properties: {
          access: 'Deny'
          destinationAddressPrefix: '*'
          destinationPortRanges: [
            '22'
            '3389'
          ]
          direction: 'Outbound'
          priority: 200
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
        }
      }
    ]
  }
}

// VNet in the Foundry subscription with agent + backend subnets
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: addressPrefixes
    }
    subnets: [
      {
        name: 'agent'
        properties: {
          addressPrefix: agentSubnetAddressPrefix
          networkSecurityGroup: {
            id: agentNsg.id
          }
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'backend'
        properties: {
          addressPrefix: backendSubnetAddressPrefix
          networkSecurityGroup: {
            id: backendNsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Peering from Foundry VNet -> Deployment VNet
resource peeringToDeployment 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-05-01' = {
  parent: vnet
  name: 'peer-to-deployment-vnet'
  properties: {
    remoteVirtualNetwork: {
      id: remoteVirtualNetworkId
    }
    allowVirtualNetworkAccess: true
    allowForwardedTraffic: true
    allowGatewayTransit: false
    useRemoteGateways: false
  }
}

@description('The resource ID of the created VNet.')
output resourceId string = vnet.id

@description('The name of the created VNet.')
output name string = vnet.name

@description('The resource ID of the agent subnet.')
output agentSubnetResourceId string = vnet.properties.subnets[0].id

@description('The resource ID of the backend subnet (for private endpoints).')
output backendSubnetResourceId string = vnet.properties.subnets[1].id

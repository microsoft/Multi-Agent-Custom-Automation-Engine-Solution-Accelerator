/****************************************************************************************************************************/
// Networking - NSGs, VNET and Subnets. Each subnet has its own NSG
/****************************************************************************************************************************/
@description('Name of the virtual network.')
param name string 

@description('Azure region to deploy resources.')
param location string = resourceGroup().location

@description('Required. An Array of 1 or more IP Address Prefixes for the Virtual Network.')
param addressPrefixes array

@description('An array of subnets to be created within the virtual network. Each subnet can have its own configuration and associated Network Security Group (NSG).')
param subnets subnetType[] = [


  {
   name:'backend'
   addressPrefixes: ['10.0.0.0/27']
   networkSecurityGroup: {
     name: 'nsg-backend'
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
    {
    name: 'containers'
    addressPrefixes: ['10.0.2.0/23']
    delegation: 'Microsoft.App/environments'
    privateEndpointNetworkPolicies: 'Enabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
    networkSecurityGroup: {
      name: 'nsg-containers'
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
  {
    name: 'webserverfarm'
    addressPrefixes: ['10.0.4.0/27']
    delegation: 'Microsoft.Web/serverfarms'
    privateEndpointNetworkPolicies: 'Enabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
    networkSecurityGroup: {
      name: 'nsg-webserverfarm'
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
  {
    name: 'administration'
    addressPrefixes: ['10.0.0.32/27']
    networkSecurityGroup: {
      name: 'nsg-administration'
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
  {
    name: 'AzureBastionSubnet' // Required name for Azure Bastion
    addressPrefixes: ['10.0.0.64/26']
    networkSecurityGroup: {
      name: 'nsg-bastion'
      securityRules: [
        {
          name: 'AllowGatewayManager'
          properties: {
            access: 'Allow'
            direction: 'Inbound'
            priority: 2702
            protocol: '*'
            sourcePortRange: '*'
            destinationPortRange: '443'
            sourceAddressPrefix: 'GatewayManager'
            destinationAddressPrefix: '*'
          }
        }
        {
          name: 'AllowHttpsInBound'
          properties: {
            access: 'Allow'
            direction: 'Inbound'
            priority: 2703
            protocol: '*'
            sourcePortRange: '*'
            destinationPortRange: '443'
            sourceAddressPrefix: 'Internet'
            destinationAddressPrefix: '*'
          }
        }
        {
          name: 'AllowSshRdpOutbound'
          properties: {
            access: 'Allow'
            direction: 'Outbound'
            priority: 100
            protocol: '*'
            sourcePortRange: '*'
            destinationPortRanges: ['22', '3389']
            sourceAddressPrefix: '*'
            destinationAddressPrefix: 'VirtualNetwork'
          }
        }
        {
          name: 'AllowAzureCloudOutbound'
          properties: {
            access: 'Allow'
            direction: 'Outbound'
            priority: 110
            protocol: 'Tcp'
            sourcePortRange: '*'
            destinationPortRange: '443'
            sourceAddressPrefix: '*'
            destinationAddressPrefix: 'AzureCloud'
          }
        }
      ]
    }
  }
]

@description('Optional. Tags to be applied to the resources.')
param tags object = {}

@description('Optional. The resource ID of the Log Analytics Workspace to send diagnostic logs to.')
param logAnalyticsWorkspaceId string

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Required. Suffix for resource naming.')
param resourceSuffix string

// VM Size Notes:
// 1 B-series VMs (like Standard_B2ms) do not support accelerated networking.
// 2 Pick a VM size that does support accelerated networking (the usual jump-box candidates):
//     Standard_DS2_v2 (2 vCPU, 7 GiB RAM, Premium SSD) // The most broadly available (it’s a legacy SKU supported in virtually every region).
//     Standard_D2s_v3 (2 vCPU, 8 GiB RAM, Premium SSD) //  next most common
//     Standard_D2s_v4 (2 vCPU, 8 GiB RAM, Premium SSD)  // Newest, so fewer regions availabl


// Subnet Classless Inter-Doman Routing (CIDR)  Sizing Reference Table (Best Practices)
// | CIDR      | # of Addresses | # of /24s | Notes                                 |
// |-----------|---------------|-----------|----------------------------------------|
// | /24       | 256           | 1         | Smallest recommended for Azure subnets |
// | /23       | 512           | 2         | Good for 1-2 workloads per subnet      |
// | /22       | 1024          | 4         | Good for 2-4 workloads per subnet      |
// | /21       | 2048          | 8         |                                        |
// | /20       | 4096          | 16        | Used for default VNet in this solution |
// | /19       | 8192          | 32        |                                        |
// | /18       | 16384         | 64        |                                        |
// | /17       | 32768         | 128       |                                        |
// | /16       | 65536         | 256       |                                        |
// | /15       | 131072        | 512       |                                        |
// | /14       | 262144        | 1024      |                                        |
// | /13       | 524288        | 2048      |                                        |
// | /12       | 1048576       | 4096      |                                        |
// | /11       | 2097152       | 8192      |                                        |
// | /10       | 4194304       | 16384     |                                        |
// | /9        | 8388608       | 32768     |                                        |
// | /8        | 16777216      | 65536     |                                        |
//
// Best Practice Notes:
// - Use /24 as the minimum subnet size for Azure (smaller subnets are not supported for most services).
// - Plan for future growth: allocate larger address spaces (e.g., /20 or /21 for VNets) to allow for new subnets.
// - Avoid overlapping address spaces with on-premises or other VNets.
// - Use contiguous, non-overlapping ranges for subnets.
// - Document subnet usage and purpose in code comments.
// - For AVM modules, ensure only one delegation per subnet and leave delegations empty if not required.

// 1. Create NSGs for subnets 
// using AVM Network Security Group module
// https://github.com/Azure/bicep-registry-modules/tree/main/avm/res/network/network-security-group

@batchSize(1)
module nsgs 'br/public:avm/res/network/network-security-group:0.5.1' = [
  for (subnet, i) in subnets: if (!empty(subnet.?networkSecurityGroup)) {
    name: take('avm.res.network.network-security-group.${subnet.?networkSecurityGroup.name}.${resourceSuffix}', 64)
    params: {
      name: '${subnet.?networkSecurityGroup.name}-${resourceSuffix}'
      location: location
      securityRules: subnet.?networkSecurityGroup.securityRules
      tags: tags
      enableTelemetry: enableTelemetry
    }
  }
]

// 2. Create VNet and subnets, with subnets associated with corresponding NSGs
// using AVM Virtual Network module
// https://github.com/Azure/bicep-registry-modules/tree/main/avm/res/network/virtual-network

module virtualNetwork 'br/public:avm/res/network/virtual-network:0.7.0' = {
  name: take('avm.res.network.virtual-network.${name}', 64)
  params: {
    name: name
    location: location
    addressPrefixes: addressPrefixes
    subnets: [
      for (subnet, i) in subnets: {
        name: subnet.name
        addressPrefixes: subnet.?addressPrefixes
        networkSecurityGroupResourceId: !empty(subnet.?networkSecurityGroup) ? nsgs[i]!.outputs.resourceId : null
        privateEndpointNetworkPolicies: subnet.?privateEndpointNetworkPolicies
        privateLinkServiceNetworkPolicies: subnet.?privateLinkServiceNetworkPolicies
        delegation: subnet.?delegation
      }
    ]
    diagnosticSettings: [
      {
        name: 'vnetDiagnostics'
        workspaceResourceId: logAnalyticsWorkspaceId
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
            enabled: true
          }
        ]
        metricCategories: [
          {
            category: 'AllMetrics'
            enabled: true
          }
        ]
      }
    ]
    tags: tags
    enableTelemetry: enableTelemetry
  }
}

output name string = virtualNetwork.outputs.name
output resourceId string = virtualNetwork.outputs.resourceId

// combined output array that holds subnet details along with NSG information
output subnets subnetOutputType[] = [
  for (subnet, i) in subnets: {
    name: subnet.name
    resourceId: virtualNetwork.outputs.subnetResourceIds[i]
    nsgName: !empty(subnet.?networkSecurityGroup) ? subnet.?networkSecurityGroup.name : null
    nsgResourceId: !empty(subnet.?networkSecurityGroup) ? nsgs[i]!.outputs.resourceId : null
  }
]

// Dynamic outputs for individual subnets for backward compatibility
output backendSubnetResourceId string = contains(map(subnets, subnet => subnet.name), 'backend') ? virtualNetwork.outputs.subnetResourceIds[indexOf(map(subnets, subnet => subnet.name), 'backend')] : ''
output containerSubnetResourceId string = contains(map(subnets, subnet => subnet.name), 'containers') ? virtualNetwork.outputs.subnetResourceIds[indexOf(map(subnets, subnet => subnet.name), 'containers')] : ''
output administrationSubnetResourceId string = contains(map(subnets, subnet => subnet.name), 'administration') ? virtualNetwork.outputs.subnetResourceIds[indexOf(map(subnets, subnet => subnet.name), 'administration')] : ''
output webserverfarmSubnetResourceId string = contains(map(subnets, subnet => subnet.name), 'webserverfarm') ? virtualNetwork.outputs.subnetResourceIds[indexOf(map(subnets, subnet => subnet.name), 'webserverfarm')] : ''
output bastionSubnetResourceId string = contains(map(subnets, subnet => subnet.name), 'AzureBastionSubnet') ? virtualNetwork.outputs.subnetResourceIds[indexOf(map(subnets, subnet => subnet.name), 'AzureBastionSubnet')] : ''

@export()
@description('Custom type definition for subnet resource information as output')
type subnetOutputType = {
  @description('The name of the subnet.')
  name: string

  @description('The resource ID of the subnet.')
  resourceId: string

  @description('The name of the associated network security group, if any.')
  nsgName: string?

  @description('The resource ID of the associated network security group, if any.')
  nsgResourceId: string?
}

@export()
@description('Custom type definition for subnet configuration')
type subnetType = {
  @description('Required. The Name of the subnet resource.')
  name: string

  @description('Required. Prefixes for the subnet.')  // Required to ensure at least one prefix is provided
  addressPrefixes: string[]   

  @description('Optional. The delegation to enable on the subnet.')
  delegation: string?

  @description('Optional. enable or disable apply network policies on private endpoint in the subnet.')
  privateEndpointNetworkPolicies: ('Disabled' | 'Enabled' | 'NetworkSecurityGroupEnabled' | 'RouteTableEnabled')?

  @description('Optional. Enable or disable apply network policies on private link service in the subnet.')
  privateLinkServiceNetworkPolicies: ('Disabled' | 'Enabled')?

  @description('Optional. Network Security Group configuration for the subnet.')
  networkSecurityGroup: networkSecurityGroupType?

  @description('Optional. The resource ID of the route table to assign to the subnet.')
  routeTableResourceId: string?

  @description('Optional. An array of service endpoint policies.')
  serviceEndpointPolicies: object[]?

  @description('Optional. The service endpoints to enable on the subnet.')
  serviceEndpoints: string[]?

  @description('Optional. Set this property to false to disable default outbound connectivity for all VMs in the subnet. This property can only be set at the time of subnet creation and cannot be updated for an existing subnet.')
  defaultOutboundAccess: bool?
}

@export()
@description('Custom type definition for network security group configuration')
type networkSecurityGroupType = {
  @description('Required. The name of the network security group.')
  name: string

  @description('Required. The security rules for the network security group.')
  securityRules: object[]
}

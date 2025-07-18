extension graphV1
//extension graphBeta

metadata name = '<Add module name>'
metadata description = '<Add description>'

@description('Required. The prefix to add in the default names given to all deployed Azure resources.')
@maxLength(19)
param solutionPrefix string

@description('Optional. Location for all Resources.')
param solutionLocation string = resourceGroup().location

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool

@description('Optional. Enable/Disable usage telemetry for module.')
param enableNetworkSecurity bool

@description('Optional. The tags to apply to all deployed Azure resources.')
param tags object = {
  app: solutionPrefix
  location: solutionLocation
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Log Analytics Workspace resource.')
param logAnalyticsWorkspaceConfiguration logAnalyticsWorkspaceConfigurationType = {
  enabled: true
  name: '${solutionPrefix}laws'
  location: solutionLocation
  sku: 'PerGB2018'
  tags: tags
  dataRetentionInDays: 30
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Application Insights resource.')
param applicationInsightsConfiguration applicationInsightsConfigurationType = {
  enabled: true
  name: '${solutionPrefix}appi'
  location: solutionLocation
  tags: tags
  retentionInDays: 30
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Managed Identity resource.')
param userAssignedManagedIdentityConfiguration userAssignedManagedIdentityType = {
  enabled: true
  name: '${solutionPrefix}mgid'
  location: solutionLocation
  tags: tags
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Network Security Group resource for the backend subnet.')
param networkSecurityGroupBackendConfiguration networkSecurityGroupConfigurationType = {
  enabled: enableNetworkSecurity
  name: '${solutionPrefix}nsgr-backend'
  location: solutionLocation
  tags: tags
  securityRules: [
    // {
    //   name: 'DenySshRdpOutbound' //Azure Bastion
    //   properties: {
    //     priority: 200
    //     access: 'Deny'
    //     protocol: '*'
    //     direction: 'Outbound'
    //     sourceAddressPrefix: 'VirtualNetwork'
    //     sourcePortRange: '*'
    //     destinationAddressPrefix: '*'
    //     destinationPortRanges: [
    //       '3389'
    //       '22'
    //     ]
    //   }
    // }
  ]
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Network Security Group resource for the containers subnet.')
param networkSecurityGroupContainersConfiguration networkSecurityGroupConfigurationType = {
  enabled: enableNetworkSecurity
  name: '${solutionPrefix}nsgr-containers'
  location: solutionLocation
  tags: tags
  securityRules: [
    // {
    //   name: 'DenySshRdpOutbound' //Azure Bastion
    //   properties: {
    //     priority: 200
    //     access: 'Deny'
    //     protocol: '*'
    //     direction: 'Outbound'
    //     sourceAddressPrefix: 'VirtualNetwork'
    //     sourcePortRange: '*'
    //     destinationAddressPrefix: '*'
    //     destinationPortRanges: [
    //       '3389'
    //       '22'
    //     ]
    //   }
    // }
  ]
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Network Security Group resource for the Bastion subnet.')
param networkSecurityGroupBastionConfiguration networkSecurityGroupConfigurationType = {
  enabled: enableNetworkSecurity
  name: '${solutionPrefix}nsgr-bastion'
  location: solutionLocation
  tags: tags
  securityRules: [
    // {
    //   name: 'DenySshRdpOutbound' //Azure Bastion
    //   properties: {
    //     priority: 200
    //     access: 'Deny'
    //     protocol: '*'
    //     direction: 'Outbound'
    //     sourceAddressPrefix: 'VirtualNetwork'
    //     sourcePortRange: '*'
    //     destinationAddressPrefix: '*'
    //     destinationPortRanges: [
    //       '3389'
    //       '22'
    //     ]
    //   }
    // }
  ]
}

@description('Optional. The configuration to apply for the Multi-Agent Custom Automation Engine Network Security Group resource for the administration subnet.')
param networkSecurityGroupAdministrationConfiguration networkSecurityGroupConfigurationType = {
  enabled: enableNetworkSecurity
  name: '${solutionPrefix}nsgr-administration'
  location: solutionLocation
  tags: tags
  securityRules: [
    // {
    //   name: 'DenySshRdpOutbound' //Azure Bastion
    //   properties: {
    //     priority: 200
    //     access: 'Deny'
    //     protocol: '*'
    //     direction: 'Outbound
    //     sourceAddressPrefix: 'VirtualNetwork'
    //     sourcePortRange: '*'
    //     destinationAddressPrefix: '*'
    //     destinationPortRanges: [
    //       '3389'
    //       '22'
    //     ]
    //   }
    // }
  ]
}

@description('Optional. Configuration for the virtual machine.')
param virtualMachineConfiguration virtualMachineConfigurationType = {
  enabled: enableNetworkSecurity
  adminUsername: 'adminuser'
  adminPassword: guid(solutionPrefix, subscription().subscriptionId)
}
var virtualMachineEnabled = virtualMachineConfiguration.?enabled ?? true

@description('Optional. Configuration for the virtual machine.')
param virtualNetworkConfiguration virtualNetworkConfigurationType = {
  enabled: enableNetworkSecurity
}
var virtualNetworkEnabled = virtualNetworkConfiguration.?enabled ?? true

@description('Optional. The configuration of the Entra ID Application used to authenticate the website.')
param entraIdApplicationConfiguration entraIdApplicationConfigurationType = {
  enabled: false
}

@description('Optional. The UTC time deployment.')
param deploymentTime string = utcNow()

//
// Add your parameters here
//

// ============== //
// Resources      //
// ============== //

/* #disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2024-03-01' = if (enableTelemetry) {
  name: '46d3xbcp.[[REPLACE WITH TELEMETRY IDENTIFIER]].${replace('-..--..-', '.', '-')}.${substring(uniqueString(deployment().name, location), 0, 4)}'
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        telemetry: {
          type: 'String'
          value: 'For more information, see https://aka.ms/avm/TelemetryInfo'
        }
      }
    }
  }
} */

// ========== Log Analytics Workspace ========== //
// Log Analytics configuration defaults
var logAnalyticsWorkspaceEnabled = logAnalyticsWorkspaceConfiguration.?enabled ?? true
var logAnalyticsWorkspaceResourceName = logAnalyticsWorkspaceConfiguration.?name ?? '${solutionPrefix}-laws'
var logAnalyticsWorkspaceTags = logAnalyticsWorkspaceConfiguration.?tags ?? tags
var logAnalyticsWorkspaceLocation = logAnalyticsWorkspaceConfiguration.?location ?? solutionLocation
var logAnalyticsWorkspaceSkuName = logAnalyticsWorkspaceConfiguration.?sku ?? 'PerGB2018'
var logAnalyticsWorkspaceDataRetentionInDays = logAnalyticsWorkspaceConfiguration.?dataRetentionInDays ?? 30
module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.11.2' = if (logAnalyticsWorkspaceEnabled) {
  name: take('operational-insights.workspace.${logAnalyticsWorkspaceResourceName}', 64)
  params: {
    name: logAnalyticsWorkspaceResourceName
    tags: logAnalyticsWorkspaceTags
    location: logAnalyticsWorkspaceLocation
    enableTelemetry: enableTelemetry
    skuName: logAnalyticsWorkspaceSkuName
    dataRetention: logAnalyticsWorkspaceDataRetentionInDays
    diagnosticSettings: [{ useThisWorkspace: true }]
  }
}

// ========== Application Insights ========== //
// Application Insights configuration defaults
var applicationInsightsEnabled = applicationInsightsConfiguration.?enabled ?? true
var applicationInsightsResourceName = applicationInsightsConfiguration.?name ?? '${solutionPrefix}appi'
var applicationInsightsTags = applicationInsightsConfiguration.?tags ?? tags
var applicationInsightsLocation = applicationInsightsConfiguration.?location ?? solutionLocation
var applicationInsightsRetentionInDays = applicationInsightsConfiguration.?retentionInDays ?? 365
module applicationInsights 'br/public:avm/res/insights/component:0.6.0' = if (applicationInsightsEnabled) {
  name: take('insights.component.${applicationInsightsResourceName}', 64)
  params: {
    name: applicationInsightsResourceName
    workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
    location: applicationInsightsLocation
    enableTelemetry: enableTelemetry
    tags: applicationInsightsTags
    retentionInDays: applicationInsightsRetentionInDays
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    kind: 'web'
    disableIpMasking: false
    flowType: 'Bluefield'
  }
}

// ========== User assigned identity Web App ========== //
var userAssignedManagedIdentityEnabled = userAssignedManagedIdentityConfiguration.?enabled ?? true
var userAssignedManagedIdentityResourceName = userAssignedManagedIdentityConfiguration.?name ?? '${solutionPrefix}uaid'
var userAssignedManagedIdentityTags = userAssignedManagedIdentityConfiguration.?tags ?? tags
var userAssignedManagedIdentityLocation = userAssignedManagedIdentityConfiguration.?location ?? solutionLocation
module userAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = if (userAssignedManagedIdentityEnabled) {
  name: take('managed-identity.user-assigned-identity.${userAssignedManagedIdentityResourceName}', 64)
  params: {
    name: userAssignedManagedIdentityResourceName
    tags: userAssignedManagedIdentityTags
    location: userAssignedManagedIdentityLocation
    enableTelemetry: enableTelemetry
  }
}

// ========== Network Security Groups ========== //
var networkSecurityGroupBackendEnabled = networkSecurityGroupBackendConfiguration.?enabled ?? true
var networkSecurityGroupBackendResourceName = networkSecurityGroupBackendConfiguration.?name ?? '${solutionPrefix}nsgr-backend'
var networkSecurityGroupBackendTags = networkSecurityGroupBackendConfiguration.?tags ?? tags
var networkSecurityGroupBackendLocation = networkSecurityGroupBackendConfiguration.?location ?? solutionLocation
var networkSecurityGroupBackendSecurityRules = networkSecurityGroupBackendConfiguration.?securityRules ?? [
  // {
  //   name: 'DenySshRdpOutbound' //Azure Bastion
  //   properties: {
  //     priority: 200
  //     access: 'Deny'
  //     protocol: '*'
  //     direction: 'Outbound'
  //     sourceAddressPrefix: 'VirtualNetwork'
  //     sourcePortRange: '*'
  //     destinationAddressPrefix: '*'
  //     destinationPortRanges: [
  //       '3389'
  //       '22'
  //     ]
  //   }
  // }
]
module networkSecurityGroupBackend 'br/public:avm/res/network/network-security-group:0.5.1' = if (virtualNetworkEnabled && networkSecurityGroupBackendEnabled) {
  name: take('network.network-security-group.${networkSecurityGroupBackendResourceName}', 64)
  params: {
    name: networkSecurityGroupBackendResourceName
    location: networkSecurityGroupBackendLocation
    tags: networkSecurityGroupBackendTags
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    securityRules: networkSecurityGroupBackendSecurityRules
  }
}

var networkSecurityGroupContainersEnabled = networkSecurityGroupContainersConfiguration.?enabled ?? true
var networkSecurityGroupContainersResourceName = networkSecurityGroupContainersConfiguration.?name ?? '${solutionPrefix}nsgr-containers'
var networkSecurityGroupContainersTags = networkSecurityGroupContainersConfiguration.?tags ?? tags
var networkSecurityGroupContainersLocation = networkSecurityGroupContainersConfiguration.?location ?? solutionLocation
var networkSecurityGroupContainersSecurityRules = networkSecurityGroupContainersConfiguration.?securityRules ?? [
  // {
  //   name: 'DenySshRdpOutbound' //Azure Bastion
  //   properties: {
  //     priority: 200
  //     access: 'Deny'
  //     protocol: '*'
  //     direction: 'Outbound'
  //     sourceAddressPrefix: 'VirtualNetwork'
  //     sourcePortRange: '*'
  //     destinationAddressPrefix: '*'
  //     destinationPortRanges: [
  //       '3389'
  //       '22'
  //     ]
  //   }
  // }
]
module networkSecurityGroupContainers 'br/public:avm/res/network/network-security-group:0.5.1' = if (virtualNetworkEnabled && networkSecurityGroupContainersEnabled) {
  name: take('network.network-security-group.${networkSecurityGroupContainersResourceName}', 64)
  params: {
    name: networkSecurityGroupContainersResourceName
    location: networkSecurityGroupContainersLocation
    tags: networkSecurityGroupContainersTags
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    securityRules: networkSecurityGroupContainersSecurityRules
  }
}

var networkSecurityGroupBastionEnabled = networkSecurityGroupBastionConfiguration.?enabled ?? true
var networkSecurityGroupBastionResourceName = networkSecurityGroupBastionConfiguration.?name ?? '${solutionPrefix}nsgr-bastion'
var networkSecurityGroupBastionTags = networkSecurityGroupBastionConfiguration.?tags ?? tags
var networkSecurityGroupBastionLocation = networkSecurityGroupBastionConfiguration.?location ?? solutionLocation
var networkSecurityGroupBastionSecurityRules = networkSecurityGroupBastionConfiguration.?securityRules ?? [
  // {
  //   name: 'DenySshRdpOutbound' //Azure Bastion
  //   properties: {
  //     priority: 200
  //     access: 'Deny'
  //     protocol: '*'
  //     direction: 'Outbound'
  //     sourceAddressPrefix: 'VirtualNetwork'
  //     sourcePortRange: '*'
  //     destinationAddressPrefix: '*'
  //     destinationPortRanges: [
  //       '3389'
  //       '22'
  //     ]
  //   }
  // }
]
module networkSecurityGroupBastion 'br/public:avm/res/network/network-security-group:0.5.1' = if (virtualNetworkEnabled && networkSecurityGroupBastionEnabled) {
  name: take('network.network-security-group.${networkSecurityGroupBastionResourceName}', 64)
  params: {
    name: networkSecurityGroupBastionResourceName
    location: networkSecurityGroupBastionLocation
    tags: networkSecurityGroupBastionTags
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    securityRules: networkSecurityGroupBastionSecurityRules
  }
}

var networkSecurityGroupAdministrationEnabled = networkSecurityGroupAdministrationConfiguration.?enabled ?? true
var networkSecurityGroupAdministrationResourceName = networkSecurityGroupAdministrationConfiguration.?name ?? '${solutionPrefix}nsgr-administration'
var networkSecurityGroupAdministrationTags = networkSecurityGroupAdministrationConfiguration.?tags ?? tags
var networkSecurityGroupAdministrationLocation = networkSecurityGroupAdministrationConfiguration.?location ?? solutionLocation
var networkSecurityGroupAdministrationSecurityRules = networkSecurityGroupAdministrationConfiguration.?securityRules ?? [
  // {
  //   name: 'DenySshRdpOutbound' //Azure Bastion
  //   properties: {
  //     priority: 200
  //     access: 'Deny'
  //     protocol: '*'
  //     direction: 'Outbound'
  //     sourceAddressPrefix: 'VirtualNetwork'
  //     sourcePortRange: '*'
  //     destinationAddressPrefix: '*'
  //     destinationPortRanges: [
  //       '3389'
  //       '22'
  //     ]
  //   }
  // }
]
module networkSecurityGroupAdministration 'br/public:avm/res/network/network-security-group:0.5.1' = if (virtualNetworkEnabled && networkSecurityGroupAdministrationEnabled) {
  name: take('network.network-security-group.${networkSecurityGroupAdministrationResourceName}', 64)
  params: {
    name: networkSecurityGroupAdministrationResourceName
    location: networkSecurityGroupAdministrationLocation
    tags: networkSecurityGroupAdministrationTags
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    securityRules: networkSecurityGroupAdministrationSecurityRules
  }
}

// ========== Virtual Network ========== //

module virtualNetwork 'br/public:avm/res/network/virtual-network:0.6.1' = if (virtualNetworkEnabled) {
  name: 'network-virtual-network'
  params: {
    name: '${solutionPrefix}vnet'
    location: solutionLocation
    tags: tags
    enableTelemetry: enableTelemetry
    addressPrefixes: ['10.0.0.0/8']
    subnets: [
      // The default subnet **must** be the first in the subnets array
      {
        name: 'backend'
        addressPrefix: '10.0.0.0/27'
        //defaultOutboundAccess: false TODO: check this configuration for a more restricted outbound access
        networkSecurityGroupResourceId: networkSecurityGroupBackend.outputs.resourceId
      }
      {
        name: 'administration'
        addressPrefix: '10.0.0.32/27'
        networkSecurityGroupResourceId: networkSecurityGroupAdministration.outputs.resourceId
        //defaultOutboundAccess: false TODO: check this configuration for a more restricted outbound access
        //natGatewayResourceId: natGateway.outputs.resourceId
      }
      {
        // For Azure Bastion resources deployed on or after November 2, 2021, the minimum AzureBastionSubnet size is /26 or larger (/25, /24, etc.).
        // https://learn.microsoft.com/en-us/azure/bastion/configuration-settings#subnet
        name: 'AzureBastionSubnet' //This exact name is required for Azure Bastion
        addressPrefix: '10.0.0.64/26'
        networkSecurityGroupResourceId: networkSecurityGroupBastion.outputs.resourceId
      }
      {
        // If you use your own VNet, you need to provide a subnet that is dedicated exclusively to the Container App environment you deploy. This subnet isn't available to other services
        // https://learn.microsoft.com/en-us/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli#custom-vnet-configuration
        name: 'containers'
        addressPrefix: '10.0.1.0/23' //subnet of size /23 is required for container app
        //defaultOutboundAccess: false TODO: check this configuration for a more restricted outbound access
        delegation: 'Microsoft.App/environments'
        networkSecurityGroupResourceId: networkSecurityGroupContainers.outputs.resourceId
        privateEndpointNetworkPolicies: 'Disabled'
        privateLinkServiceNetworkPolicies: 'Enabled'
      }
    ]
  }
}

// ========== Bastion host ========== //

module bastionHost 'br/public:avm/res/network/bastion-host:0.6.1' = if (virtualNetworkEnabled) {
  name: 'network-dns-zone-bastion-host'
  params: {
    name: '${solutionPrefix}bstn'
    location: solutionLocation
    skuName: 'Standard'
    enableTelemetry: enableTelemetry
    tags: tags
    virtualNetworkResourceId: virtualNetwork.outputs.resourceId
    publicIPAddressObject: {
      name: '${solutionPrefix}pbipbstn'
    }
    disableCopyPaste: false
    enableFileCopy: false
    enableIpConnect: true
    //enableKerberos: bastionConfiguration.?enableKerberos
    enableShareableLink: true
    //scaleUnits: bastionConfiguration.?scaleUnits
  }
}

// ========== Virtual machine ========== //

module virtualMachine 'br/public:avm/res/compute/virtual-machine:0.13.0' = if (virtualNetworkEnabled && virtualMachineEnabled) {
  name: 'compute-virtual-machine'
  params: {
    name: '${solutionPrefix}vmws'
    computerName: take('${solutionPrefix}vmws', 15)
    location: solutionLocation
    tags: tags
    enableTelemetry: enableTelemetry
    adminUsername: virtualMachineConfiguration.?adminUsername!
    adminPassword: virtualMachineConfiguration.?adminPassword!
    nicConfigurations: [
      {
        //networkSecurityGroupResourceId: virtualMachineConfiguration.?nicConfigurationConfiguration.networkSecurityGroupResourceId
        nicSuffix: 'nic01'
        diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
        ipConfigurations: [
          {
            name: 'ipconfig01'
            subnetResourceId: virtualNetwork.outputs.subnetResourceIds[1]
            diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
          }
        ]
      }
    ]
    imageReference: {
      publisher: 'microsoft-dsvm'
      offer: 'dsvm-win-2022'
      sku: 'winserver-2022'
      version: 'latest'
    }
    osDisk: {
      createOption: 'FromImage'
      managedDisk: {
        storageAccountType: 'Premium_ZRS'
      }
      diskSizeGB: 128
      caching: 'ReadWrite'
    }
    //patchMode: virtualMachineConfiguration.?patchMode
    osType: 'Windows'
    encryptionAtHost: false //The property 'securityProfile.encryptionAtHost' is not valid because the 'Microsoft.Compute/EncryptionAtHost' feature is not enabled for this subscription.
    vmSize: 'Standard_D2s_v3'
    zone: 0
    extensionAadJoinConfig: {
      enabled: true
      typeHandlerVersion: '1.0'
    }
    // extensionMonitoringAgentConfig: {
    //   enabled: true
    // }
    //    maintenanceConfigurationResourceId: virtualMachineConfiguration.?maintenanceConfigurationResourceId
  }
}
// ========== DNS Zone for AI Foundry: Open AI ========== //
var openAiSubResource = 'account'
var openAiPrivateDnsZones = {
  'privatelink.cognitiveservices.azure.com': openAiSubResource
  'privatelink.openai.azure.com': openAiSubResource
  'privatelink.services.ai.azure.com': openAiSubResource
}

module privateDnsZonesAiServices 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
  for zone in objectKeys(openAiPrivateDnsZones): if (virtualNetworkEnabled) {
    name: 'network-dns-zone-${uniqueString(deployment().name, zone)}'
    params: {
      name: zone
      tags: tags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [{ virtualNetworkResourceId: virtualNetwork.outputs.resourceId }]
    }
  }
]

// ========== AI Foundry: AI Services ==========
// NOTE: Required version 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' not available in AVM
var aiFoundryAiServicesModelDeployment = {
  format: 'OpenAI'
  name: 'gpt-4o'
  version: '2024-08-06'
  sku: {
    name: 'GlobalStandard'
    capacity: 50
  }
  raiPolicyName: 'Microsoft.Default'
}

var aiFoundryAiServicesAccountName = '${solutionPrefix}aifdaisv'
module aiFoundryAiServices 'br/public:avm/res/cognitive-services/account:0.10.2' = {
  name: 'cognitive-services-account'
  params: {
    name: aiFoundryAiServicesAccountName
    tags: tags
    location: solutionLocation
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    sku: 'S0'
    kind: 'AIServices'
    disableLocalAuth: false //Should be set to true for WAF aligned configuration
    customSubDomainName: aiFoundryAiServicesAccountName
    apiProperties: {
      //staticsEnabled: false
    }
    //publicNetworkAccess: virtualNetworkEnabled ? 'Disabled' : 'Enabled'
    publicNetworkAccess: 'Enabled' //TODO: connection via private endpoint is not working from containers network. Change this when fixed
    privateEndpoints: virtualNetworkEnabled
      ? ([
          {
            subnetResourceId: virtualNetwork.outputs.subnetResourceIds[0]
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: map(objectKeys(openAiPrivateDnsZones), zone => {
                name: replace(zone, '.', '-')
                privateDnsZoneResourceId: resourceId('Microsoft.Network/privateDnsZones', zone)
              })
            }
          }
        ])
      : []
    roleAssignments: [
      // {
      //   principalId: userAssignedIdentity.outputs.principalId
      //   principalType: 'ServicePrincipal'
      //   roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
      // }
      {
        principalId: containerApp.outputs.?systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
      }
    ]
    deployments: [
      {
        name: aiFoundryAiServicesModelDeployment.name
        model: {
          format: aiFoundryAiServicesModelDeployment.format
          name: aiFoundryAiServicesModelDeployment.name
          version: aiFoundryAiServicesModelDeployment.version
        }
        raiPolicyName: aiFoundryAiServicesModelDeployment.raiPolicyName
        sku: {
          name: aiFoundryAiServicesModelDeployment.sku.name
          capacity: aiFoundryAiServicesModelDeployment.sku.capacity
        }
      }
    ]
  }
}

// AI Foundry: storage account

var storageAccountPrivateDnsZones = {
  'privatelink.blob.${environment().suffixes.storage}': 'blob'
  'privatelink.file.${environment().suffixes.storage}': 'file'
}

module privateDnsZonesAiFoundryStorageAccount 'br/public:avm/res/network/private-dns-zone:0.3.1' = [
  for zone in objectKeys(storageAccountPrivateDnsZones): if (virtualNetworkEnabled) {
    name: 'network-dns-zone-aifd-stac-${zone}'
    params: {
      name: zone
      tags: tags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [
        {
          virtualNetworkResourceId: virtualNetwork.outputs.resourceId
        }
      ]
    }
  }
]

var aiFoundryStorageAccountName = '${solutionPrefix}aifdstrg'
module aiFoundryStorageAccount 'br/public:avm/res/storage/storage-account:0.18.2' = {
  name: 'storage-storage-account'
  dependsOn: [
    privateDnsZonesAiFoundryStorageAccount
  ]
  params: {
    name: aiFoundryStorageAccountName
    location: solutionLocation
    tags: tags
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    blobServices: {
      deleteRetentionPolicyEnabled: false
      containerDeleteRetentionPolicyDays: 7
      containerDeleteRetentionPolicyEnabled: false
      diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    }
    publicNetworkAccess: virtualNetworkEnabled ? 'Disabled' : 'Enabled'
    allowBlobPublicAccess: virtualNetworkEnabled ? false : true
    privateEndpoints: virtualNetworkEnabled
      ? map(items(storageAccountPrivateDnsZones), zone => {
          name: 'pep-${zone.value}-${aiFoundryStorageAccountName}'
          customNetworkInterfaceName: 'nic-${zone.value}-${aiFoundryStorageAccountName}'
          service: zone.value
          subnetResourceId: virtualNetwork.outputs.subnetResourceIds[0] ?? ''
          privateDnsZoneResourceIds: [resourceId('Microsoft.Network/privateDnsZones', zone.key)]
        })
      : null
    roleAssignments: [
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// AI Foundry: AI Hub
var mlTargetSubResource = 'amlworkspace'
var mlPrivateDnsZones = {
  'privatelink.api.azureml.ms': mlTargetSubResource
  'privatelink.notebooks.azure.net': mlTargetSubResource
}
module privateDnsZonesAiFoundryWorkspaceHub 'br/public:avm/res/network/private-dns-zone:0.3.1' = [
  for zone in objectKeys(mlPrivateDnsZones): if (virtualNetworkEnabled) {
    name: 'network-dns-zone-${zone}'
    params: {
      name: zone
      enableTelemetry: enableTelemetry
      tags: tags
      virtualNetworkLinks: [
        {
          virtualNetworkResourceId: virtualNetwork.outputs.resourceId
        }
      ]
    }
  }
]
var aiFoundryAiHubName = '${solutionPrefix}aifdaihb'
module aiFoundryAiHub 'modules/ai-hub.bicep' = {
  name: 'modules-ai-hub'
  dependsOn: [
    privateDnsZonesAiFoundryWorkspaceHub
  ]
  params: {
    name: aiFoundryAiHubName
    location: solutionLocation
    tags: tags
    aiFoundryAiServicesName: aiFoundryAiServices.outputs.name
    applicationInsightsResourceId: applicationInsights.outputs.resourceId
    enableTelemetry: enableTelemetry
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
    storageAccountResourceId: aiFoundryStorageAccount.outputs.resourceId
    virtualNetworkEnabled: virtualNetworkEnabled
    privateEndpoints: virtualNetworkEnabled
      ? [
          {
            name: 'pep-${mlTargetSubResource}-${aiFoundryAiHubName}'
            customNetworkInterfaceName: 'nic-${mlTargetSubResource}-${aiFoundryAiHubName}'
            service: mlTargetSubResource
            subnetResourceId: virtualNetworkEnabled ? virtualNetwork.?outputs.?subnetResourceIds[0] : null
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: map(objectKeys(mlPrivateDnsZones), zone => {
                name: replace(zone, '.', '-')
                privateDnsZoneResourceId: resourceId('Microsoft.Network/privateDnsZones', zone)
              })
            }
          }
        ]
      : []
  }
}

// AI Foundry: AI Project
var aiFoundryAiProjectName = '${solutionPrefix}aifdaipj'

module aiFoundryAiProject 'br/public:avm/res/machine-learning-services/workspace:0.12.0' = {
  name: 'machine-learning-services-workspace-project'
  params: {
    name: aiFoundryAiProjectName
    location: solutionLocation
    tags: tags
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    sku: 'Basic'
    kind: 'Project'
    hubResourceId: aiFoundryAiHub.outputs.resourceId
    roleAssignments: [
      {
        principalId: containerApp.outputs.?systemAssignedMIPrincipalId!
        // Assigning the role with the role name instead of the role ID freezes the deployment at this point
        roleDefinitionIdOrName: '64702f94-c441-49e6-a78b-ef80e0188fee' //'Azure AI Developer'
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// ========== DNS Zone for Cosmos DB ========== //
module privateDnsZonesCosmosDb 'br/public:avm/res/network/private-dns-zone:0.7.0' = if (virtualNetworkEnabled) {
  name: 'network-dns-zone-cosmos-db'
  params: {
    name: 'privatelink.documents.azure.com'
    enableTelemetry: enableTelemetry
    virtualNetworkLinks: [{ virtualNetworkResourceId: virtualNetwork.outputs.resourceId }]
    tags: tags
  }
}

// ========== Cosmos DB ========== //
var cosmosDbName = '${solutionPrefix}csdb'
var cosmosDbDatabaseName = 'autogen'
var cosmosDbDatabaseMemoryContainerName = 'memory'
module cosmosDb 'br/public:avm/res/document-db/database-account:0.12.0' = {
  name: 'cosmos-db'
  params: {
    // Required parameters
    name: cosmosDbName
    tags: tags
    location: solutionLocation
    enableTelemetry: enableTelemetry
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    databaseAccountOfferType: 'Standard'
    enableFreeTier: false
    networkRestrictions: {
      networkAclBypass: 'None'
      publicNetworkAccess: virtualNetworkEnabled ? 'Disabled' : 'Enabled'
    }
    privateEndpoints: virtualNetworkEnabled
      ? [
          {
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [{ privateDnsZoneResourceId: privateDnsZonesCosmosDb.outputs.resourceId }]
            }
            service: 'Sql'
            subnetResourceId: virtualNetwork.outputs.subnetResourceIds[0]
          }
        ]
      : []
    sqlDatabases: [
      {
        name: cosmosDbDatabaseName
        containers: [
          {
            name: cosmosDbDatabaseMemoryContainerName
            paths: [
              '/session_id'
            ]
            kind: 'Hash'
            version: 2
          }
        ]
      }
    ]
    locations: [
      {
        locationName: solutionLocation
        failoverPriority: 0
      }
    ]
    capabilitiesToAdd: [
      'EnableServerless'
    ]
    sqlRoleAssignmentsPrincipalIds: [
      //userAssignedIdentity.outputs.principalId
      containerApp.outputs.?systemAssignedMIPrincipalId
    ]
    sqlRoleDefinitions: [
      {
        // Replace this with built-in role definition Cosmos DB Built-in Data Contributor: https://docs.azure.cn/en-us/cosmos-db/nosql/security/reference-data-plane-roles#cosmos-db-built-in-data-contributor
        roleType: 'CustomRole'
        roleName: 'Cosmos DB SQL Data Contributor'
        name: 'cosmos-db-sql-data-contributor'
        dataAction: [
          'Microsoft.DocumentDB/databaseAccounts/readMetadata'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*'
        ]
      }
    ]
  }
}

// ========== Backend Container App Environment ========== //

module containerAppEnvironment 'modules/container-app-environment.bicep' = {
  name: 'modules-container-app-environment'
  params: {
    name: '${solutionPrefix}cenv'
    tags: tags
    location: solutionLocation
    logAnalyticsResourceName: logAnalyticsWorkspace.outputs.name
    publicNetworkAccess: 'Enabled'
    zoneRedundant: virtualNetworkEnabled ? true : false
    aspireDashboardEnabled: !virtualNetworkEnabled
    vnetConfiguration: virtualNetworkEnabled
      ? {
          internal: false
          infrastructureSubnetId: virtualNetwork.?outputs.?subnetResourceIds[2] ?? ''
        }
      : {}
  }
}

// module containerAppEnvironment 'br/public:avm/res/app/managed-environment:0.11.0' = {
//   name: 'container-app-environment'
//   params: {
//     name: '${solutionPrefix}cenv'
//     location: solutionLocation
//     tags: tags
//     enableTelemetry: enableTelemetry
//     //daprAIConnectionString: applicationInsights.outputs.connectionString //Troubleshoot: ContainerAppsConfiguration.DaprAIConnectionString is invalid.  DaprAIConnectionString can not be set when AppInsightsConfiguration has been set, please set DaprAIConnectionString to null. (Code:InvalidRequestParameterWithDetails
//     appLogsConfiguration: {
//       destination: 'log-analytics'
//       logAnalyticsConfiguration: {
//         customerId: logAnalyticsWorkspace.outputs.logAnalyticsWorkspaceId
//         sharedKey: listKeys(
//           '${resourceGroup().id}/providers/Microsoft.OperationalInsights/workspaces/${logAnalyticsWorkspaceName}',
//           '2023-09-01'
//         ).primarySharedKey
//       }
//     }
//     appInsightsConnectionString: applicationInsights.outputs.connectionString
//     publicNetworkAccess: virtualNetworkEnabled ? 'Disabled' : 'Enabled' //TODO: use Azure Front Door WAF or Application Gateway WAF instead
//     zoneRedundant: true //TODO: make it zone redundant for waf aligned
//     infrastructureSubnetResourceId: virtualNetworkEnabled
//       ? virtualNetwork.outputs.subnetResourceIds[1]
//       : null
//     internal: false
//   }
// }

// ========== Backend Container App Service ========== //
module containerApp 'br/public:avm/res/app/container-app:0.14.2' = {
  name: 'container-app'
  params: {
    name: '${solutionPrefix}capp'
    tags: tags
    location: solutionLocation
    enableTelemetry: enableTelemetry
    //environmentResourceId: containerAppEnvironment.outputs.resourceId
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    managedIdentities: {
      systemAssigned: true //Replace with user assigned identity
      userAssignedResourceIds: [userAssignedIdentity.outputs.resourceId]
    }
    ingressTargetPort: 8000
    ingressExternal: true
    activeRevisionsMode: 'Single'
    corsPolicy: {
      allowedOrigins: [
        'https://${webSiteName}.azurewebsites.net'
        'http://${webSiteName}.azurewebsites.net'
      ]
    }
    scaleSettings: {
      //TODO: Make maxReplicas and minReplicas parameterized
      maxReplicas: 1
      minReplicas: 1
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
        //TODO: Make image parameterized for the registry name and the appversion
        image: 'biabcontainerreg.azurecr.io/macaebackend:fnd01'
        resources: {
          //TODO: Make cpu and memory parameterized
          cpu: '2.0'
          memory: '4.0Gi'
        }
        env: [
          {
            name: 'COSMOSDB_ENDPOINT'
            value: 'https://${cosmosDbName}.documents.azure.com:443/'
          }
          {
            name: 'COSMOSDB_DATABASE'
            value: cosmosDbDatabaseName
          }
          {
            name: 'COSMOSDB_CONTAINER'
            value: cosmosDbDatabaseMemoryContainerName
          }
          {
            name: 'AZURE_OPENAI_ENDPOINT'
            value: 'https://${aiFoundryAiServicesAccountName}.openai.azure.com/'
          }
          {
            name: 'AZURE_OPENAI_MODEL_NAME'
            value: aiFoundryAiServicesModelDeployment.name
          }
          {
            name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
            value: aiFoundryAiServicesModelDeployment.name
          }
          {
            name: 'AZURE_OPENAI_API_VERSION'
            value: '2025-01-01-preview' //TODO: set parameter/variable
          }
          {
            name: 'APPLICATIONINSIGHTS_INSTRUMENTATION_KEY'
            value: applicationInsights.outputs.instrumentationKey
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: applicationInsights.outputs.connectionString
          }
          {
            name: 'AZURE_AI_AGENT_PROJECT_CONNECTION_STRING'
            value: '${toLower(replace(solutionLocation,' ',''))}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${aiFoundryAiProjectName}'
            //Location should be the AI Foundry AI Project location
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
            value: aiFoundryAiProjectName
          }
          {
            name: 'FRONTEND_SITE_NAME'
            value: 'https://${webSiteName}.azurewebsites.net'
          }
        ]
      }
    ]
  }
}

// ========== Frontend server farm ========== //
module webServerfarm 'br/public:avm/res/web/serverfarm:0.4.1' = {
  name: 'web-server-farm'
  params: {
    tags: tags
    location: solutionLocation
    name: '${solutionPrefix}sfrm'
    skuName: 'P1v2'
    skuCapacity: 1
    reserved: true
    diagnosticSettings: [{ workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId }]
    kind: 'linux'
    zoneRedundant: false //TODO: make it zone redundant for waf aligned
  }
}

// ========== Entra ID Application ========== //
resource entraIdApplication 'Microsoft.Graph/applications@v1.0' = if (entraIdApplicationConfiguration.?enabled!) {
  displayName: '${webSiteName}-app'
  uniqueName: '${webSiteName}-app-${uniqueString(resourceGroup().id, webSiteName)}'
  description: 'EntraId Application for ${webSiteName} authentication'
  passwordCredentials: [
    {
      displayName: 'Credential for website ${webSiteName}'
      endDateTime: dateTimeAdd(deploymentTime, 'P180D')
      // keyId: 'string'
      // startDateTime: 'string'
    }
  ]
}

var graphAppId = '00000003-0000-0000-c000-000000000000' //Microsoft Graph ID
// Get the Microsoft Graph service principal so that the scope names can be looked up and mapped to a permission ID
resource msGraphSP 'Microsoft.Graph/servicePrincipals@v1.0' existing = {
  appId: graphAppId
}

// ========== Entra ID Service Principal ========== //
resource entraIdServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = if (entraIdApplicationConfiguration.?enabled!) {
  appId: entraIdApplication.appId
}

// Grant the OAuth2.0 scopes (requested in parameters) to the basic app, for all users in the tenant
resource graphScopesAssignment 'Microsoft.Graph/oauth2PermissionGrants@v1.0' = if (entraIdApplicationConfiguration.?enabled!) {
  clientId: entraIdServicePrincipal.id
  resourceId: msGraphSP.id
  consentType: 'AllPrincipals'
  scope: 'User.Read'
}

// ========== Frontend web site ========== //
var webSiteName = '${solutionPrefix}wapp'
var entraIdApplicationCredentialSecretSettingName = 'MICROSOFT_PROVIDER_AUTHENTICATION_SECRET'
module webSite 'br/public:avm/res/web/site:0.15.1' = {
  name: 'web-site'
  params: {
    tags: tags
    kind: 'app,linux,container'
    name: webSiteName
    location: solutionLocation
    serverFarmResourceId: webServerfarm.outputs.resourceId
    appInsightResourceId: applicationInsights.outputs.resourceId
    siteConfig: {
      linuxFxVersion: 'DOCKER|biabcontainerreg.azurecr.io/macaefrontend:fnd01'
    }
    publicNetworkAccess: 'Enabled' //TODO: use Azure Front Door WAF or Application Gateway WAF instead
    //privateEndpoints: [{ subnetResourceId: virtualNetwork.outputs.subnetResourceIds[0] }]
    //Not required, this resource only serves a static website
    appSettingsKeyValuePairs: union(
      {
        SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
        DOCKER_REGISTRY_SERVER_URL: 'https://biabcontainerreg.azurecr.io'
        WEBSITES_PORT: '3000'
        WEBSITES_CONTAINER_START_TIME_LIMIT: '1800' // 30 minutes, adjust as needed
        BACKEND_API_URL: 'https://${containerApp.outputs.fqdn}'
        AUTH_ENABLED: 'false'
      },
      (entraIdApplicationConfiguration.?enabled!
        ? { '${entraIdApplicationCredentialSecretSettingName}': entraIdApplication.passwordCredentials[0].secretText }
        : {})
    )
    authSettingV2Configuration: {
      platform: {
        enabled: entraIdApplicationConfiguration.?enabled!
        runtimeVersion: '~1'
      }
      login: {
        cookieExpiration: {
          convention: 'FixedTime'
          timeToExpiration: '08:00:00'
        }
        nonce: {
          nonceExpirationInterval: '00:05:00'
          validateNonce: true
        }
        preserveUrlFragmentsForLogins: false
        routes: {}
        tokenStore: {
          azureBlobStorage: {}
          enabled: true
          fileSystem: {}
          tokenRefreshExtensionHours: 72
        }
      }
      globalValidation: {
        requireAuthentication: true
        unauthenticatedClientAction: 'RedirectToLoginPage'
        redirectToProvider: 'azureactivedirectory'
      }
      httpSettings: {
        forwardProxy: {
          convention: 'NoProxy'
        }
        requireHttps: true
        routes: {
          apiPrefix: '/.auth'
        }
      }
      identityProviders: {
        azureActiveDirectory: entraIdApplicationConfiguration.?enabled!
          ? {
              isAutoProvisioned: true
              enabled: true
              login: {
                disableWWWAuthenticate: false
              }
              registration: {
                clientId: entraIdApplication.appId //create application in AAD
                clientSecretSettingName: entraIdApplicationCredentialSecretSettingName
                openIdIssuer: 'https://sts.windows.net/${tenant().tenantId}/v2.0/'
              }
              validation: {
                allowedAudiences: [
                  'api://${entraIdApplication.appId}'
                ]
                defaultAuthorizationPolicy: {
                  allowedPrincipals: {}
                  allowedApplications: ['86e2d249-6832-461f-8888-cfa0394a5f8c']
                }
                jwtClaimChecks: {}
              }
            }
          : {}
      }
    }
  }
}

// ============ //
// Outputs      //
// ============ //

// Add your outputs here

// @description('The resource ID of the resource.')
// output resourceId string = <Resource>.id

// @description('The name of the resource.')
// output name string = <Resource>.name

// @description('The location the resource was deployed into.')
// output location string = <Resource>.location

// ================ //
// Definitions      //
// ================ //
//
// Add your User-defined-types here, if any
//

@export()
@description('The type for the Multi-Agent Custom Automation Engine Log Analytics Workspace resource configuration.')
type logAnalyticsWorkspaceConfigurationType = {
  @description('Optional. If the Log Analytics Workspace resource should be enabled or not.')
  enabled: bool?

  @description('Optional. The name of the Log Analytics Workspace resource.')
  @maxLength(63)
  name: string?

  @description('Optional. Location for the Log Analytics Workspace resource.')
  @metadata({ azd: { type: 'location' } })
  location: string?

  @description('Optional. The tags to for the Log Analytics Workspace resource.')
  tags: object?

  @description('Optional. The SKU for the Log Analytics Workspace resource.')
  sku: ('CapacityReservation' | 'Free' | 'LACluster' | 'PerGB2018' | 'PerNode' | 'Premium' | 'Standalone' | 'Standard')?

  @description('Optional. The number of days to retain the data in the Log Analytics Workspace. If empty, it will be set to 30 days.')
  @maxValue(730)
  dataRetentionInDays: int?
}

@export()
@description('The type for the Multi-Agent Custom Automation Engine Application Insights resource configuration.')
type applicationInsightsConfigurationType = {
  @description('Optional. If the Application Insights resource should be enabled or not.')
  enabled: bool?

  @description('Optional. The name of the Application Insights resource.')
  @maxLength(90)
  name: string?

  @description('Optional. Location for the Application Insights resource.')
  @metadata({ azd: { type: 'location' } })
  location: string?

  @description('Optional. The tags to set for the Application Insights resource.')
  tags: object?

  @description('Optional. The retention of Application Insights data in days. If empty, Standard will be used.')
  retentionInDays: (120 | 180 | 270 | 30 | 365 | 550 | 60 | 730 | 90)?
}

@export()
@description('The type for the Multi-Agent Custom Automation Engine Application User Assigned Managed Identity resource configuration.')
type userAssignedManagedIdentityType = {
  @description('Optional. If the User Assigned Managed Identity resource should be enabled or not.')
  enabled: bool?

  @description('Optional. The name of the User Assigned Managed Identity resource.')
  @maxLength(128)
  name: string?

  @description('Optional. Location for the User Assigned Managed Identity resource.')
  @metadata({ azd: { type: 'location' } })
  location: string?

  @description('Optional. The tags to set for the User Assigned Managed Identity resource.')
  tags: object?
}

@export()
import { securityRuleType } from 'br/public:avm/res/network/network-security-group:0.5.1'
@description('The type for the Multi-Agent Custom Automation Engine Network Security Group resource configuration.')
type networkSecurityGroupConfigurationType = {
  @description('Optional. If the Network Security Group resource should be enabled or not.')
  enabled: bool?

  @description('Optional. The name of the Network Security Group resource.')
  @maxLength(90)
  name: string?

  @description('Optional. Location for the Network Security Group resource.')
  @metadata({ azd: { type: 'location' } })
  location: string?

  @description('Optional. The tags to set for the Network Security Group resource.')
  tags: object?

  @description('Optional. The security rules to set for the Network Security Group resource.')
  securityRules: securityRuleType[]?
}

@export()
@description('The type for the Multi-Agent Custom Automation virtual machine resource configuration.')
type virtualMachineConfigurationType = {
  @description('Optional. If the Virtual Machine resource should be enabled or not.')
  enabled: bool?

  @description('Required. The username for the administrator account on the virtual machine. Required if a virtual machine is created as part of the module.')
  adminUsername: string?

  @description('Required. The password for the administrator account on the virtual machine. Required if a virtual machine is created as part of the module.')
  @secure()
  adminPassword: string?
}

@export()
@description('The type for the Multi-Agent Custom Automation virtual network resource configuration.')
type virtualNetworkConfigurationType = {
  @description('Optional. If the Virtual Network resource should be enabled or not.')
  enabled: bool?
}

@export()
@description('The type for the Multi-Agent Custom Automation Engine Entra ID Application resource configuration.')
type entraIdApplicationConfigurationType = {
  @description('Optional. If the Entra ID Application for website authentication should be enabled or not.')
  enabled: bool?
}

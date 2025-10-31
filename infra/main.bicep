// // ========== main.bicep ========== //
targetScope = 'resourceGroup'

metadata name = 'Multi-Agent Custom Automation Engine'
metadata description = '''This module contains the resources required to deploy the [Multi-Agent Custom Automation Engine solution accelerator](https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator) for both Sandbox environments and WAF aligned environments.

> **Note:** This module is not intended for broad, generic use, as it was designed by the Commercial Solution Areas CTO team, as a Microsoft Solution Accelerator. Feature requests and bug fix requests are welcome if they support the needs of this organization but may not be incorporated if they aim to make this module more generic than what it needs to be for its primary use case. This module will likely be updated to leverage AVM resource modules in the future. This may result in breaking changes in upcoming versions when these features are implemented.
'''

@description('Optional. A unique application/solution name for all resources in this deployment. This should be 3-16 characters long.')
@minLength(3)
@maxLength(16)
param solutionName string = 'macae'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = take(uniqueString(subscription().id, resourceGroup().name, solutionName), 5)

@metadata({ azd: { type: 'location' } })
@description('Required. Azure region for all services. Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).')
@allowed([
  'australiaeast'
  'centralus'
  'eastasia'
  'eastus2'
  'japaneast'
  'northeurope'
  'southeastasia'
  'uksouth'
])
param location string

//Get the current deployer's information
var deployerInfo = deployer()
var deployingUserPrincipalId = deployerInfo.objectId

// Restricting deployment to only supported Azure OpenAI regions validated with GPT-4o model
@allowed(['australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus'])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1, 150'
      'OpenAI.GlobalStandard.o4-mini, 50'
      'OpenAI.GlobalStandard.gpt4.1-mini, 50'
    ]
  }
})
@description('Required. Location for all AI service resources. This should be one of the supported Azure AI Service locations.')
param azureAiServiceLocation string

@minLength(1)
@description('Optional. Name of the GPT model to deploy:')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the GPT model to deploy. Defaults to 2025-04-14.')
param gptModelVersion string = '2025-04-14'

@minLength(1)
@description('Optional. Name of the GPT model to deploy:')
param gpt4_1ModelName string = 'gpt-4.1'

@description('Optional. Version of the GPT model to deploy. Defaults to 2025-04-14.')
param gpt4_1ModelVersion string = '2025-04-14'

@minLength(1)
@description('Optional. Name of the GPT Reasoning model to deploy:')
param gptReasoningModelName string = 'o4-mini'

@description('Optional. Version of the GPT Reasoning model to deploy. Defaults to 2025-04-14.')
param gptReasoningModelVersion string = '2025-04-16'

@description('Optional. Version of the Azure OpenAI service to deploy. Defaults to 2025-01-01-preview.')
param azureopenaiVersion string = '2024-12-01-preview'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT model deployment type. Defaults to GlobalStandard.')
param gpt4_1ModelDeploymentType string = 'GlobalStandard'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT model deployment type. Defaults to GlobalStandard.')
param gptModelDeploymentType string = 'GlobalStandard'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT model deployment type. Defaults to GlobalStandard.')
param gptReasoningModelDeploymentType string = 'GlobalStandard'

@description('Optional. AI model deployment token capacity. Defaults to 50 for optimal performance.')
param gptModelCapacity int = 50

@description('Optional. AI model deployment token capacity. Defaults to 150 for optimal performance.')
param gpt4_1ModelCapacity int = 150

@description('Optional. AI model deployment token capacity. Defaults to 50 for optimal performance.')
param gptReasoningModelCapacity int = 50

@description('Optional. The tags to apply to all deployed Azure resources.')
param tags resourceInput<'Microsoft.Resources/resourceGroups@2025-04-01'>.tags = {}

@description('Optional. Enable monitoring applicable resources, aligned with the Well Architected Framework recommendations. This setting enables Application Insights and Log Analytics and configures all the resources applicable resources to send logs. Defaults to false.')
param enableMonitoring bool = false

@description('Optional. Enable scalability for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableScalability bool = false

@description('Optional. Enable redundancy for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enableRedundancy bool = false

@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')
param enablePrivateNetworking bool = false

@secure()
@description('Optional. The user name for the administrator account of the virtual machine. Allows to customize credentials if `enablePrivateNetworking` is set to true.')
param virtualMachineAdminUsername string = take(newGuid(), 20)

@description('Optional. The password for the administrator account of the virtual machine. Allows to customize credentials if `enablePrivateNetworking` is set to true.')
@secure()
param virtualMachineAdminPassword string = newGuid()

// These parameters are changed for testing - please reset as part of publication

@description('Optional. The Container Registry hostname where the docker images for the backend are located.')
param backendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the backend.')
param backendContainerImageName string = 'macaebackend'

@description('Optional. The Container Image Tag to deploy on the backend.')
param backendContainerImageTag string = 'latest_v3'

@description('Optional. The Container Registry hostname where the docker images for the frontend are located.')
param frontendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the frontend.')
param frontendContainerImageName string = 'macaefrontend'

@description('Optional. The Container Image Tag to deploy on the frontend.')
param frontendContainerImageTag string = 'latest_v3'

@description('Optional. The Container Registry hostname where the docker images for the MCP are located.')
param MCPContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the MCP.')
param MCPContainerImageName string = 'macaemcp'

@description('Optional. The Container Image Tag to deploy on the MCP.')
param MCPContainerImageTag string = 'latest_v3'

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. Resource ID of an existing Log Analytics Workspace.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing Ai Foundry AI Services resource.')
param existingAiFoundryAiProjectResourceId string = ''

// ============== //
// Variables      //
// ============== //

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

// Region pairs list based on article in [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions) for supported high availability regions for CosmosDB.
var cosmosDbZoneRedundantHaRegionPairs = {
  australiaeast: 'uksouth'
  centralus: 'eastus2'
  eastasia: 'southeastasia'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'australiaeast'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
}
// Paired location calculated based on 'location' parameter. This location will be used by applicable resources if `enableScalability` is set to `true`
var cosmosDbHaLocation = cosmosDbZoneRedundantHaRegionPairs[location]

// Replica regions list based on article in [Azure regions list](https://learn.microsoft.com/azure/reliability/regions-list) and [Enhance resilience by replicating your Log Analytics workspace across regions](https://learn.microsoft.com/azure/azure-monitor/logs/workspace-replication#supported-regions) for supported regions for Log Analytics Workspace.
var replicaRegionPairs = {
  australiaeast: 'australiasoutheast'
  centralus: 'westus'
  eastasia: 'japaneast'
  eastus: 'centralus'
  eastus2: 'centralus'
  japaneast: 'eastasia'
  northeurope: 'westeurope'
  southeastasia: 'eastasia'
  uksouth: 'westeurope'
  westeurope: 'northeurope'
}
var replicaLocation = replicaRegionPairs[location]

// ============== //
// Resources      //
// ============== //


var allTags = union(
  {
    'azd-env-name': solutionName
  },
  tags
)
@description('Tag, Created by user name')
param createdBy string = contains(deployer(), 'userPrincipalName')? split(deployer().userPrincipalName, '@')[0]: deployer().objectId
var deployerPrincipalType = contains(deployer(), 'userPrincipalName')? 'User' : 'ServicePrincipal'

resource resourceGroupTags 'Microsoft.Resources/tags@2021-04-01' = {
  name: 'default'
  properties: {
    tags: {
      ...resourceGroup().tags
      ...allTags
      TemplateName: 'MACAE'
      Type: enablePrivateNetworking ? 'WAF' : 'Non-WAF'
      CreatedBy: createdBy
      DeploymentName: deployment().name
    }
  }
}


#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2024-03-01' = if (enableTelemetry) {
  name: '46d3xbcp.ptn.sa-multiagentcustauteng.${replace('-..--..-', '.', '-')}.${substring(uniqueString(deployment().name, location), 0, 4)}'
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
}

// Extracts subscription, resource group, and workspace name from the resource ID when using an existing Log Analytics workspace
var useExistingLogAnalytics = !empty(existingLogAnalyticsWorkspaceId)

var existingLawSubscription = useExistingLogAnalytics ? split(existingLogAnalyticsWorkspaceId, '/')[2] : ''
var existingLawResourceGroup = useExistingLogAnalytics ? split(existingLogAnalyticsWorkspaceId, '/')[4] : ''
var existingLawName = useExistingLogAnalytics ? split(existingLogAnalyticsWorkspaceId, '/')[8] : ''

resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2020-08-01' existing = if (useExistingLogAnalytics) {
  name: existingLawName
  scope: resourceGroup(existingLawSubscription, existingLawResourceGroup)
}

// ========== Log Analytics Workspace ========== //
// WAF best practices for Log Analytics: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-log-analytics
// WAF PSRules for Log Analytics: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#azure-monitor-logs
var logAnalyticsWorkspaceResourceName = 'log-${solutionSuffix}'
module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.12.0' = if (enableMonitoring && !useExistingLogAnalytics) {
  name: take('avm.res.operational-insights.workspace.${logAnalyticsWorkspaceResourceName}', 64)
  params: {
    name: logAnalyticsWorkspaceResourceName
    tags: tags
    location: location
    enableTelemetry: enableTelemetry
    skuName: 'PerGB2018'
    dataRetention: 365
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
    diagnosticSettings: [{ useThisWorkspace: true }]
    // WAF aligned configuration for Redundancy
    dailyQuotaGb: enableRedundancy ? 150 : null //WAF recommendation: 150 GB per day is a good starting point for most workloads
    replication: enableRedundancy
      ? {
          enabled: true
          location: replicaLocation
        }
      : null
    // WAF aligned configuration for Private Networking
    publicNetworkAccessForIngestion: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    publicNetworkAccessForQuery: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    dataSources: enablePrivateNetworking
      ? [
          {
            tags: tags
            eventLogName: 'Application'
            eventTypes: [
              {
                eventType: 'Error'
              }
              {
                eventType: 'Warning'
              }
              {
                eventType: 'Information'
              }
            ]
            kind: 'WindowsEvent'
            name: 'applicationEvent'
          }
          {
            counterName: '% Processor Time'
            instanceName: '*'
            intervalSeconds: 60
            kind: 'WindowsPerformanceCounter'
            name: 'windowsPerfCounter1'
            objectName: 'Processor'
          }
          {
            kind: 'IISLogs'
            name: 'sampleIISLog1'
            state: 'OnPremiseEnabled'
          }
        ]
      : null
  }
}
// Log Analytics Name, workspace ID, customer ID, and shared key (existing or new) 
var logAnalyticsWorkspaceName = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.name
  : logAnalyticsWorkspace!.outputs.name
var logAnalyticsWorkspaceResourceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspaceId
  : logAnalyticsWorkspace!.outputs.resourceId
var logAnalyticsPrimarySharedKey = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.listKeys().primarySharedKey
  : logAnalyticsWorkspace!.outputs!.primarySharedKey
var logAnalyticsWorkspaceId = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.properties.customerId
  : logAnalyticsWorkspace!.outputs.logAnalyticsWorkspaceId

// ========== Application Insights ========== //
// WAF best practices for Application Insights: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/application-insights
// WAF PSRules for  Application Insights: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#application-insights
var applicationInsightsResourceName = 'appi-${solutionSuffix}'
module applicationInsights 'br/public:avm/res/insights/component:0.6.0' = if (enableMonitoring) {
  name: take('avm.res.insights.component.${applicationInsightsResourceName}', 64)
  params: {
    name: applicationInsightsResourceName
    tags: tags
    location: location
    enableTelemetry: enableTelemetry
    retentionInDays: 365
    kind: 'web'
    disableIpMasking: false
    flowType: 'Bluefield'
    // WAF aligned configuration for Monitoring
    workspaceResourceId: enableMonitoring ? logAnalyticsWorkspaceResourceId : ''
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
  }
}

// ========== User Assigned Identity ========== //
// WAF best practices for identity and access management: https://learn.microsoft.com/en-us/azure/well-architected/security/identity-access
var userAssignedIdentityResourceName = 'id-${solutionSuffix}'
module userAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: take('avm.res.managed-identity.user-assigned-identity.${userAssignedIdentityResourceName}', 64)
  params: {
    name: userAssignedIdentityResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
  }
}
// ========== Virtual Network ========== //
// WAF best practices for virtual networks: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/virtual-network
// WAF recommendations for networking and connectivity: https://learn.microsoft.com/en-us/azure/well-architected/security/networking
var virtualNetworkResourceName = 'vnet-${solutionSuffix}'
module virtualNetwork 'modules/virtualNetwork.bicep' = if (enablePrivateNetworking) {
  name: take('module.virtualNetwork.${solutionSuffix}', 64)
  params: {
    name: 'vnet-${solutionSuffix}'
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    addressPrefixes: ['10.0.0.0/8']
    logAnalyticsWorkspaceId: logAnalyticsWorkspaceResourceId
    resourceSuffix: solutionSuffix
  }
}

var bastionResourceName = 'bas-${solutionSuffix}'
// ========== Bastion host ========== //
// WAF best practices for virtual networks: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/virtual-network
// WAF recommendations for networking and connectivity: https://learn.microsoft.com/en-us/azure/well-architected/security/networking
module bastionHost 'br/public:avm/res/network/bastion-host:0.7.0' = if (enablePrivateNetworking) {
  name: take('avm.res.network.bastion-host.${bastionResourceName}', 64)
  params: {
    name: bastionResourceName
    location: location
    skuName: 'Standard'
    enableTelemetry: enableTelemetry
    tags: tags
    virtualNetworkResourceId: virtualNetwork!.?outputs.?resourceId
    availabilityZones:[]
    publicIPAddressObject: {
      name: 'pip-bas${solutionSuffix}'
      diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
      tags: tags
    }
    disableCopyPaste: true
    enableFileCopy: false
    enableIpConnect: false
    enableShareableLink: false
    scaleUnits: 4
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
  }
}

// ========== Virtual machine ========== //
// WAF best practices for virtual machines: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/virtual-machines
var maintenanceConfigurationResourceName = 'mc-${solutionSuffix}'
module maintenanceConfiguration 'br/public:avm/res/maintenance/maintenance-configuration:0.3.1' = if (enablePrivateNetworking) {
  name: take('avm.res.compute.virtual-machine.${maintenanceConfigurationResourceName}', 64)
  params: {
    name: maintenanceConfigurationResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    extensionProperties: {
      InGuestPatchMode: 'User'
    }
    maintenanceScope: 'InGuestPatch'
    maintenanceWindow: {
      startDateTime: '2024-06-16 00:00'
      duration: '03:55'
      timeZone: 'W. Europe Standard Time'
      recurEvery: '1Day'
    }
    visibility: 'Custom'
    installPatches: {
      rebootSetting: 'IfRequired'
      windowsParameters: {
        classificationsToInclude: [
          'Critical'
          'Security'
        ]
      }
      linuxParameters: {
        classificationsToInclude: [
          'Critical'
          'Security'
        ]
      }
    }
  }
}

var dataCollectionRulesResourceName = 'dcr-${solutionSuffix}'
var dataCollectionRulesLocation = useExistingLogAnalytics
  ? existingLogAnalyticsWorkspace!.location
  : logAnalyticsWorkspace!.outputs.location
module windowsVmDataCollectionRules 'br/public:avm/res/insights/data-collection-rule:0.6.1' = if (enablePrivateNetworking && enableMonitoring) {
  name: take('avm.res.insights.data-collection-rule.${dataCollectionRulesResourceName}', 64)
  params: {
    name: dataCollectionRulesResourceName
    tags: tags
    enableTelemetry: enableTelemetry
    location: dataCollectionRulesLocation
    dataCollectionRuleProperties: {
      kind: 'Windows'
      dataSources: {
        performanceCounters: [
          {
            streams: [
              'Microsoft-Perf'
            ]
            samplingFrequencyInSeconds: 60
            counterSpecifiers: [
              '\\Processor Information(_Total)\\% Processor Time'
              '\\Processor Information(_Total)\\% Privileged Time'
              '\\Processor Information(_Total)\\% User Time'
              '\\Processor Information(_Total)\\Processor Frequency'
              '\\System\\Processes'
              '\\Process(_Total)\\Thread Count'
              '\\Process(_Total)\\Handle Count'
              '\\System\\System Up Time'
              '\\System\\Context Switches/sec'
              '\\System\\Processor Queue Length'
              '\\Memory\\% Committed Bytes In Use'
              '\\Memory\\Available Bytes'
              '\\Memory\\Committed Bytes'
              '\\Memory\\Cache Bytes'
              '\\Memory\\Pool Paged Bytes'
              '\\Memory\\Pool Nonpaged Bytes'
              '\\Memory\\Pages/sec'
              '\\Memory\\Page Faults/sec'
              '\\Process(_Total)\\Working Set'
              '\\Process(_Total)\\Working Set - Private'
              '\\LogicalDisk(_Total)\\% Disk Time'
              '\\LogicalDisk(_Total)\\% Disk Read Time'
              '\\LogicalDisk(_Total)\\% Disk Write Time'
              '\\LogicalDisk(_Total)\\% Idle Time'
              '\\LogicalDisk(_Total)\\Disk Bytes/sec'
              '\\LogicalDisk(_Total)\\Disk Read Bytes/sec'
              '\\LogicalDisk(_Total)\\Disk Write Bytes/sec'
              '\\LogicalDisk(_Total)\\Disk Transfers/sec'
              '\\LogicalDisk(_Total)\\Disk Reads/sec'
              '\\LogicalDisk(_Total)\\Disk Writes/sec'
              '\\LogicalDisk(_Total)\\Avg. Disk sec/Transfer'
              '\\LogicalDisk(_Total)\\Avg. Disk sec/Read'
              '\\LogicalDisk(_Total)\\Avg. Disk sec/Write'
              '\\LogicalDisk(_Total)\\Avg. Disk Queue Length'
              '\\LogicalDisk(_Total)\\Avg. Disk Read Queue Length'
              '\\LogicalDisk(_Total)\\Avg. Disk Write Queue Length'
              '\\LogicalDisk(_Total)\\% Free Space'
              '\\LogicalDisk(_Total)\\Free Megabytes'
              '\\Network Interface(*)\\Bytes Total/sec'
              '\\Network Interface(*)\\Bytes Sent/sec'
              '\\Network Interface(*)\\Bytes Received/sec'
              '\\Network Interface(*)\\Packets/sec'
              '\\Network Interface(*)\\Packets Sent/sec'
              '\\Network Interface(*)\\Packets Received/sec'
              '\\Network Interface(*)\\Packets Outbound Errors'
              '\\Network Interface(*)\\Packets Received Errors'
            ]
            name: 'perfCounterDataSource60'
          }
        ]
        windowsEventLogs: [
          {
            name: 'SecurityAuditEvents'
            streams: [
              'Microsoft-WindowsEvent'
            ]
            eventLogName: 'Security'
            eventTypes: [
              {
                eventType: 'Audit Success'
              }
              {
                eventType: 'Audit Failure'
              }
            ]
            xPathQueries: [
              'Security!*[System[(EventID=4624 or EventID=4625)]]'
            ]
          }
        ]
      }
      destinations: {
        logAnalytics: [
          {
            workspaceResourceId: logAnalyticsWorkspaceResourceId
            name: 'la--1264800308'
          }
        ]
      }
      dataFlows: [
        {
          streams: [
            'Microsoft-Perf'
          ]
          destinations: [
            'la--1264800308'
          ]
          transformKql: 'source'
          outputStream: 'Microsoft-Perf'
        }
      ]
    }
  }
}

var proximityPlacementGroupResourceName = 'ppg-${solutionSuffix}'
module proximityPlacementGroup 'br/public:avm/res/compute/proximity-placement-group:0.4.0' = if (enablePrivateNetworking) {
  name: take('avm.res.compute.proximity-placement-group.${proximityPlacementGroupResourceName}', 64)
  params: {
    name: proximityPlacementGroupResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    availabilityZone: virtualMachineAvailabilityZone
    intent: { vmSizes: [virtualMachineSize] }
  }
}

var virtualMachineResourceName = 'vm-${solutionSuffix}'
var virtualMachineAvailabilityZone = 1
var virtualMachineSize = 'Standard_D2s_v3'
module virtualMachine 'br/public:avm/res/compute/virtual-machine:0.17.0' = if (enablePrivateNetworking) {
  name: take('avm.res.compute.virtual-machine.${virtualMachineResourceName}', 64)
  params: {
    name: virtualMachineResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    computerName: take(virtualMachineResourceName, 15)
    osType: 'Windows'
    vmSize: virtualMachineSize
    adminUsername: virtualMachineAdminUsername
    adminPassword: virtualMachineAdminPassword
    patchMode: 'AutomaticByPlatform'
    bypassPlatformSafetyChecksOnUserSchedule: true
    maintenanceConfigurationResourceId: maintenanceConfiguration!.outputs.resourceId
    enableAutomaticUpdates: true
    encryptionAtHost: true
    availabilityZone: virtualMachineAvailabilityZone
    proximityPlacementGroupResourceId: proximityPlacementGroup!.outputs.resourceId
    imageReference: {
      publisher: 'microsoft-dsvm'
      offer: 'dsvm-win-2022'
      sku: 'winserver-2022'
      version: 'latest'
    }
    osDisk: {
      name: 'osdisk-${virtualMachineResourceName}'
      caching: 'ReadWrite'
      createOption: 'FromImage'
      deleteOption: 'Delete'
      diskSizeGB: 128
      managedDisk: { storageAccountType: 'Premium_LRS' }
    }
    nicConfigurations: [
      {
        name: 'nic-${virtualMachineResourceName}'
        //networkSecurityGroupResourceId: virtualMachineConfiguration.?nicConfigurationConfiguration.networkSecurityGroupResourceId
        //nicSuffix: 'nic-${virtualMachineResourceName}'
        tags: tags
        deleteOption: 'Delete'
        diagnosticSettings: enableMonitoring //WAF aligned configuration for Monitoring
          ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }]
          : null
        ipConfigurations: [
          {
            name: '${virtualMachineResourceName}-nic01-ipconfig01'
            subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId
            diagnosticSettings: enableMonitoring //WAF aligned configuration for Monitoring
              ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }]
              : null
          }
        ]
      }
    ]
    extensionAadJoinConfig: {
      enabled: true
      tags: tags
      typeHandlerVersion: '1.0'
    }
    extensionAntiMalwareConfig: {
      enabled: true
      settings: {
        AntimalwareEnabled: 'true'
        Exclusions: {}
        RealtimeProtectionEnabled: 'true'
        ScheduledScanSettings: {
          day: '7'
          isEnabled: 'true'
          scanType: 'Quick'
          time: '120'
        }
      }
      tags: tags
    }
    //WAF aligned configuration for Monitoring
    extensionMonitoringAgentConfig: enableMonitoring
      ? {
          dataCollectionRuleAssociations: [
            {
              dataCollectionRuleResourceId: windowsVmDataCollectionRules!.outputs.resourceId
              name: 'send-${logAnalyticsWorkspaceName}'
            }
          ]
          enabled: true
          tags: tags
        }
      : null
    extensionNetworkWatcherAgentConfig: {
      enabled: true
      tags: tags
    }
  }
}

// ========== Private DNS Zones ========== //
var keyVaultPrivateDNSZone = 'privatelink.${toLower(environment().name) == 'azureusgovernment' ? 'vaultcore.usgovcloudapi.net' : 'vaultcore.azure.net'}'
var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.documents.azure.com'
  'privatelink.blob.core.windows.net'
  'privatelink.search.windows.net'
  keyVaultPrivateDNSZone
]

// DNS Zone Index Constants
var dnsZoneIndex = {
  cognitiveServices: 0
  openAI: 1
  aiServices: 2
  cosmosDb: 3
  blob: 4
  search: 5
  keyVault: 6
}

// List of DNS zone indices that correspond to AI-related services.
var aiRelatedDnsZoneIndices = [
  dnsZoneIndex.cognitiveServices
  dnsZoneIndex.openAI
  dnsZoneIndex.aiServices
]

// ===================================================
// DEPLOY PRIVATE DNS ZONES
// - Deploys all zones if no existing Foundry project is used
// - Excludes AI-related zones when using with an existing Foundry project
// ===================================================
@batchSize(5)
module avmPrivateDnsZones 'br/public:avm/res/network/private-dns-zone:0.7.1' = [
  for (zone, i) in privateDnsZones: if (enablePrivateNetworking && (!useExistingAiFoundryAiProject || !contains(
    aiRelatedDnsZoneIndices,
    i
  ))) {
    name: 'avm.res.network.private-dns-zone.${contains(zone, 'azurecontainerapps.io') ? 'containerappenv' : split(zone, '.')[1]}'
    params: {
      name: zone
      tags: tags
      enableTelemetry: enableTelemetry
      virtualNetworkLinks: [
        {
          name: take('vnetlink-${virtualNetworkResourceName}-${split(zone, '.')[1]}', 80)
          virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
        }
      ]
    }
  }
]

// ========== AI Foundry: AI Services ========== //
// WAF best practices for Open AI: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-openai

var useExistingAiFoundryAiProject = !empty(existingAiFoundryAiProjectResourceId)
var aiFoundryAiServicesResourceGroupName = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[4]
  : resourceGroup().name
var aiFoundryAiServicesSubscriptionId = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[2]
  : subscription().subscriptionId
var aiFoundryAiServicesResourceName = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[8]
  : 'aif-${solutionSuffix}'
var aiFoundryAiProjectResourceName = useExistingAiFoundryAiProject
  ? split(existingAiFoundryAiProjectResourceId, '/')[10]
  : 'proj-${solutionSuffix}' // AI Project resource id: /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.CognitiveServices/accounts/<ai-services-name>/projects/<project-name>
var aiFoundryAiServicesModelDeployment = {
  format: 'OpenAI'
  name: gptModelName
  version: gptModelVersion
  sku: {
    name: gptModelDeploymentType
    capacity: gptModelCapacity
  }
  raiPolicyName: 'Microsoft.Default'
}
var aiFoundryAiServices4_1ModelDeployment = {
  format: 'OpenAI'
  name: gpt4_1ModelName
  version: gpt4_1ModelVersion
  sku: {
    name: gpt4_1ModelDeploymentType
    capacity: gpt4_1ModelCapacity
  }
  raiPolicyName: 'Microsoft.Default'
}
var aiFoundryAiServicesReasoningModelDeployment = {
  format: 'OpenAI'
  name: gptReasoningModelName
  version: gptReasoningModelVersion
  sku: {
    name: gptReasoningModelDeploymentType
    capacity: gptReasoningModelCapacity
  }
  raiPolicyName: 'Microsoft.Default'
}
var aiFoundryAiProjectDescription = 'AI Foundry Project'

resource existingAiFoundryAiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = if (useExistingAiFoundryAiProject) {
  name: aiFoundryAiServicesResourceName
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
}

module existingAiFoundryAiServicesDeployments 'modules/ai-services-deployments.bicep' = if (useExistingAiFoundryAiProject) {
  name: take('module.ai-services-model-deployments.${existingAiFoundryAiServices.name}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    name: existingAiFoundryAiServices.name
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
      {
        name: aiFoundryAiServices4_1ModelDeployment.name
        model: {
          format: aiFoundryAiServices4_1ModelDeployment.format
          name: aiFoundryAiServices4_1ModelDeployment.name
          version: aiFoundryAiServices4_1ModelDeployment.version
        }
        raiPolicyName: aiFoundryAiServices4_1ModelDeployment.raiPolicyName
        sku: {
          name: aiFoundryAiServices4_1ModelDeployment.sku.name
          capacity: aiFoundryAiServices4_1ModelDeployment.sku.capacity
        }
      }
      {
        name: aiFoundryAiServicesReasoningModelDeployment.name
        model: {
          format: aiFoundryAiServicesReasoningModelDeployment.format
          name: aiFoundryAiServicesReasoningModelDeployment.name
          version: aiFoundryAiServicesReasoningModelDeployment.version
        }
        raiPolicyName: aiFoundryAiServicesReasoningModelDeployment.raiPolicyName
        sku: {
          name: aiFoundryAiServicesReasoningModelDeployment.sku.name
          capacity: aiFoundryAiServicesReasoningModelDeployment.sku.capacity
        }
      }
    ]
    roleAssignments: [
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '64702f94-c441-49e6-a78b-ef80e0188fee' // Azure AI Developer
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

module aiFoundryAiServices 'br:mcr.microsoft.com/bicep/avm/res/cognitive-services/account:0.13.2' = if (!useExistingAiFoundryAiProject) {
  name: take('avm.res.cognitive-services.account.${aiFoundryAiServicesResourceName}', 64)
  params: {
    name: aiFoundryAiServicesResourceName
    location: azureAiServiceLocation
    tags: tags
    sku: 'S0'
    kind: 'AIServices'
    disableLocalAuth: true
    allowProjectManagement: true
    customSubDomainName: aiFoundryAiServicesResourceName
    apiProperties: {
      //staticsEnabled: false
    }
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
      {
        name: aiFoundryAiServices4_1ModelDeployment.name
        model: {
          format: aiFoundryAiServices4_1ModelDeployment.format
          name: aiFoundryAiServices4_1ModelDeployment.name
          version: aiFoundryAiServices4_1ModelDeployment.version
        }
        raiPolicyName: aiFoundryAiServices4_1ModelDeployment.raiPolicyName
        sku: {
          name: aiFoundryAiServices4_1ModelDeployment.sku.name
          capacity: aiFoundryAiServices4_1ModelDeployment.sku.capacity
        }
      }
      {
        name: aiFoundryAiServicesReasoningModelDeployment.name
        model: {
          format: aiFoundryAiServicesReasoningModelDeployment.format
          name: aiFoundryAiServicesReasoningModelDeployment.name
          version: aiFoundryAiServicesReasoningModelDeployment.version
        }
        raiPolicyName: aiFoundryAiServicesReasoningModelDeployment.raiPolicyName
        sku: {
          name: aiFoundryAiServicesReasoningModelDeployment.sku.name
          capacity: aiFoundryAiServicesReasoningModelDeployment.sku.capacity
        }
      }
    ]
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    managedIdentities: { userAssignedResourceIds: [userAssignedIdentity!.outputs.resourceId] } //To create accounts or projects, you must enable a managed identity on your resource
    roleAssignments: [
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '64702f94-c441-49e6-a78b-ef80e0188fee' // Azure AI Developer
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
        principalId: userAssignedIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
        principalId: deployingUserPrincipalId
        principalType: deployerPrincipalType
      }
      {
        roleDefinitionIdOrName: '64702f94-c441-49e6-a78b-ef80e0188fee' // Azure AI Developer
        principalId: deployingUserPrincipalId
        principalType: deployerPrincipalType
      }
    ]
    // WAF aligned configuration for Monitoring
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    privateEndpoints: (enablePrivateNetworking)
      ? ([
          {
            name: 'pep-${aiFoundryAiServicesResourceName}'
            customNetworkInterfaceName: 'nic-${aiFoundryAiServicesResourceName}'
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'ai-services-dns-zone-cognitiveservices'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cognitiveServices]!.outputs.resourceId
                }
                {
                  name: 'ai-services-dns-zone-openai'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.openAI]!.outputs.resourceId
                }
                {
                  name: 'ai-services-dns-zone-aiservices'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.aiServices]!.outputs.resourceId
                }
              ]
            }
          }
        ])
      : []
  }
}

resource existingAiFoundryAiServicesProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = if (useExistingAiFoundryAiProject) {
  name: aiFoundryAiProjectResourceName
  parent: existingAiFoundryAiServices
}

module aiFoundryAiServicesProject 'modules/ai-project.bicep' = if (!useExistingAiFoundryAiProject) {
  name: take('module.ai-project.${aiFoundryAiProjectResourceName}', 64)
  params: {
    name: aiFoundryAiProjectResourceName
    location: azureAiServiceLocation
    tags: tags
    desc: aiFoundryAiProjectDescription
    //Implicit dependencies below
    aiServicesName: aiFoundryAiServices!.outputs.name
  }
}

var aiFoundryAiProjectName = useExistingAiFoundryAiProject
  ? existingAiFoundryAiServicesProject.name
  : aiFoundryAiServicesProject!.outputs.name
var aiFoundryAiProjectEndpoint = useExistingAiFoundryAiProject
  ? existingAiFoundryAiServicesProject!.properties.endpoints['AI Foundry API']
  : aiFoundryAiServicesProject!.outputs.apiEndpoint
var aiFoundryAiProjectPrincipalId = useExistingAiFoundryAiProject
  ? existingAiFoundryAiServicesProject!.identity.principalId
  : aiFoundryAiServicesProject!.outputs.principalId

// ========== Cosmos DB ========== //
// WAF best practices for Cosmos DB: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/cosmos-db

var cosmosDbResourceName = 'cosmos-${solutionSuffix}'
var cosmosDbDatabaseName = 'macae'
var cosmosDbDatabaseMemoryContainerName = 'memory'

module cosmosDb 'br/public:avm/res/document-db/database-account:0.15.0' = {
  name: take('avm.res.document-db.database-account.${cosmosDbResourceName}', 64)
  params: {
    // Required parameters
    name: cosmosDbResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
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
    dataPlaneRoleDefinitions: [
      {
        // Cosmos DB Built-in Data Contributor: https://docs.azure.cn/en-us/cosmos-db/nosql/security/reference-data-plane-roles#cosmos-db-built-in-data-contributor
        roleName: 'Cosmos DB SQL Data Contributor'
        dataActions: [
          'Microsoft.DocumentDB/databaseAccounts/readMetadata'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*'
        ]
        assignments: [
          { principalId: userAssignedIdentity.outputs.principalId }
          { principalId: deployingUserPrincipalId }
        ]
      }
    ]
    // WAF aligned configuration for Monitoring
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    // WAF aligned configuration for Private Networking
    networkRestrictions: {
      networkAclBypass: 'None'
      publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    }
    privateEndpoints: enablePrivateNetworking
      ? [
          {
            name: 'pep-${cosmosDbResourceName}'
            customNetworkInterfaceName: 'nic-${cosmosDbResourceName}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                { privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.cosmosDb]!.outputs.resourceId }
              ]
            }
            service: 'Sql'
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
          }
        ]
      : []
    // WAF aligned configuration for Redundancy
    zoneRedundant: enableRedundancy ? true : false
    capabilitiesToAdd: enableRedundancy ? null : ['EnableServerless']
    automaticFailover: enableRedundancy ? true : false
    failoverLocations: enableRedundancy
      ? [
          {
            failoverPriority: 0
            isZoneRedundant: true
            locationName: location
          }
          {
            failoverPriority: 1
            isZoneRedundant: true
            locationName: cosmosDbHaLocation
          }
        ]
      : [
          {
            locationName: location
            failoverPriority: 0
            isZoneRedundant: enableRedundancy
          }
        ]
  }
}

// ========== Backend Container App Environment ========== //
// WAF best practices for container apps: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-container-apps
// PSRule for Container App: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#container-app
var containerAppEnvironmentResourceName = 'cae-${solutionSuffix}'
module containerAppEnvironment 'br/public:avm/res/app/managed-environment:0.11.2' = {
  name: take('avm.res.app.managed-environment.${containerAppEnvironmentResourceName}', 64)
  params: {
    name: containerAppEnvironmentResourceName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    // WAF aligned configuration for Private Networking
    publicNetworkAccess: 'Enabled' // Always enabling the publicNetworkAccess for Container App Environment
    internal: false //  Must be false when publicNetworkAccess is'Enabled'
    infrastructureSubnetResourceId: enablePrivateNetworking ? virtualNetwork.?outputs.?containerSubnetResourceId : null
    // WAF aligned configuration for Monitoring
    appLogsConfiguration: enableMonitoring
      ? {
          destination: 'log-analytics'
          logAnalyticsConfiguration: {
            customerId: logAnalyticsWorkspaceId
            sharedKey: logAnalyticsPrimarySharedKey
          }
        }
      : null
    appInsightsConnectionString: enableMonitoring ? applicationInsights!.outputs.connectionString : null
    // WAF aligned configuration for Redundancy
    zoneRedundant: enableRedundancy ? true : false
    infrastructureResourceGroupName: enableRedundancy ? '${resourceGroup().name}-infra' : null
    workloadProfiles: enableRedundancy
      ? [
          {
            maximumCount: 3
            minimumCount: 3
            name: 'CAW01'
            workloadProfileType: 'D4'
          }
        ]
      : [
          {
            name: 'Consumption'
            workloadProfileType: 'Consumption'
          }
        ]
  }
}

// ========== Backend Container App Service ========== //
// WAF best practices for container apps: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-container-apps
// PSRule for Container App: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#container-app
var containerAppResourceName = 'ca-${solutionSuffix}'
module containerApp 'br/public:avm/res/app/container-app:0.18.1' = {
  name: take('avm.res.app.container-app.${containerAppResourceName}', 64)
  params: {
    name: containerAppResourceName
    tags: tags
    location: location
    enableTelemetry: enableTelemetry
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    managedIdentities: { userAssignedResourceIds: [userAssignedIdentity.outputs.resourceId] }
    ingressTargetPort: 8000
    ingressExternal: true
    activeRevisionsMode: 'Single'
    corsPolicy: {
      allowedOrigins: [
        'https://${webSiteResourceName}.azurewebsites.net'
        'http://${webSiteResourceName}.azurewebsites.net'
      ]
      allowedMethods:[
        'GET'
        'POST'
        'PUT'
        'DELETE'
        'OPTIONS'
      ]
    }
    // WAF aligned configuration for Scalability
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 1
      minReplicas: enableScalability ? 1 : 1
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
        image: '${backendContainerRegistryHostname}/${backendContainerImageName}:${backendContainerImageTag}'
        resources: {
          cpu: '2.0'
          memory: '4.0Gi'
        }
        env: [
          {
            name: 'COSMOSDB_ENDPOINT'
            value: 'https://${cosmosDbResourceName}.documents.azure.com:443/'
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
            value: 'https://${aiFoundryAiServicesResourceName}.openai.azure.com/'
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
            value: azureopenaiVersion
          }
          {
            name: 'APPLICATIONINSIGHTS_INSTRUMENTATION_KEY'
            value: enableMonitoring ? applicationInsights!.outputs.instrumentationKey : ''
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: enableMonitoring ? applicationInsights!.outputs.connectionString : ''
          }
          {
            name: 'AZURE_AI_SUBSCRIPTION_ID'
            value: aiFoundryAiServicesSubscriptionId
          }
          {
            name: 'AZURE_AI_RESOURCE_GROUP'
            value: aiFoundryAiServicesResourceGroupName
          }
          {
            name: 'AZURE_AI_PROJECT_NAME'
            value: aiFoundryAiProjectName
          }
          {
            name: 'FRONTEND_SITE_NAME'
            value: 'https://${webSiteResourceName}.azurewebsites.net'
          }
          {
            name: 'AZURE_AI_AGENT_ENDPOINT'
            value: aiFoundryAiProjectEndpoint
          }
          {
            name: 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
            value: aiFoundryAiServicesModelDeployment.name
          }
          {
            name: 'APP_ENV'
            value: 'Prod'
          }
          {
            name: 'AZURE_AI_SEARCH_CONNECTION_NAME'
            value: aiSearchConnectionName
          }
          {
            name: 'AZURE_AI_SEARCH_INDEX_NAME'
            value: aiSearchIndexName
          }
          {
            name: 'AZURE_AI_SEARCH_ENDPOINT'
            value: searchService.outputs.endpoint
          }
          {
            name: 'AZURE_COGNITIVE_SERVICES'
            value: 'https://cognitiveservices.azure.com/.default' 
          }
          {
            name: 'AZURE_BING_CONNECTION_NAME'
            value: 'binggrnd' 
          }
          {
            name: 'BING_CONNECTION_NAME'
            value: 'binggrnd' 
          } 
          {
            name: 'REASONING_MODEL_NAME'
            value: aiFoundryAiServicesReasoningModelDeployment.name
          }
          {
            name: 'MCP_SERVER_ENDPOINT'
            value: 'https://${containerAppMcp.outputs.fqdn}/mcp'
          }
          {
            name: 'MCP_SERVER_NAME'
            value: 'MacaeMcpServer' 
          }
          {
            name: 'MCP_SERVER_DESCRIPTION'
            value: 'MCP server with greeting, HR, and planning tools' 
          }
          {
            name: 'AZURE_TENANT_ID'
            value: tenant().tenantId
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: userAssignedIdentity!.outputs.clientId
          }
          {
            name: 'SUPPORTED_MODELS'
            value: '["o3","o4-mini","gpt-4.1","gpt-4.1-mini"]' 
          } 
          {
            name: 'AZURE_AI_SEARCH_API_KEY'
            secretRef: 'azure-ai-search-api-key'
          } 
          {
            name: 'AZURE_STORAGE_BLOB_URL'
            value: avmStorageAccount.outputs.serviceEndpoints.blob
          }
          {
            name: 'AZURE_STORAGE_CONTAINER_NAME'
            value: storageContainerName
          }
          {
            name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
            value: aiFoundryAiServicesModelDeployment.name
          }
        ]
        
      }
    ]
    secrets: [
      {
        name: 'azure-ai-search-api-key'
        keyVaultUrl: keyvault.outputs.secrets[0].uriWithVersion
        identity: userAssignedIdentity.outputs.resourceId
      }
    ]
  }
}

// ========== MCP Container App Service ========== //
// WAF best practices for container apps: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-container-apps
// PSRule for Container App: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#container-app
var containerAppMcpResourceName  = 'ca-mcp-${solutionSuffix}'
module containerAppMcp 'br/public:avm/res/app/container-app:0.18.1' = {
  name: take('avm.res.app.container-app.${containerAppMcpResourceName}', 64)
  params: {
    name: containerAppMcpResourceName
    tags: tags
    location: location
    enableTelemetry: enableTelemetry
    environmentResourceId: containerAppEnvironment.outputs.resourceId
    managedIdentities: { userAssignedResourceIds: [userAssignedIdentity.outputs.resourceId] }
    ingressTargetPort: 9000
    ingressExternal: true
    activeRevisionsMode: 'Single'
    corsPolicy: {
      allowedOrigins: [
        'https://${webSiteResourceName}.azurewebsites.net'
        'http://${webSiteResourceName}.azurewebsites.net'
      ]
    }
    // WAF aligned configuration for Scalability
    scaleSettings: {
      maxReplicas: enableScalability ? 3 : 1
      minReplicas: enableScalability ? 1 : 1
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
        name: 'mcp'
        image: '${MCPContainerRegistryHostname}/${MCPContainerImageName}:${MCPContainerImageTag}'
        resources: {
          cpu: '2.0'
          memory: '4.0Gi'
        }
        env: [
          {
            name: 'HOST'
            value: '0.0.0.0'
          }
          {
            name: 'PORT'
            value: '9000'
          }
          {
            name: 'DEBUG'
            value: 'false'
          }
          {
            name: 'SERVER_NAME'
            value: 'MacaeMcpServer'
          }
          {
            name: 'ENABLE_AUTH'
            value: 'false'
          }
          {
            name: 'TENANT_ID'
            value: tenant().tenantId
          }
          {
            name: 'CLIENT_ID'
            value: userAssignedIdentity!.outputs.clientId
          }
          {
            name: 'JWKS_URI'
            value: 'https://login.microsoftonline.com/${tenant().tenantId}/discovery/v2.0/keys'
          }
          {
            name: 'ISSUER'
            value: 'https://sts.windows.net/${tenant().tenantId}/'
          }
          {
            name: 'AUDIENCE'
            value: 'api://${userAssignedIdentity!.outputs.clientId}'
          }
          {
            name: 'DATASET_PATH'
            value: './datasets'
          }
        ]
      }
    ]
  }
}

// ========== Frontend server farm ========== //
// WAF best practices for Web Application Services: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/app-service-web-apps
// PSRule for Web Server Farm: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#app-service
var webServerFarmResourceName = 'asp-${solutionSuffix}'
module webServerFarm 'br/public:avm/res/web/serverfarm:0.5.0' = {
  name: take('avm.res.web.serverfarm.${webServerFarmResourceName}', 64)
  params: {
    name: webServerFarmResourceName
    tags: tags
    enableTelemetry: enableTelemetry
    location: location
    reserved: true
    kind: 'linux'
    // WAF aligned configuration for Monitoring
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    // WAF aligned configuration for Scalability
    skuName: enableScalability || enableRedundancy ? 'P1v3' : 'B3'
    skuCapacity: enableScalability ? 3 : 1
    // WAF aligned configuration for Redundancy
    zoneRedundant: enableRedundancy ? true : false
  }
}

// ========== Frontend web site ========== //
// WAF best practices for web app service: https://learn.microsoft.com/en-us/azure/well-architected/service-guides/app-service-web-apps
// PSRule for Web Server Farm: https://azure.github.io/PSRule.Rules.Azure/en/rules/resource/#app-service

//NOTE: AVM module adds 1 MB of overhead to the template. Keeping vanilla resource to save template size.
var webSiteResourceName = 'app-${solutionSuffix}'
module webSite 'modules/web-sites.bicep' = {
  name: take('module.web-sites.${webSiteResourceName}', 64)
  params: {
    name: webSiteResourceName
    tags: tags
    location: location
    kind: 'app,linux,container'
    serverFarmResourceId: webServerFarm.?outputs.resourceId
    siteConfig: {
      linuxFxVersion: 'DOCKER|${frontendContainerRegistryHostname}/${frontendContainerImageName}:${frontendContainerImageTag}'
      minTlsVersion: '1.2'
    }
    configs: [
      {
        name: 'appsettings'
        properties: {
          SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
          DOCKER_REGISTRY_SERVER_URL: 'https://${frontendContainerRegistryHostname}'
          WEBSITES_PORT: '3000'
          WEBSITES_CONTAINER_START_TIME_LIMIT: '1800' // 30 minutes, adjust as needed
          BACKEND_API_URL: 'https://${containerApp.outputs.fqdn}'
          AUTH_ENABLED: 'false'
        }
        // WAF aligned configuration for Monitoring
        applicationInsightResourceId: enableMonitoring ? applicationInsights!.outputs.resourceId : null
      }
    ]
    diagnosticSettings: enableMonitoring ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] : null
    // WAF aligned configuration for Private Networking
    vnetRouteAllEnabled: enablePrivateNetworking ? true : false
    vnetImagePullEnabled: enablePrivateNetworking ? true : false
    virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webserverfarmSubnetResourceId : null
    publicNetworkAccess: 'Enabled' // Always enabling the public network access for Web App
    e2eEncryptionEnabled: true
  }
}


// ========== Storage Account ========== //

var storageAccountName = replace('st${solutionSuffix}', '-', '')
param storageContainerName string = 'sample-dataset'
module avmStorageAccount 'br/public:avm/res/storage/storage-account:0.20.0' = {
  name: take('avm.res.storage.storage-account.${storageAccountName}', 64)
  params: {
    name: storageAccountName
    location: location
    managedIdentities: { systemAssigned: true }
    minimumTlsVersion: 'TLS1_2'
    enableTelemetry: enableTelemetry
    tags: tags
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true

    roleAssignments: [
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: deployingUserPrincipalId
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalType: deployerPrincipalType
      }
    ]

    // WAF aligned networking
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: enablePrivateNetworking  ? 'Deny' : 'Allow'
    }
    allowBlobPublicAccess: false
    publicNetworkAccess: enablePrivateNetworking  ? 'Disabled' : 'Enabled'

    // Private endpoints for blob
    privateEndpoints: enablePrivateNetworking 
      ? [
          {
            name: 'pep-blob-${solutionSuffix}'
            customNetworkInterfaceName: 'nic-blob-${solutionSuffix}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [
                {
                  name: 'storage-dns-zone-group-blob'
                  privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.blob]!.outputs.resourceId
                }
              ]
            }
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
            service: 'blob'
          }
        ]
      : []
    blobServices: {
      automaticSnapshotPolicyEnabled: true
      containerDeleteRetentionPolicyDays: 10
      containerDeleteRetentionPolicyEnabled: true
      containers: [
        {
          name: storageContainerName
          publicAccess: 'None'
        }
      ]
      deleteRetentionPolicyDays: 9
      deleteRetentionPolicyEnabled: true
      lastAccessTimeTrackingPolicyEnabled: true
    }
  }
}

// ========== Search Service ========== //

var searchServiceName = 'srch-${solutionSuffix}'
var aiSearchIndexName = 'sample-dataset-index'
module searchService 'br/public:avm/res/search/search-service:0.11.1' = {
  name: take('avm.res.search.search-service.${solutionSuffix}', 64)
  params: {
    name: searchServiceName
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: false
    hostingMode: 'default'
    managedIdentities: {
      systemAssigned: true
    }

    // Enabled the Public access because other services are not able to connect with search search AVM module when public access is disabled

    // publicNetworkAccess: enablePrivateNetworking  ? 'Disabled' : 'Enabled'
    publicNetworkAccess: 'Enabled'
    networkRuleSet: {
      bypass: 'AzureServices'
    }
    partitionCount: 1
    replicaCount: 1
    sku: enableScalability ? 'standard' : 'basic'
    tags: tags
    roleAssignments: [
      {
        principalId: userAssignedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Search Index Data Contributor'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: deployingUserPrincipalId
        roleDefinitionIdOrName: 'Search Index Data Contributor'
        principalType: deployerPrincipalType
      }
      {
        principalId: aiFoundryAiProjectPrincipalId
        roleDefinitionIdOrName: 'Search Index Data Reader'
        principalType: 'ServicePrincipal'
      }
      {
        principalId: aiFoundryAiProjectPrincipalId
        roleDefinitionIdOrName: 'Search Service Contributor'
        principalType: 'ServicePrincipal'
      }
    ]

    //Removing the Private endpoints as we are facing the issue with connecting to search service while comminicating with agents

    privateEndpoints:[]
    // privateEndpoints: enablePrivateNetworking 
    //   ? [
    //       {
    //         name: 'pep-search-${solutionSuffix}'
    //         customNetworkInterfaceName: 'nic-search-${solutionSuffix}'
    //         privateDnsZoneGroup: {
    //           privateDnsZoneGroupConfigs: [
    //             {
    //               privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.search]!.outputs.resourceId
    //             }
    //           ]
    //         }
    //         subnetResourceId: virtualNetwork!.outputs.subnetResourceIds[0]
    //         service: 'searchService'
    //       }
    //     ]
    //   : []
  }
}

// ========== Search Service - AI Project Connection ========== //

var aiSearchConnectionName = 'aifp-srch-connection-${solutionSuffix}'
module aiSearchFoundryConnection 'modules/aifp-connections.bicep' = {
  name: take('aifp-srch-connection.${solutionSuffix}', 64)
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  params: {
    aiFoundryProjectName: aiFoundryAiProjectName
    aiFoundryName: aiFoundryAiServicesResourceName
    aifSearchConnectionName: aiSearchConnectionName
    searchServiceResourceId: searchService.outputs.resourceId
    searchServiceLocation: searchService.outputs.location
    searchServiceName: searchService.outputs.name
    searchApiKey: searchService.outputs.primaryKey
  }
  dependsOn: [
    aiFoundryAiServices
  ]
}


// ========== KeyVault ========== //
var keyVaultName = 'kv-${solutionSuffix}'
module keyvault 'br/public:avm/res/key-vault/vault:0.12.1' = {
  name: take('avm.res.key-vault.vault.${keyVaultName}', 64)
  params: {
    name: keyVaultName
    location: location
    tags: tags
    sku: enableScalability ? 'premium' : 'standard'
    publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
    enableVaultForDeployment: true
    enableVaultForDiskEncryption: true
    enableVaultForTemplateDeployment: true
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    diagnosticSettings: enableMonitoring 
      ? [{ workspaceResourceId: logAnalyticsWorkspaceResourceId }] 
      : []
    // WAF aligned configuration for Private Networking
    privateEndpoints: enablePrivateNetworking
      ? [
          {
            name: 'pep-${keyVaultName}'
            customNetworkInterfaceName: 'nic-${keyVaultName}'
            privateDnsZoneGroup: {
              privateDnsZoneGroupConfigs: [{ privateDnsZoneResourceId: avmPrivateDnsZones[dnsZoneIndex.keyVault]!.outputs.resourceId }]
            }
            service: 'vault'
            subnetResourceId: virtualNetwork!.outputs.backendSubnetResourceId
          }
        ]
      : []
    // WAF aligned configuration for Role-based Access Control
    roleAssignments: [
      {
         principalId: userAssignedIdentity.outputs.principalId
         principalType: 'ServicePrincipal'
         roleDefinitionIdOrName: 'Key Vault Administrator'
      }
    ]
    secrets: [
      {
        name: 'AzureAISearchAPIKey'
        value: searchService.outputs.primaryKey
      }
    ]
    enableTelemetry: enableTelemetry
  }
}

// ============ //
// Outputs      //
// ============ //

@description('The resource group the resources were deployed into.')
output resourceGroupName string = resourceGroup().name

@description('The default url of the website to connect to the Multi-Agent Custom Automation Engine solution.')
output webSiteDefaultHostname string = webSite.outputs.defaultHostname

output AZURE_STORAGE_BLOB_URL string = avmStorageAccount.outputs.serviceEndpoints.blob
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccountName
output AZURE_STORAGE_CONTAINER_NAME string = storageContainerName
output AZURE_AI_SEARCH_ENDPOINT string = searchService.outputs.endpoint
output AZURE_AI_SEARCH_NAME string = searchService.outputs.name
output AZURE_AI_SEARCH_INDEX_NAME string = aiSearchIndexName

output COSMOSDB_ENDPOINT string = 'https://${cosmosDbResourceName}.documents.azure.com:443/'
output COSMOSDB_DATABASE string = cosmosDbDatabaseName
output COSMOSDB_CONTAINER string = cosmosDbDatabaseMemoryContainerName
output AZURE_OPENAI_ENDPOINT string = 'https://${aiFoundryAiServicesResourceName}.openai.azure.com/'
output AZURE_OPENAI_MODEL_NAME string = aiFoundryAiServicesModelDeployment.name
output AZURE_OPENAI_DEPLOYMENT_NAME string = aiFoundryAiServicesModelDeployment.name
output AZURE_OPENAI_API_VERSION string = azureopenaiVersion
// output APPLICATIONINSIGHTS_INSTRUMENTATION_KEY string = applicationInsights.outputs.instrumentationKey
// output AZURE_AI_PROJECT_ENDPOINT string = aiFoundryAiServices.outputs.aiProjectInfo.apiEndpoint
output AZURE_AI_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_AI_RESOURCE_GROUP string = resourceGroup().name
output AZURE_AI_PROJECT_NAME string = aiFoundryAiProjectName
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = aiFoundryAiServicesModelDeployment.name
// output APPLICATIONINSIGHTS_CONNECTION_STRING string = applicationInsights.outputs.connectionString
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = aiFoundryAiServicesModelDeployment.name
output AZURE_AI_AGENT_ENDPOINT string = aiFoundryAiProjectEndpoint
output APP_ENV string = 'Prod'
output AI_FOUNDRY_RESOURCE_ID string = !useExistingAiFoundryAiProject ? aiFoundryAiServices.outputs.resourceId : existingAiFoundryAiProjectResourceId
output COSMOSDB_ACCOUNT_NAME string = cosmosDbResourceName
output AZURE_SEARCH_ENDPOINT string =searchService.outputs.endpoint
output AZURE_CLIENT_ID string  = userAssignedIdentity!.outputs.clientId
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_AI_SEARCH_CONNECTION_NAME string  = aiSearchConnectionName
output AZURE_COGNITIVE_SERVICES string = 'https://cognitiveservices.azure.com/.default'
output REASONING_MODEL_NAME string = aiFoundryAiServicesReasoningModelDeployment.name
output MCP_SERVER_NAME string = 'MacaeMcpServer'
output MCP_SERVER_DESCRIPTION string = 'MCP server with greeting, HR, and planning tools'
output SUPPORTED_MODELS string = '["o3","o4-mini","gpt-4.1","gpt-4.1-mini"]'
output AZURE_AI_SEARCH_API_KEY string = '<Deployed-Search-ApiKey>'
output BACKEND_URL string = 'https://${containerApp.outputs.fqdn}'

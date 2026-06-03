// ============================================================================
// Module: Virtual Machine (Jumpbox)
// Description: AVM wrapper for Azure Virtual Machine
// AVM Module: avm/res/compute/virtual-machine
// ============================================================================

@description('Solution name suffix used to derive the resource name.')
param solutionName string

var name = 'vm-${solutionName}'

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('VM size.')
param vmSize string = 'Standard_D2s_v5'

@secure()
@description('Admin username for the VM.')
param adminUsername string

@secure()
@description('Admin password for the VM.')
param adminPassword string

@description('Resource ID of the subnet for the VM NIC.')
param subnetResourceId string

@description('Optional. Diagnostic settings for the resource.')
param diagnosticSettings array?

@description('OS type for the VM.')
param osType string = 'Windows'

@description('Availability zone for the VM.')
param availabilityZone int = 1

@description('Image reference for the VM.')
param imageReference object = {
  publisher: 'microsoft-dsvm'
  offer: 'dsvm-win-2022'
  sku: 'winserver-2022'
  version: 'latest'
}

@description('OS disk size in GB.')
param osDiskSizeGB int = 128

@description('Optional. Resource ID of the maintenance configuration.')
param maintenanceConfigurationResourceId string?

@description('Optional. Resource ID of the proximity placement group.')
param proximityPlacementGroupResourceId string?

@description('Optional. Monitoring agent extension configuration (data collection rule associations).')
param extensionMonitoringAgentConfig object?

// ============================================================================
// AVM Module Deployment
// ============================================================================
module virtualMachine 'br/public:avm/res/compute/virtual-machine:0.22.0' = {
  name: take('avm.res.compute.virtual-machine.${name}', 64)
  params: {
    name: name
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    computerName: take(name, 15)
    osType: osType
    vmSize: vmSize
    adminUsername: adminUsername
    adminPassword: adminPassword
    patchMode: 'AutomaticByPlatform'
    bypassPlatformSafetyChecksOnUserSchedule: true
    maintenanceConfigurationResourceId: maintenanceConfigurationResourceId
    enableAutomaticUpdates: true
    encryptionAtHost: true
    availabilityZone: availabilityZone
    proximityPlacementGroupResourceId: proximityPlacementGroupResourceId
    imageReference: imageReference
    osDisk: {
      name: 'osdisk-${name}'
      caching: 'ReadWrite'
      createOption: 'FromImage'
      deleteOption: 'Delete'
      diskSizeGB: osDiskSizeGB
      managedDisk: { storageAccountType: 'Premium_LRS' }
    }
    nicConfigurations: [
      {
        name: 'nic-${name}'
        tags: tags
        deleteOption: 'Delete'
        diagnosticSettings: diagnosticSettings
        ipConfigurations: [
          {
            name: '${name}-nic01-ipconfig01'
            subnetResourceId: subnetResourceId
            diagnosticSettings: diagnosticSettings
          }
        ]
      }
    ]
    extensionAadJoinConfig: { enabled: true, tags: tags, typeHandlerVersion: '1.0' }
    extensionAntiMalwareConfig: {
      enabled: true
      settings: {
        AntimalwareEnabled: 'true'
        Exclusions: {}
        RealtimeProtectionEnabled: 'true'
        ScheduledScanSettings: { day: '7', isEnabled: 'true', scanType: 'Quick', time: '120' }
      }
      tags: tags
    }
    extensionMonitoringAgentConfig: extensionMonitoringAgentConfig
    extensionNetworkWatcherAgentConfig: { enabled: true, tags: tags }
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('Resource ID of the virtual machine.')
output resourceId string = virtualMachine.outputs.resourceId

@description('Name of the virtual machine.')
output name string = virtualMachine.outputs.name

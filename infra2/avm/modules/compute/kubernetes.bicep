// ============================================================================
// Module: Azure Kubernetes Service (AKS)
// Description: AVM wrapper for Azure Kubernetes Service Managed Cluster
// AVM Module: avm/res/container-service/managed-cluster:0.13.0
// ============================================================================

@description('Solution name suffix used to derive the resource name.')
param solutionName string

var clusterName = 'aks-${solutionName}'

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Kubernetes version for the cluster.')
param kubernetesVersion string = '1.34'

@description('Agent pool configurations. Each entry requires name, vmSize, count, mode (System/User).')
param agentPools array = [
  {
    name: 'agentpool'
    vmSize: 'Standard_D4ds_v5'
    count: 2
    minCount: 1
    maxCount: 2
    enableAutoScaling: true
    osType: 'Linux'
    mode: 'System'
    type: 'VirtualMachineScaleSets'
    scaleSetEvictionPolicy: 'Delete'
    scaleSetPriority: 'Regular'
  }
]

@description('Enable Kubernetes RBAC.')
param enableRBAC bool = true

@description('Disable local accounts (enforce AAD-only).')
param disableLocalAccounts bool = false

@description('Network plugin for the cluster.')
@allowed(['azure', 'kubenet', 'none'])
param networkPlugin string = 'azure'

@description('Network policy for the cluster.')
@allowed(['azure', 'calico', ''])
param networkPolicy string = 'azure'

@description('DNS prefix for the cluster.')
param dnsPrefix string = ''

@description('SKU tier for the cluster.')
@allowed(['Free', 'Standard', 'Premium'])
param skuTier string = 'Standard'

@description('Service CIDR for Kubernetes services.')
param serviceCidr string = '10.20.0.0/16'

@description('DNS service IP (must be within serviceCidr).')
param dnsServiceIP string = '10.20.0.10'

// --- WAF: Networking ---
@description('Public network access setting.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Enable private cluster (API server not publicly accessible).')
param enablePrivateCluster bool = false

@description('Subnet resource ID for the agent pool (for VNet integration).')
param agentPoolSubnetId string = ''

// --- WAF: Auto Upgrade ---
@description('Auto-upgrade channel for the cluster.')
@allowed(['none', 'patch', 'rapid', 'stable', 'node-image'])
param autoUpgradeChannel string = 'stable'

// --- WAF: Monitoring ---
@description('Log Analytics workspace resource ID for monitoring.')
param logAnalyticsWorkspaceResourceId string = ''

@description('Enable Microsoft Defender for Containers.')
param enableDefender bool = false

@description('Diagnostic settings for monitoring.')
param diagnosticSettings array = []

// --- WAF: Role Assignments ---
@description('Role assignments for the cluster.')
param roleAssignments array = []

var effectiveDnsPrefix = !empty(dnsPrefix) ? dnsPrefix : clusterName
var enableMonitoring = !empty(logAnalyticsWorkspaceResourceId)

// Inject subnet into agent pools if provided
var effectiveAgentPools = [for pool in agentPools: union(pool, !empty(agentPoolSubnetId) ? { vnetSubnetResourceId: agentPoolSubnetId } : {})]

// ============================================================================
// AVM Module Deployment
// ============================================================================
module aksCluster 'br/public:avm/res/container-service/managed-cluster:0.13.0' = {
  name: take('avm.res.container-service.managed-cluster.${clusterName}', 64)
  params: {
    name: clusterName
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    kubernetesVersion: kubernetesVersion
    primaryAgentPoolProfiles: effectiveAgentPools
    enableRBAC: enableRBAC
    disableLocalAccounts: disableLocalAccounts
    networkPlugin: networkPlugin
    networkPolicy: networkPolicy
    dnsPrefix: effectiveDnsPrefix
    skuTier: skuTier
    serviceCidr: serviceCidr
    dnsServiceIP: dnsServiceIP
    publicNetworkAccess: publicNetworkAccess
    apiServerAccessProfile: {
      enablePrivateCluster: enablePrivateCluster
    }
    autoUpgradeProfile: {
      upgradeChannel: autoUpgradeChannel
      nodeOSUpgradeChannel: 'Unmanaged'
    }
    managedIdentities: { systemAssigned: true }
    omsAgentEnabled: enableMonitoring
    monitoringWorkspaceResourceId: enableMonitoring ? logAnalyticsWorkspaceResourceId : null
    diagnosticSettings: !empty(diagnosticSettings) ? diagnosticSettings : []
    securityProfile: enableDefender && enableMonitoring ? {
      defender: {
        logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
        securityMonitoring: {
          enabled: true
        }
      }
    } : {}
    roleAssignments: roleAssignments
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('Name of the AKS cluster.')
output name string = aksCluster.outputs.name

@description('Resource ID of the AKS cluster.')
output resourceId string = aksCluster.outputs.resourceId

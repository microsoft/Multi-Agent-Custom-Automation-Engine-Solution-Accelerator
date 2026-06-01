targetScope = 'resourceGroup'

@description('The name of the solution, used as the base for resource naming.')
param solutionName string

@description('The Azure region where the Key Vault will be deployed.')
param solutionLocation string

@description('Tags to apply to the resource.')
param tags object = {}

@description('The SKU tier for the Key Vault.')
param sku string = 'standard'

@description('Indicates whether Azure RBAC authorization is enabled for the Key Vault.')
param enableRbacAuthorization bool = true

@description('Indicates whether soft delete is enabled for the Key Vault.')
param enableSoftDelete bool = true

@description('The number of days that soft-deleted vaults are retained.')
param softDeleteRetentionInDays int = 90

@description('Indicates whether purge protection is enabled for the Key Vault.')
param enablePurgeProtection bool = true

@description('Controls public network access to the Key Vault.')
param publicNetworkAccess string = 'Enabled'

@description('The Microsoft Entra tenant ID for the Key Vault.')
param tenantId string = subscription().tenantId

var name = 'kv-${solutionName}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: solutionLocation
  tags: tags
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: sku
    }
    accessPolicies: []
    enableRbacAuthorization: enableRbacAuthorization
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: publicNetworkAccess == 'Disabled' ? 'Deny' : 'Allow'
    }
  }
}

@description('The name of the Key Vault.')
output name string = keyVault.name

@description('The URI of the Key Vault.')
output uri string = keyVault.properties.vaultUri

@description('The resource ID of the Key Vault.')
output id string = keyVault.id

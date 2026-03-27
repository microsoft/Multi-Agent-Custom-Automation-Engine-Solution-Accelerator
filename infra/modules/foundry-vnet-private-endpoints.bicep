// ========================================================================
// Private Endpoints in the Foundry VNet for Cross-Subscription Scenarios
// ========================================================================
// When AI Foundry agent compute runs in the Foundry VNet (cross-subscription),
// it needs direct private endpoint access to Cosmos DB, Storage, and Search.
// Cross-VNet PE access through peering alone may not satisfy the service-side
// "approved private endpoint" check. Creating local PEs in the Foundry VNet
// ensures agent compute traffic is recognized as coming from an approved PE.
//
// DNS zone groups point to the central DNS zones (in the deployment sub).
// Both PEs register A records; Azure handles multi-IP record sets correctly.
// ========================================================================

@description('Required. Azure region for the private endpoints.')
param location string

@description('Optional. Tags to apply to resources.')
param tags object = {}

@description('Required. Solution suffix for naming.')
param solutionSuffix string

@description('Required. The backend subnet resource ID in the Foundry VNet for hosting PEs.')
param backendSubnetResourceId string

// ---- Target service resource IDs (in the deployment subscription) ----
@description('Required. Resource ID of the Cosmos DB account.')
param cosmosDbAccountResourceId string

@description('Required. Resource ID of the Storage account.')
param storageAccountResourceId string

@description('Required. Resource ID of the Search service.')
param searchServiceResourceId string

// ---- Private DNS Zone IDs (in the deployment subscription) ----
@description('Required. Resource ID of the privatelink.documents.azure.com DNS zone.')
param cosmosDbDnsZoneId string

@description('Required. Resource ID of the privatelink.blob.core.windows.net DNS zone.')
param blobDnsZoneId string

@description('Required. Resource ID of the privatelink.search.windows.net DNS zone.')
param searchDnsZoneId string

// ========== Cosmos DB Private Endpoint ==========
resource cosmosDbPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pep-cosmos-foundry-${solutionSuffix}'
  location: location
  tags: tags
  properties: {
    customNetworkInterfaceName: 'nic-cosmos-foundry-${solutionSuffix}'
    subnet: {
      id: backendSubnetResourceId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-cosmos-foundry-${solutionSuffix}'
        properties: {
          privateLinkServiceId: cosmosDbAccountResourceId
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}

resource cosmosDbPeDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: cosmosDbPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos-dns-zone'
        properties: {
          privateDnsZoneId: cosmosDbDnsZoneId
        }
      }
    ]
  }
}

// ========== Storage (Blob) Private Endpoint ==========
resource storageBlobPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pep-blob-foundry-${solutionSuffix}'
  location: location
  tags: tags
  properties: {
    customNetworkInterfaceName: 'nic-blob-foundry-${solutionSuffix}'
    subnet: {
      id: backendSubnetResourceId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-blob-foundry-${solutionSuffix}'
        properties: {
          privateLinkServiceId: storageAccountResourceId
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

resource storageBlobPeDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: storageBlobPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob-dns-zone'
        properties: {
          privateDnsZoneId: blobDnsZoneId
        }
      }
    ]
  }
}

// ========== Search Service Private Endpoint ==========
resource searchPe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: 'pep-search-foundry-${solutionSuffix}'
  location: location
  tags: tags
  properties: {
    customNetworkInterfaceName: 'nic-search-foundry-${solutionSuffix}'
    subnet: {
      id: backendSubnetResourceId
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-search-foundry-${solutionSuffix}'
        properties: {
          privateLinkServiceId: searchServiceResourceId
          groupIds: [
            'searchService'
          ]
        }
      }
    ]
  }
}

resource searchPeDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: searchPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'search-dns-zone'
        properties: {
          privateDnsZoneId: searchDnsZoneId
        }
      }
    ]
  }
}

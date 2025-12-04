param aiServicesName string
param aiServicesId string
param location string
param subnetResourceId string
param cognitiveServicesDnsZoneId string
param openAiDnsZoneId string
param aiServicesDnsZoneId string
param tags object
param isPrivate bool

module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = if (isPrivate) {
  name: take('module.private-endpoint.${aiServicesName}', 64)
  params: {
    name: 'pep-${aiServicesName}'
    location: location
    subnetResourceId: subnetResourceId
    customNetworkInterfaceName: 'nic-${aiServicesName}'
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          name: 'ai-services-dns-zone-cognitiveservices'
          privateDnsZoneResourceId: cognitiveServicesDnsZoneId
        }
        {
          name: 'ai-services-dns-zone-openai'
          privateDnsZoneResourceId: openAiDnsZoneId
        }
        {
          name: 'ai-services-dns-zone-aiservices'
          privateDnsZoneResourceId: aiServicesDnsZoneId
        }
      ]
    }
    privateLinkServiceConnections: [
      {
        name: 'pep-${aiServicesName}'
        properties: {
          groupIds: ['account']
          privateLinkServiceId: aiServicesId
        }
      }
    ]
    tags: tags
  }
}
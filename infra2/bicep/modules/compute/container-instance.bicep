targetScope = 'resourceGroup'

@description('The name of the Container Instance group.')
param name string

@description('The Azure region where the Container Instance group will be deployed.')
param solutionLocation string

@description('Tags to apply to the resource.')
param tags object = {}

@description('The containers to deploy in the container group.')
param containers array

@description('The operating system type for the container group.')
param osType string = 'Linux'

@description('The restart policy for the container group.')
param restartPolicy string = 'OnFailure'

@description('The managed identity type assigned to the container group.')
param identityType string = 'None'

@description('The user-assigned identities to associate with the container group when applicable.')
param userAssignedIdentities object = {}

@description('The IP address type for the container group.')
param ipAddressType string = 'Public'

@description('Image registry credentials for pulling private images.')
param imageRegistryCredentials array = []

var containerGroupIdentity = identityType == 'None' ? null : {
  type: identityType
  userAssignedIdentities: contains(identityType, 'UserAssigned') ? userAssignedIdentities : null
}

var firstContainerPorts = length(containers) > 0 ? (containers[0].?properties.?ports ?? []) : []

var ipAddressPorts = [for port in firstContainerPorts: {
  port: port.port
  protocol: port.?protocol ?? 'TCP'
}]

resource containerGroup 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: name
  location: solutionLocation
  tags: tags
  identity: containerGroupIdentity
  properties: {
    osType: osType
    restartPolicy: restartPolicy
    containers: containers
    imageRegistryCredentials: imageRegistryCredentials
    ipAddress: ipAddressType == 'Public' ? {
      type: 'Public'
      ports: ipAddressPorts
    } : null
  }
}

@description('The name of the Container Instance group.')
output name string = containerGroup.name

@description('The resource ID of the Container Instance group.')
output id string = containerGroup.id

@description('The public IP address assigned to the container group, if available.')
output ipAddress string = ipAddressType == 'Public' ? containerGroup.properties.ipAddress.ip : ''

@description('The Azure region where the SQL Server and database will be deployed.')
param solutionLocation string

@description('The name of the SQL Server.')
param serverName string

@description('The name of the SQL database.')
param sqlDBName string

@description('The principal ID of the deployer for SQL Server admin access.')
param deployerPrincipalId string

var location = solutionLocation

resource sqlServer 'Microsoft.Sql/servers@2025-01-01' = {
  name: serverName
  location: location
  kind: 'v12.0'
  properties: {
    publicNetworkAccess: 'Enabled'
    version: '12.0'
    restrictOutboundNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
    administrators: {
      login: deployerPrincipalId
      sid: deployerPrincipalId
      tenantId: subscription().tenantId
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
    }
  }
}

resource firewallRule 'Microsoft.Sql/servers/firewallRules@2025-01-01' = {
  name: 'AllowSpecificRange'
  parent: sqlServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '255.255.255.255'
  }
}

resource AllowAllWindowsAzureIps 'Microsoft.Sql/servers/firewallRules@2025-01-01' = {
  name: 'AllowAllWindowsAzureIps'
  parent: sqlServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource sqlDB 'Microsoft.Sql/servers/databases@2025-01-01' = {
  parent: sqlServer
  name: sqlDBName
  location: location
  sku: {
    name: 'GP_S_Gen5'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 2
  }
  kind: 'v12.0,user,vcore,serverless'
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    autoPauseDelay: 60
    minCapacity: 1
    readScale: 'Disabled'
    zoneRedundant: false
  }
}

@description('The fully qualified domain name of the SQL Server.')
output sqlServerName string = '${serverName}.database.windows.net'

@description('The name of the SQL database.')
output sqlDbName string = sqlDBName

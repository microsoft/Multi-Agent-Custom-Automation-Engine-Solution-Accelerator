// ============== //
//   Parameters   //
// ============== //

@description('Required. The name of the Key Vault to set the ecrets in.')
param keyVaultName string

import { secretToSetType } from 'br/public:avm/utl/types/avm-common-types:0.5.1'
@description('Required. The secrets to set in the Key Vault.')
param secretsToSet secretToSetType[]

// ============= //
//   Resources   //
// ============= //

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource secrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [
  for secret in secretsToSet: {
    name: secret.name
    parent: keyVault
    properties: {
      value: secret.value
    }
  }
]

// =========== //
//   Outputs   //
// =========== //

import { secretSetOutputType } from 'br/public:avm/utl/types/avm-common-types:0.5.1'
@description('The references to the secrets exported to the provided Key Vault.')
output secretsSet secretSetOutputType[] = [
  #disable-next-line outputs-should-not-contain-secrets // Only returning the references, not a secret value
  for index in range(0, length(secretsToSet ?? [])): {
    secretResourceId: secrets[index].id
    secretUri: secrets[index].properties.secretUri
    secretUriWithVersion: secrets[index].properties.secretUriWithVersion
  }
]

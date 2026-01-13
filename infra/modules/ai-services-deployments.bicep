@description('Required. The name of Cognitive Services account.')
param name string

@description('Optional. SKU of the Cognitive Services account. Use \'Get-AzCognitiveServicesAccountSku\' to determine a valid combinations of \'kind\' and \'SKU\' for your Azure region.')
@allowed([
  'C2'
  'C3'
  'C4'
  'F0'
  'F1'
  'S'
  'S0'
  'S1'
  'S10'
  'S2'
  'S3'
  'S4'
  'S5'
  'S6'
  'S7'
  'S8'
  'S9'
])
param sku string = 'S0'

import { deploymentType } from 'br:mcr.microsoft.com/bicep/avm/res/cognitive-services/account:0.13.2'
@description('Optional. Array of deployments about cognitive service accounts to create.')
param deployments deploymentType[]?

import { roleAssignmentType } from 'br/public:avm/utl/types/avm-common-types:0.5.1'
@description('Optional. Array of role assignments to create.')
param roleAssignments roleAssignmentType[]?

var builtInRoleNames = {
  'Cognitive Services Contributor': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
  )
  'Cognitive Services Custom Vision Contributor': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'c1ff6cc2-c111-46fe-8896-e0ef812ad9f3'
  )
  'Cognitive Services Custom Vision Deployment': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '5c4089e1-6d96-4d2f-b296-c1bc7137275f'
  )
  'Cognitive Services Custom Vision Labeler': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '88424f51-ebe7-446f-bc41-7fa16989e96c'
  )
  'Cognitive Services Custom Vision Reader': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '93586559-c37d-4a6b-ba08-b9f0940c2d73'
  )
  'Cognitive Services Custom Vision Trainer': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '0a5ae4ab-0d65-4eeb-be61-29fc9b54394b'
  )
  'Cognitive Services Data Reader (Preview)': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'b59867f0-fa02-499b-be73-45a86b5b3e1c'
  )
  'Cognitive Services Face Recognizer': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '9894cab4-e18a-44aa-828b-cb588cd6f2d7'
  )
  'Cognitive Services Immersive Reader User': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'b2de6794-95db-4659-8781-7e080d3f2b9d'
  )
  'Cognitive Services Language Owner': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'f07febfe-79bc-46b1-8b37-790e26e6e498'
  )
  'Cognitive Services Language Reader': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '7628b7b8-a8b2-4cdc-b46f-e9b35248918e'
  )
  'Cognitive Services Language Writer': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'f2310ca1-dc64-4889-bb49-c8e0fa3d47a8'
  )
  'Cognitive Services LUIS Owner': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'f72c8140-2111-481c-87ff-72b910f6e3f8'
  )
  'Cognitive Services LUIS Reader': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '18e81cdc-4e98-4e29-a639-e7d10c5a6226'
  )
  'Cognitive Services LUIS Writer': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '6322a993-d5c9-4bed-b113-e49bbea25b27'
  )
  'Cognitive Services Metrics Advisor Administrator': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'cb43c632-a144-4ec5-977c-e80c4affc34a'
  )
  'Cognitive Services Metrics Advisor User': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '3b20f47b-3825-43cb-8114-4bd2201156a8'
  )
  'Cognitive Services OpenAI Contributor': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'a001fd3d-188f-4b5d-821b-7da978bf7442'
  )
  'Cognitive Services OpenAI User': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  )
  'Cognitive Services QnA Maker Editor': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'f4cc2bf9-21be-47a1-bdf1-5c5804381025'
  )
  'Cognitive Services QnA Maker Reader': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '466ccd10-b268-4a11-b098-b4849f024126'
  )
  'Cognitive Services Speech Contributor': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '0e75ca1e-0464-4b4d-8b93-68208a576181'
  )
  'Cognitive Services Speech User': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'f2dc8367-1007-4938-bd23-fe263f013447'
  )
  'Cognitive Services User': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'a97b65f3-24c7-4388-baec-2e87135dc908'
  )
  'Azure AI Developer': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '64702f94-c441-49e6-a78b-ef80e0188fee'
  )
  Contributor: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  Owner: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8e3af657-a8ff-443c-a75c-2fe8c4bcb635')
  Reader: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
  'Role Based Access Control Administrator': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    'f58310d9-a9f6-439a-9e8d-f62e7b41a168'
  )
  'User Access Administrator': subscriptionResourceId(
    'Microsoft.Authorization/roleDefinitions',
    '18d7d88d-d35e-4fb5-a5c3-7773c20a72d9'
  )
}

var formattedRoleAssignments = [
  for (roleAssignment, index) in (roleAssignments ?? []): union(roleAssignment, {
    roleDefinitionId: builtInRoleNames[?roleAssignment.roleDefinitionIdOrName] ?? (contains(
        roleAssignment.roleDefinitionIdOrName,
        '/providers/Microsoft.Authorization/roleDefinitions/'
      )
      ? roleAssignment.roleDefinitionIdOrName
      : subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAssignment.roleDefinitionIdOrName))
  })
]

resource cognitiveService 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: name
}

@batchSize(1)
resource cognitiveService_deployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [
  for (deployment, index) in (deployments ?? []): {
    parent: cognitiveService
    name: deployment.?name ?? '${name}-deployments'
    properties: {
      model: deployment.model
      raiPolicyName: deployment.?raiPolicyName
      versionUpgradeOption: deployment.?versionUpgradeOption
    }
    sku: deployment.?sku ?? {
      name: sku
      capacity: sku.?capacity
      tier: sku.?tier
      size: sku.?size
      family: sku.?family
    }
  }
]

resource cognitiveService_roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for (roleAssignment, index) in (formattedRoleAssignments ?? []): {
    name: roleAssignment.?name ?? guid(cognitiveService.id, roleAssignment.principalId, roleAssignment.roleDefinitionId)
    properties: {
      roleDefinitionId: roleAssignment.roleDefinitionId
      principalId: roleAssignment.principalId
      description: roleAssignment.?description
      principalType: roleAssignment.?principalType
      condition: roleAssignment.?condition
      conditionVersion: !empty(roleAssignment.?condition) ? (roleAssignment.?conditionVersion ?? '2.0') : null // Must only be set if condtion is set
      delegatedManagedIdentityResourceId: roleAssignment.?delegatedManagedIdentityResourceId
    }
    scope: cognitiveService
  }
]

// ============================================================================
// main_custom.bicep
// Description: Bicep file for deploying the Multi-Agent Custom Automation Engine solution with custom code.
// ============================================================================
targetScope = 'resourceGroup'

metadata name = 'Multi-Agent Custom Automation Engine - Deployment Router'
metadata description = 'This is the bicep file used for deploying the Multi-Agent Custom Automation Engine solution with custom code.'

// ============================================================================
// Routing Parameter
// ============================================================================

@allowed(['bicep'])
@description('Required. Deployment flavor: bicep (vanilla Bicep)')
param deploymentFlavor string

// ============================================================================
// Parameters — Core
// ============================================================================

@description('Optional. A unique application/solution name for all resources in this deployment. This should be 3-16 characters long.')
@minLength(3)
@maxLength(16)
param solutionName string = 'macae'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources.')
param solutionUniqueText string = take(uniqueString(subscription().id, resourceGroup().name, solutionName), 5)

@metadata({
  azd: {
    type: 'location'
  }
})
@description('Required. Azure region for app, data, and monitoring resources.')
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

@allowed(['australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus', 'westus3', 'polandcentral', 'uaenorth'])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1, 150'
      'OpenAI.GlobalStandard.o4-mini, 50'
      'OpenAI.GlobalStandard.gpt4.1-mini, 50'
      'OpenAI.GlobalStandard.gpt-image-1.5, 5'
    ]
  }
})
@description('Required. Location for Azure AI Services and Azure AI Foundry resources.')
param azureAiServiceLocation string

// ============================================================================
// Parameters — AI
// ============================================================================

@description('Optional. Name of the default GPT model deployment.')
param gptModelName string = 'gpt-4.1-mini'

@description('Optional. Version of the default GPT model deployment.')
param gptModelVersion string = '2025-04-14'

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Deployment type for the default GPT model deployment.')
param deploymentType string = 'GlobalStandard'

@minValue(1)
@description('Optional. Capacity of the default GPT model deployment.')
param gptDeploymentCapacity int = 50

@description('Optional. Name of the RAI GPT model deployment.')
param gpt4_1ModelName string = 'gpt-4.1'

@description('Optional. Version of the RAI GPT model deployment.')
param gpt4_1ModelVersion string = '2025-04-14'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Deployment type for the RAI GPT model deployment.')
param gpt4_1ModelDeploymentType string = 'GlobalStandard'

@minValue(1)
@description('Optional. Capacity of the RAI GPT model deployment.')
param gpt4_1ModelCapacity int = 150

@minLength(1)
@description('Optional. Name of the GPT Reasoning model to deploy:')
param gptReasoningModelName string = 'o4-mini'

@description('Optional. Version of the GPT Reasoning model to deploy. Defaults to 2025-04-16.')
param gptReasoningModelVersion string = '2025-04-16'

@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. Deployment type for the reasoning model deployment.')
param gptReasoningModelDeploymentType string = 'GlobalStandard'

@minValue(1)
@description('Optional. Capacity of the reasoning model deployment.')
param gptReasoningModelCapacity int = 50

@minLength(1)
@description('Optional. Name of the image-generation model to deploy. Defaults to gpt-image-1.5.')
param gptImageModelName string = 'gpt-image-1.5'

@description('Optional. Version of the image-generation model to deploy. Defaults to 2025-12-16.')
param gptImageModelVersion string = '2025-12-16'

@minLength(1)
@allowed([
  'Standard'
  'GlobalStandard'
])
@description('Optional. GPT image model deployment type. Defaults to GlobalStandard.')
param gptImageModelDeploymentType string = 'GlobalStandard'

@description('Optional. gpt-image-1.5 deployment capacity (RPM). Defaults to 5 to support concurrent marketing-image generation across multiple sessions.')
param gptImageModelCapacity int = 5

@description('Optional. Version of the Azure OpenAI service to deploy. Defaults to 2024-12-01-preview.')
param azureOpenaiAPIVersion string = '2024-12-01-preview'

// ============================================================================
// Parameters — Compute
// ============================================================================

@description('Optional. The Container Registry hostname where the docker images for the backend are located.')
param backendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the backend.')
param backendContainerImageName string = 'macaebackend'

@description('Optional. The Container Image Tag to deploy on the backend.')
param backendContainerImageTag string = 'latest_v4'

@description('Optional. The Container Registry hostname where the docker images for the frontend are located.')
param frontendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the frontend.')
param frontendContainerImageName string = 'macaefrontend'

@description('Optional. The Container Image Tag to deploy on the frontend.')
param frontendContainerImageTag string = 'latest_v4'

@description('Optional. The Container Registry hostname where the docker images for the MCP are located.')
param MCPContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'

@description('Optional. The Container Image Name to deploy on the MCP.')
param MCPContainerImageName string = 'macaemcp'

@description('Optional. The Container Image Tag to deploy on the MCP.')
param MCPContainerImageTag string = 'latest_v4'

// ============================================================================
// Parameters — Existing Resources and Governance
// ============================================================================

@description('Optional. Resource ID of an existing Log Analytics Workspace.')
param existingLogAnalyticsWorkspaceId string = ''

@description('Optional. Resource ID of an existing AI Foundry project.')
param existingFoundryProjectResourceId string = ''

@description('Optional. Additional tags to apply to deployed resources.')
param tags object = {}

// ============================================================================
// Parameters — Data
// ============================================================================

@description('Optional. Blob container name for retail customer documents.')
param storageContainerNameRetailCustomer string = 'retail-dataset-customer'

@description('Optional. Blob container name for retail order documents.')
param storageContainerNameRetailOrder string = 'retail-dataset-order'

@description('Optional. Blob container name for RFP summary documents.')
param storageContainerNameRFPSummary string = 'rfp-summary-dataset'

@description('Optional. Blob container name for RFP risk documents.')
param storageContainerNameRFPRisk string = 'rfp-risk-dataset'

@description('Optional. Blob container name for RFP compliance documents.')
param storageContainerNameRFPCompliance string = 'rfp-compliance-dataset'

@description('Optional. Blob container name for contract summary documents.')
param storageContainerNameContractSummary string = 'contract-summary-dataset'

@description('Optional. Blob container name for contract risk documents.')
param storageContainerNameContractRisk string = 'contract-risk-dataset'

@description('Optional. Blob container name for contract compliance documents.')
param storageContainerNameContractCompliance string = 'contract-compliance-dataset'

// ============================================================================
// Module: Vanilla Bicep Deployment
// ============================================================================

module bicepDeployment './bicep/main.bicep' = {
  name: take('module.bicep.${solutionName}', 64)
  params: {
    solutionName: solutionName
    solutionUniqueText: solutionUniqueText
    location: location
    azureAiServiceLocation: azureAiServiceLocation
    gptModelName: gptModelName
    gptModelVersion: gptModelVersion
    deploymentType: deploymentType
    gptDeploymentCapacity: gptDeploymentCapacity
    gpt4_1ModelName: gpt4_1ModelName
    gpt4_1ModelVersion: gpt4_1ModelVersion
    gpt4_1ModelDeploymentType: gpt4_1ModelDeploymentType
    gpt4_1ModelCapacity: gpt4_1ModelCapacity
    gptReasoningModelName: gptReasoningModelName
    gptReasoningModelVersion: gptReasoningModelVersion
    gptReasoningModelDeploymentType: gptReasoningModelDeploymentType
    gptReasoningModelCapacity: gptReasoningModelCapacity
    gptImageModelName: gptImageModelName
    gptImageModelVersion: gptImageModelVersion
    gptImageModelDeploymentType: gptImageModelDeploymentType
    gptImageModelCapacity: gptImageModelCapacity
    azureOpenaiAPIVersion: azureOpenaiAPIVersion
    backendContainerRegistryHostname: backendContainerRegistryHostname
    backendContainerImageName: backendContainerImageName
    backendContainerImageTag: backendContainerImageTag
    frontendContainerRegistryHostname: frontendContainerRegistryHostname
    frontendContainerImageName: frontendContainerImageName
    frontendContainerImageTag: frontendContainerImageTag
    MCPContainerRegistryHostname: MCPContainerRegistryHostname
    MCPContainerImageName: MCPContainerImageName
    MCPContainerImageTag: MCPContainerImageTag
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    tags: tags
    storageContainerNameRetailCustomer: storageContainerNameRetailCustomer
    storageContainerNameRetailOrder: storageContainerNameRetailOrder
    storageContainerNameRFPSummary: storageContainerNameRFPSummary
    storageContainerNameRFPRisk: storageContainerNameRFPRisk
    storageContainerNameRFPCompliance: storageContainerNameRFPCompliance
    storageContainerNameContractSummary: storageContainerNameContractSummary
    storageContainerNameContractRisk: storageContainerNameContractRisk
    storageContainerNameContractCompliance: storageContainerNameContractCompliance
    isCustom: true
  }
}

// ============================================================================
// Outputs — Coalesced from whichever flavor was deployed
// ============================================================================

output resourceGroupName string = bicepDeployment!.outputs.resourceGroupName
output webSiteDefaultHostname string = bicepDeployment!.outputs.webSiteDefaultHostname
output AZURE_STORAGE_BLOB_URL string = bicepDeployment!.outputs.AZURE_STORAGE_BLOB_URL
output AZURE_STORAGE_ACCOUNT_NAME string = bicepDeployment!.outputs.AZURE_STORAGE_ACCOUNT_NAME
output AZURE_AI_SEARCH_ENDPOINT string = bicepDeployment!.outputs.AZURE_AI_SEARCH_ENDPOINT
output AZURE_AI_SEARCH_NAME string = bicepDeployment!.outputs.AZURE_AI_SEARCH_NAME
output COSMOSDB_ENDPOINT string = bicepDeployment!.outputs.COSMOSDB_ENDPOINT
output COSMOSDB_DATABASE string = bicepDeployment!.outputs.COSMOSDB_DATABASE
output COSMOSDB_CONTAINER string = bicepDeployment!.outputs.COSMOSDB_CONTAINER
output AZURE_OPENAI_ENDPOINT string = bicepDeployment!.outputs.AZURE_OPENAI_ENDPOINT
output AZURE_OPENAI_DEPLOYMENT_NAME string = bicepDeployment!.outputs.AZURE_OPENAI_DEPLOYMENT_NAME
output AZURE_OPENAI_RAI_DEPLOYMENT_NAME string = bicepDeployment!.outputs.AZURE_OPENAI_RAI_DEPLOYMENT_NAME
output AZURE_OPENAI_API_VERSION string = bicepDeployment!.outputs.AZURE_OPENAI_API_VERSION
output AZURE_AI_SUBSCRIPTION_ID string = bicepDeployment!.outputs.AZURE_AI_SUBSCRIPTION_ID
output AZURE_AI_RESOURCE_GROUP string = bicepDeployment!.outputs.AZURE_AI_RESOURCE_GROUP
output AZURE_AI_PROJECT_NAME string = bicepDeployment!.outputs.AZURE_AI_PROJECT_NAME
output APP_ENV string = bicepDeployment!.outputs.APP_ENV
output AI_FOUNDRY_RESOURCE_ID string = bicepDeployment!.outputs.AI_FOUNDRY_RESOURCE_ID
output COSMOSDB_ACCOUNT_NAME string = bicepDeployment!.outputs.COSMOSDB_ACCOUNT_NAME
output AZURE_SEARCH_ENDPOINT string = bicepDeployment!.outputs.AZURE_SEARCH_ENDPOINT
output AZURE_CLIENT_ID string = bicepDeployment!.outputs.AZURE_CLIENT_ID
output AZURE_TENANT_ID string = bicepDeployment!.outputs.AZURE_TENANT_ID
output AZURE_COGNITIVE_SERVICES string = bicepDeployment!.outputs.AZURE_COGNITIVE_SERVICES
output ORCHESTRATOR_MODEL_NAME string = bicepDeployment!.outputs.ORCHESTRATOR_MODEL_NAME
output MCP_SERVER_NAME string = bicepDeployment!.outputs.MCP_SERVER_NAME
output MCP_SERVER_DESCRIPTION string = bicepDeployment!.outputs.MCP_SERVER_DESCRIPTION
output SUPPORTED_MODELS string = bicepDeployment!.outputs.SUPPORTED_MODELS
output BACKEND_URL string = bicepDeployment!.outputs.BACKEND_URL
output AZURE_AI_PROJECT_ENDPOINT string = bicepDeployment!.outputs.AZURE_AI_PROJECT_ENDPOINT
output AZURE_AI_AGENT_ENDPOINT string = bicepDeployment!.outputs.AZURE_AI_AGENT_ENDPOINT
output AI_SERVICE_NAME string = bicepDeployment!.outputs.AI_SERVICE_NAME
output AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER
output AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER
output AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY
output AZURE_STORAGE_CONTAINER_NAME_RFP_RISK string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_RISK
output AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE string = bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE
output AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER
output AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER
output AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY
output AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK
output AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE string = bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE

output DEPLOYMENT_FLAVOR string = deploymentFlavor
output RESOURCE_GROUP_NAME string = resourceGroup().name

// Container Registry Outputs
output AZURE_CONTAINER_REGISTRY_ENDPOINT string? = bicepDeployment!.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT!
output AZURE_CONTAINER_REGISTRY_NAME string? = bicepDeployment!.outputs.AZURE_CONTAINER_REGISTRY_NAME!

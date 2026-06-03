// ============================================================================
// main.bicep — Deployment Router
// Description: Routes MACAE deployment to either the AVM or vanilla Bicep
//              orchestrator while preserving a unified parameter and output
//              contract.
// ============================================================================
targetScope = 'resourceGroup'

metadata name = 'Multi-Agent Custom Automation Engine - Deployment Router'
metadata description = 'Deployment router for the Multi-Agent Custom Automation Engine accelerator. Routes to either the AVM or vanilla Bicep orchestrator and preserves a unified deployment contract.'

// ============================================================================
// Routing Parameter
// ============================================================================

@allowed(['bicep', 'avm', 'avm-waf'])
@description('Required. Deployment flavor: bicep (vanilla Bicep), avm (AVM non-WAF), or avm-waf (AVM WAF-aligned).')
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
  'westus3'
])
param location string

@allowed(['australiaeast', 'eastus2', 'francecentral', 'japaneast', 'norwayeast', 'swedencentral', 'uksouth', 'westus', 'westus3'])
@metadata({
  azd: {
    type: 'location'
    usageName: [
      'OpenAI.GlobalStandard.gpt4.1, 150'
      'OpenAI.GlobalStandard.o4-mini, 50'
      'OpenAI.GlobalStandard.gpt4.1-mini, 50'
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

@description('Optional. Version of the Azure AI Agent API version. Defaults to 2025-01-01-preview.')
param azureAiAgentAPIVersion string = '2025-01-01-preview'

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

@description('Optional. Enable or disable usage telemetry for this deployment.')
param enableTelemetry bool = true

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
// Parameters — AVM-WAF only
// ============================================================================

@description('Optional. Enable monitoring for applicable resources. Defaults to true when deploymentFlavor is avm-waf.')
param enableMonitoring bool = deploymentFlavor == 'avm-waf'

@description('Optional. Enable private networking for applicable resources. Defaults to true when deploymentFlavor is avm-waf.')
param enablePrivateNetworking bool = deploymentFlavor == 'avm-waf'

@description('Optional. Enable scalability for applicable resources. Defaults to true when deploymentFlavor is avm-waf.')
param enableScalability bool = deploymentFlavor == 'avm-waf'

@description('Optional. Enable redundancy for applicable resources. Defaults to true when deploymentFlavor is avm-waf.')
param enableRedundancy bool = deploymentFlavor == 'avm-waf'

@secure()
@description('Optional. The user name for the administrator account of the virtual machine. Applies only to AVM flavors.')
param vmAdminUsername string?

@secure()
@description('Optional. The password for the administrator account of the virtual machine. Applies only to AVM flavors.')
param vmAdminPassword string?

@description('Optional. The size of the virtual machine. Applies only to AVM flavors.')
param vmSize string = 'Standard_D2s_v5'

// ============================================================================
// Derived Variables
// ============================================================================

var isAvm = deploymentFlavor == 'avm' || deploymentFlavor == 'avm-waf'
var isBicep = deploymentFlavor == 'bicep'

// ============================================================================
// Telemetry
// ============================================================================

#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2025-04-01' = if (enableTelemetry) {
  name: '46d3xbcp.ptn.sa-multiagentcustauteng.router.${substring(uniqueString(deployment().name, location), 0, 4)}'
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        telemetry: {
          type: 'String'
          value: 'For more information, see https://aka.ms/avm/TelemetryInfo'
        }
      }
    }
  }
}

// ============================================================================
// Module: AVM Deployment
// ============================================================================

module avmDeployment './avm/main.bicep' = if (isAvm) {
  name: take('module.avm.${solutionName}', 64)
  params: {
    solutionName: solutionName
    solutionUniqueText: solutionUniqueText
    location: location
    tags: tags
    enableTelemetry: enableTelemetry
    azureAiServiceLocation: azureAiServiceLocation
    gptModelName: gptModelName
    gptModelVersion: gptModelVersion
    gpt4_1ModelName: gpt4_1ModelName
    gpt4_1ModelVersion: gpt4_1ModelVersion
    gptReasoningModelName: gptReasoningModelName
    gptReasoningModelVersion: gptReasoningModelVersion
    azureOpenaiAPIVersion: azureOpenaiAPIVersion
    azureAiAgentAPIVersion: azureAiAgentAPIVersion
    deploymentType: deploymentType
    gpt4_1ModelDeploymentType: gpt4_1ModelDeploymentType
    gptReasoningModelDeploymentType: gptReasoningModelDeploymentType
    gptDeploymentCapacity: gptDeploymentCapacity
    gpt4_1ModelCapacity: gpt4_1ModelCapacity
    gptReasoningModelCapacity: gptReasoningModelCapacity
    backendContainerRegistryHostname: backendContainerRegistryHostname
    backendContainerImageName: backendContainerImageName
    backendContainerImageTag: backendContainerImageTag
    frontendContainerRegistryHostname: frontendContainerRegistryHostname
    frontendContainerImageName: frontendContainerImageName
    frontendContainerImageTag: frontendContainerImageTag
    MCPContainerRegistryHostname: MCPContainerRegistryHostname
    MCPContainerImageName: MCPContainerImageName
    MCPContainerImageTag: MCPContainerImageTag
    enableMonitoring: enableMonitoring
    enableScalability: enableScalability
    enableRedundancy: enableRedundancy
    enablePrivateNetworking: enablePrivateNetworking
    vmAdminUsername: vmAdminUsername
    vmAdminPassword: vmAdminPassword
    vmSize: vmSize
    existingLogAnalyticsWorkspaceId: existingLogAnalyticsWorkspaceId
    existingFoundryProjectResourceId: existingFoundryProjectResourceId
    storageContainerNameRetailCustomer: storageContainerNameRetailCustomer
    storageContainerNameRetailOrder: storageContainerNameRetailOrder
    storageContainerNameRFPSummary: storageContainerNameRFPSummary
    storageContainerNameRFPRisk: storageContainerNameRFPRisk
    storageContainerNameRFPCompliance: storageContainerNameRFPCompliance
    storageContainerNameContractSummary: storageContainerNameContractSummary
    storageContainerNameContractRisk: storageContainerNameContractRisk
    storageContainerNameContractCompliance: storageContainerNameContractCompliance
  }
}

// ============================================================================
// Module: Vanilla Bicep Deployment
// ============================================================================

module bicepDeployment './bicep/main.bicep' = if (isBicep) {
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
    azureOpenaiAPIVersion: azureOpenaiAPIVersion
    azureAiAgentAPIVersion: azureAiAgentAPIVersion
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
    enableTelemetry: enableTelemetry
    tags: tags
    storageContainerNameRetailCustomer: storageContainerNameRetailCustomer
    storageContainerNameRetailOrder: storageContainerNameRetailOrder
    storageContainerNameRFPSummary: storageContainerNameRFPSummary
    storageContainerNameRFPRisk: storageContainerNameRFPRisk
    storageContainerNameRFPCompliance: storageContainerNameRFPCompliance
    storageContainerNameContractSummary: storageContainerNameContractSummary
    storageContainerNameContractRisk: storageContainerNameContractRisk
    storageContainerNameContractCompliance: storageContainerNameContractCompliance
  }
}

// ============================================================================
// Outputs — Coalesced from whichever flavor was deployed
// ============================================================================

output resourceGroupName string = isAvm ? avmDeployment!.outputs.resourceGroupName : bicepDeployment!.outputs.resourceGroupName
output webSiteDefaultHostname string = isAvm ? avmDeployment!.outputs.webSiteDefaultHostname : bicepDeployment!.outputs.webSiteDefaultHostname
output AZURE_STORAGE_BLOB_URL string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_BLOB_URL : bicepDeployment!.outputs.AZURE_STORAGE_BLOB_URL
output AZURE_STORAGE_ACCOUNT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_ACCOUNT_NAME : bicepDeployment!.outputs.AZURE_STORAGE_ACCOUNT_NAME
output AZURE_AI_SEARCH_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_ENDPOINT : bicepDeployment!.outputs.AZURE_AI_SEARCH_ENDPOINT
output AZURE_AI_SEARCH_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_NAME : bicepDeployment!.outputs.AZURE_AI_SEARCH_NAME
output COSMOSDB_ENDPOINT string = isAvm ? avmDeployment!.outputs.COSMOSDB_ENDPOINT : bicepDeployment!.outputs.COSMOSDB_ENDPOINT
output COSMOSDB_DATABASE string = isAvm ? avmDeployment!.outputs.COSMOSDB_DATABASE : bicepDeployment!.outputs.COSMOSDB_DATABASE
output COSMOSDB_CONTAINER string = isAvm ? avmDeployment!.outputs.COSMOSDB_CONTAINER : bicepDeployment!.outputs.COSMOSDB_CONTAINER
output AZURE_OPENAI_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_OPENAI_ENDPOINT : bicepDeployment!.outputs.AZURE_OPENAI_ENDPOINT
output AZURE_OPENAI_MODEL_NAME string = isAvm ? avmDeployment!.outputs.AZURE_OPENAI_MODEL_NAME : bicepDeployment!.outputs.AZURE_OPENAI_MODEL_NAME
output AZURE_OPENAI_DEPLOYMENT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_OPENAI_DEPLOYMENT_NAME : bicepDeployment!.outputs.AZURE_OPENAI_DEPLOYMENT_NAME
output AZURE_OPENAI_RAI_DEPLOYMENT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_OPENAI_RAI_DEPLOYMENT_NAME : bicepDeployment!.outputs.AZURE_OPENAI_RAI_DEPLOYMENT_NAME
output AZURE_OPENAI_API_VERSION string = isAvm ? avmDeployment!.outputs.AZURE_OPENAI_API_VERSION : bicepDeployment!.outputs.AZURE_OPENAI_API_VERSION
output AZURE_AI_SUBSCRIPTION_ID string = isAvm ? avmDeployment!.outputs.AZURE_AI_SUBSCRIPTION_ID : bicepDeployment!.outputs.AZURE_AI_SUBSCRIPTION_ID
output AZURE_AI_RESOURCE_GROUP string = isAvm ? avmDeployment!.outputs.AZURE_AI_RESOURCE_GROUP : bicepDeployment!.outputs.AZURE_AI_RESOURCE_GROUP
output AZURE_AI_PROJECT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_PROJECT_NAME : bicepDeployment!.outputs.AZURE_AI_PROJECT_NAME
output AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME : bicepDeployment!.outputs.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME
output APP_ENV string = isAvm ? avmDeployment!.outputs.APP_ENV : bicepDeployment!.outputs.APP_ENV
output AI_FOUNDRY_RESOURCE_ID string = isAvm ? avmDeployment!.outputs.AI_FOUNDRY_RESOURCE_ID : bicepDeployment!.outputs.AI_FOUNDRY_RESOURCE_ID
output COSMOSDB_ACCOUNT_NAME string = isAvm ? avmDeployment!.outputs.COSMOSDB_ACCOUNT_NAME : bicepDeployment!.outputs.COSMOSDB_ACCOUNT_NAME
output AZURE_SEARCH_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_SEARCH_ENDPOINT : bicepDeployment!.outputs.AZURE_SEARCH_ENDPOINT
output AZURE_CLIENT_ID string = isAvm ? avmDeployment!.outputs.AZURE_CLIENT_ID : bicepDeployment!.outputs.AZURE_CLIENT_ID
output AZURE_TENANT_ID string = isAvm ? avmDeployment!.outputs.AZURE_TENANT_ID : bicepDeployment!.outputs.AZURE_TENANT_ID
output AZURE_AI_SEARCH_CONNECTION_NAME string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_CONNECTION_NAME : bicepDeployment!.outputs.AZURE_AI_SEARCH_CONNECTION_NAME
output AZURE_COGNITIVE_SERVICES string = isAvm ? avmDeployment!.outputs.AZURE_COGNITIVE_SERVICES : bicepDeployment!.outputs.AZURE_COGNITIVE_SERVICES
output REASONING_MODEL_NAME string = isAvm ? avmDeployment!.outputs.REASONING_MODEL_NAME : bicepDeployment!.outputs.REASONING_MODEL_NAME
output MCP_SERVER_NAME string = isAvm ? avmDeployment!.outputs.MCP_SERVER_NAME : bicepDeployment!.outputs.MCP_SERVER_NAME
output MCP_SERVER_DESCRIPTION string = isAvm ? avmDeployment!.outputs.MCP_SERVER_DESCRIPTION : bicepDeployment!.outputs.MCP_SERVER_DESCRIPTION
output SUPPORTED_MODELS string = isAvm ? avmDeployment!.outputs.SUPPORTED_MODELS : bicepDeployment!.outputs.SUPPORTED_MODELS
output BACKEND_URL string = isAvm ? avmDeployment!.outputs.BACKEND_URL : bicepDeployment!.outputs.BACKEND_URL
output AZURE_AI_PROJECT_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_AI_PROJECT_ENDPOINT : bicepDeployment!.outputs.AZURE_AI_PROJECT_ENDPOINT
output AZURE_AI_AGENT_ENDPOINT string = isAvm ? avmDeployment!.outputs.AZURE_AI_AGENT_ENDPOINT : bicepDeployment!.outputs.AZURE_AI_AGENT_ENDPOINT
output AZURE_AI_AGENT_API_VERSION string = isAvm ? avmDeployment!.outputs.AZURE_AI_AGENT_API_VERSION : bicepDeployment!.outputs.AZURE_AI_AGENT_API_VERSION
output AZURE_AI_AGENT_PROJECT_CONNECTION_STRING string = isAvm ? avmDeployment!.outputs.AZURE_AI_AGENT_PROJECT_CONNECTION_STRING : bicepDeployment!.outputs.AZURE_AI_AGENT_PROJECT_CONNECTION_STRING
output AI_SERVICE_NAME string = isAvm ? avmDeployment!.outputs.AI_SERVICE_NAME : bicepDeployment!.outputs.AI_SERVICE_NAME
output AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RETAIL_CUSTOMER
output AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RETAIL_ORDER
output AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_SUMMARY
output AZURE_STORAGE_CONTAINER_NAME_RFP_RISK string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_RISK : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_RISK
output AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_RFP_COMPLIANCE
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_SUMMARY
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_RISK
output AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE string = isAvm ? avmDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE : bicepDeployment!.outputs.AZURE_STORAGE_CONTAINER_NAME_CONTRACT_COMPLIANCE
output AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RETAIL_CUSTOMER
output AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RETAIL_ORDER
output AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_SUMMARY
output AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK
output AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_RFP_COMPLIANCE
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_SUMMARY
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_RISK
output AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE string = isAvm ? avmDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE : bicepDeployment!.outputs.AZURE_AI_SEARCH_INDEX_NAME_CONTRACT_COMPLIANCE

output DEPLOYMENT_FLAVOR string = deploymentFlavor
output RESOURCE_GROUP_NAME string = resourceGroup().name

# 🛠️ Troubleshooting
 
When deploying Azure resources, you may come across different error codes that stop or delay the deployment process. This section lists some of the most common errors along with possible causes and step-by-step resolutions.
 
Use these as quick reference guides to unblock your deployments.

## Error Codes

 <details>
<summary><b>ReadOnlyDisabledSubscription</b></summary>  
 
- Check if you have an active subscription before starting the deployment.
 
</details>

 <details>
  <summary><b>MissingSubscriptionRegistration/ AllowBringYourOwnPublicIpAddress</b></summary>
 
 
Enable `AllowBringYourOwnPublicIpAddress` Feature
 
Before deploying the resources, you may need to enable the **Bring Your Own Public IP Address** feature in Azure. This is required only once per subscription.
 
### Steps
 
1. **Run the following command to register the feature:**
 
   ```bash
   az feature register --namespace Microsoft.Network --name AllowBringYourOwnPublicIpAddress
   ```
 
2. **Wait for the registration to complete.**
    You can check the status using:
 
    ```bash
    az feature show --namespace Microsoft.Network --name AllowBringYourOwnPublicIpAddress --query properties.state
    ```
 
3. **The output should show:**
    "Registered"
 
4. **Once the feature is registered, refresh the provider:**
 
    ```bash
    az provider register --namespace Microsoft.Network
    ```
 
    💡 Note: Feature registration may take several minutes to complete. This needs to be done only once per Azure subscription.
 
  </details>
 
<details>
<summary><b>ResourceGroupNotFound</b></summary>
 
## Option 1
### Steps
 
1. Go to [Azure Portal](https:/portal.azure.com/#home).
 
2. Click on the **"Resource groups"** option available on the Azure portal home page.
![alt text](../docs/images/AzureHomePage.png)

3. In the Resource Groups search bar, search for the resource group you intend to target for deployment. If it exists, you can proceed with using it.
![alt text](../docs/images/resourcegroup1.png)

 ## Option 2
 
- This error can occur if you deploy the template using the same .env file - from a previous deployment.
- To avoid this issue, create a new environment before redeploying.
- You can use the following command to create a new environment:
 ```
 azd env new <env-name>
 ```
</details>
<details>
<summary><b>ResourceGroupBeingDeleted</b></summary>
 
To prevent this issue, please ensure that the resource group you are targeting for deployment is not currently being deleted. You can follow steps to verify resource group is being deleted or not.
### Steps:
1. Go to [Azure Portal](https://portal.azure.com/#home)
2. Go to resource group option and search for targeted resource group
3. If Targeted resource group is there and deletion for this is in progress, it means u cannot use this, you can create new or use any other resource group
 
</details>
 
<details>
<summary><b>InternalSubscriptionIsOverQuotaForSku/ManagedEnvironmentProvisioningError </b></summary>

Quotas are applied per resource group, subscriptions, accounts, and other scopes. For example, your subscription might be configured to limit the number of vCPUs for a region. If you attempt to deploy a virtual machine with more vCPUs than the permitted amount, you receive an error that the quota was exceeded. 
For PowerShell, use the `Get-AzVMUsage` cmdlet to find virtual machine quotas.
```ps
Get-AzVMUsage -Location "West US"
```
based on available quota you can deploy application otherwise, you can request for more quota
</details>
 
<details>
<summary><b>InsufficientQuota</b></summary>

- Check if you have sufficient quota available in your subscription before deployment.
- To verify, refer to the [quota_check](../docs/quota_check.md) file for details.

</details>
 
<details>
<summary><b>DeploymentModelNotSupported</b></summary>
 
 -  The updated model may not be supported in the selected region. Please verify its availability in the [Azure AI Foundry models](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/models?tabs=global-standard%2Cstandard-chat-completions) document.
 
</details>
 <details>
<summary><b>LinkedInvalidPropertyId/ ResourceNotFound/DeploymentOutputEvaluationFailed/ CanNotRestoreANonExistingResource </b></summary>
  
- Before using any resource ID, ensure it follows the correct format.
- Verify that the resource ID you are passing actually exists.
- Make sure there are no typos in the resource ID.
- Verify that the provisioning state of the existing resource is `Succeeded` by running the following command to avoid this error while deployment or restoring the resource.

    ```
    az resource show --ids <Resource ID> --query "properties.provisioningState"
    ```
- Sample Resource IDs format
    - Log Analytics Workspace Resource ID
    ```
    /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.OperationalInsights/workspaces/{workspaceName}
    ```
    - Azure AI Foundry Project Resource ID
    ```
    /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.MachineLearningServices/workspaces/{name}
    ```
- For more information refer [Resource Not Found errors solutions](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/error-not-found?tabs=bicep)

</details>
 <details>
<summary><b>ResourceNameInvalid</b></summary>
 
- Ensure the resource name is within the allowed length and naming rules defined for that specific resource type, you can refer [Resource Naming Convention](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules) document.

</details>
 <details>
<summary><b>ServiceUnavailable/ResourceNotFound</b></summary>
 
  - Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).

  - You can request more quota, refer [Quota Request](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/create-support-request-quota-increase) Documentation


</details>
 <details>
<summary><b>Workspace Name - InvalidParameter</b></summary>

 To avoid this errors in workspace ID follow below rules. 
1. Must start and end with an alphanumeric character (letter or number).
2. Allowed characters:
    `a–z`
    `0–9`
    `- (hyphen)`
3. Cannot start or end with a hyphen -.
4. No spaces, underscores (_), periods (.), or special characters.
5. Must be unique within the Azure region & subscription.
6. Length: 3–33 characters (for AML workspaces).
</details>
 <details>
<summary><b>BadRequest: Dns record under zone Document is already taken</b></summary>

This error can occur only when user hardcoding the CosmosDB Service name. To avoid this you can try few below suggestions.
- Verify resource names are globally unique.
- If you already created an account/resource with same name in another subscription or resource group, check and delete it before reusing the name.
- By default in this template we are using unique prefix with every resource/account name to avoid this kind for errors.
</details>
 <details>
<summary><b>NetcfgSubnetRangeOutsideVnet</b></summary>

- Ensure the subnet’s IP address range falls within the virtual network’s address space.
- Always validate that the subnet CIDR block is a subset of the VNet range.
- For Azure Bastion, the AzureBastionSubnet must be at least /27.
- Confirm that the AzureBastionSubnet is deployed inside the VNet.
</details>
 <details>
<summary><b>DisableExport_PublicNetworkAccessMustBeDisabled</b></summary>

- <b>Check container source:</b> Confirm whether the deployment is using a Docker image or Azure Container Registry (ACR).
- <b>Verify ACR configuration:</b> If ACR is included, review its settings to ensure they comply with Azure requirements.
- <b>Check export settings:</b> If export is disabled in ACR, make sure public network access is also disabled.
- <b>Dedeploy after fix:</b> Correct the configuration and redeploy. This will prevent the Conflict error during deployment.
- For more information refer [ACR Data Loss Prevention](https://learn.microsoft.com/en-us/azure/container-registry/data-loss-prevention) document. 
</details>
 <details>
<summary><b>AccountProvisioningStateInvalid</b></summary>

- The AccountProvisioningStateInvalid error occurs when you try to use resources while they are still in the Accepted provisioning state.
- This means the deployment has not yet fully completed.
- To avoid this error, wait until the provisioning state changes to Succeeded.
- Only use the resources once the deployment is fully completed.
</details>
 <details>
<summary><b>VaultNameNotValid</b></summary>

 In this template Vault name will be unique everytime, but if you trying to hard code the name then please make sure below points.
 1. Check name length
    - Ensure the Key Vault name is between 3 and 24 characters.
 2. Validate allowed characters
    - The name can only contain letters (a–z, A–Z) and numbers (0–9).
    - Hyphens are allowed, but not at the beginning or end, and not consecutive (--).
3. Ensure proper start and end
    - The name must start with a letter.
    - The name must end with a letter or digit (not a hyphen).
4. Test with a new name
    - Example of a valid vault name:
        ✅ `cartersaikeyvault1`
        ✅ `securevaultdemo`
        ✅ `kv-project123`
</details>
 <details>
<summary><b>DeploymentCanceled</b></summary>

 There might be multiple reasons for this error you can follow below steps to troubleshoot.
 1. Check deployment history
    - Go to Azure Portal → Resource Group → Deployments.
    - Look at the detailed error message for the deployment that was canceled — this will show which resource failed and why.
 2. Identify the root cause
    - A DeploymentCanceled usually means:
        - A dependent resource failed to deploy.
        - A validation error occurred earlier.
        - A manual cancellation was triggered.
    - Expand the failed deployment logs for inner error messages.
3. Validate your template (ARM/Bicep)
    Run:
    ```
    az deployment group validate --resource-group <rg-name> --template-file main.bicep
    ```
4. Check resource limits/quotas
    - Ensure you have not exceeded quotas (vCPUs, IPs, storage accounts, etc.), which can silently cause cancellation.
5. Fix the failed dependency
    - If a specific resource shows BadRequest, Conflict, or ValidationError, resolve that first.
    - Re-run the deployment after fixing the root cause.
6. Retry deployment
    Once corrected, redeploy with:
    ```
    az deployment group create --resource-group <rg-name> --template-file main.bicep
    ```
Essentially: DeploymentCanceled itself is just a wrapper error — you need to check inner errors in the deployment logs to find the actual failure.
</details>
<details>
<summary><b>LocationNotAvailableForResourceType</b></summary>
 
- You may encounter a LocationNotAvailableForResourceType error if you set the secondary location to 'Australia Central' in the main.bicep file.
- This happens because 'Australia Central' is not a supported region for that resource type.
- Always refer to the README file or Azure documentation to check the list of supported regions.
- Update the deployment with a valid supported region to resolve the issue.
 
</details>
 
<details>
<summary><b>InvalidResourceLocation</b></summary>  
 
- You may encounter an InvalidResourceLocation error if you change the region for Cosmos DB or the Storage Account (secondary location) multiple times in the main.bicep file and redeploy.
- Azure resources like Cosmos DB and Storage Accounts do not support changing regions after deployment.
- If you need to change the region again, first delete the existing deployment.
- Then redeploy the resources with the updated region configuration.
 
</details>
 
<details>
 
<summary><b>DeploymentActive</b></summary>

- This issue occurs when a deployment is already in progress and another deployment is triggered in the same resource group, causing a DeploymentActive error.
- Cancel the ongoing deployment before starting a new one.
- Do not initiate a new deployment in the same resource group until the previous one is completed.
</details>

<details>
<summary><b>ResourceOperationFailure/ProvisioningDisabled</b></summary>
 
  - This error occurs when provisioning of a resource is restricted in the selected region.
    It usually happens because the service is not available in that region or provisioning has been temporarily disabled.  
 
  - Regions are restricted to guarantee compatibility with paired regions and replica locations for data redundancy and failover scenarios based on articles [Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list) and [Azure Database for MySQL Flexible Server - Azure Regions](https://learn.microsoft.com/azure/mysql/flexible-server/overview#azure-regions).
   
- If you need to use the same region, you can request a quota or provisioning exception.  
  Refer [Quota Request](https://docs.microsoft.com/en-us/azure/sql-database/quota-increase-request) for more details.
 
</details>

<details>
<summary><b>MaxNumberOfRegionalEnvironmentsInSubExceeded</b></summary>
 
- This error occurs when you try to create more than the allowed number of **Azure Container App Environments (ACA Environments)** in the same region for a subscription.  
- For example, in **Sweden Central**, only **1 Container App Environment** is allowed per subscription.  
 
The subscription 'xxxx-xxxx' cannot have more than 1 Container App Environments in Sweden Central.
 
- To fix this, you can:
  - Deploy the Container App Environment in a **different region**, OR  
  - Request a quota increase via Azure Support → [Quota Increase Request](https://go.microsoft.com/fwlink/?linkid=2208872)  
 
</details>

💡 Note: If you encounter any other issues, you can refer to the [Common Deployment Errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) documentation.
If the problem persists, you can also raise an bug in our [MACAE Github Issues](https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/issues) for further support.

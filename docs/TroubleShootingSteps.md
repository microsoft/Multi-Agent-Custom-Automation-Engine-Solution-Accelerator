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
 
 
Enable `AllowBringYourOwnPublicIpAddress` & Feature
 
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
<summary><b>DeploymentModelNotSupported/ ServiceModelDeprecated/ InvalidResourceProperties</b></summary>
 
 -  The updated model may not be supported in the selected region. Please verify its availability in the [Azure AI Foundry models](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/models?tabs=global-standard%2Cstandard-chat-completions) document.
 
</details>
 <details>
<summary><b>LinkedInvalidPropertyId/ ResourceNotFound/DeploymentOutputEvaluationFailed/ CanNotRestoreANonExistingResource / The language expression property array index is out of bounds</b></summary>
  
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
- You may encounter the error `The language expression property array index '8' is out of bounds` if the resource ID is incomplete. Please ensure your resource ID is correct and contains all required information, as shown in sample resource IDs.

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

<details>
<summary><b>Unauthorized - Operation cannot be completed without additional quota</b> </summary>

- You can check your quota usage using `az vm list-usage`.
    
    ```
    az vm list-usage --location "<Location>" -o table
    ```
- To Request more quota refer [VM Quota Request](https://techcommunity.microsoft.com/blog/startupsatmicrosoftblog/how-to-increase-quota-for-specific-types-of-azure-virtual-machines/3792394).

</details>

<details><summary><b>ParentResourceNotFound</b></summary>

- You can refer to the [Parent Resource Not found](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/error-parent-resource?tabs=bicep) documentation if you encounter this error.

</details>

<details><summary><b>ResourceProviderError</b></summary>

- This error occurs when the resource provider is not registered in your subscription. 
- To register it, refer to [Register Resource Provider](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/error-register-resource-provider?tabs=azure-cli) documentation.

</details>

<details><summary><b>Conflict - Cannot use the SKU Basic with File Change Audit for site.</b></summary>

- This error happens because File Change Audit logs aren’t supported on Basic SKU App Service Plans.

- Upgrading to Premium/Isolated SKU (supports File Change Audit), or

- Disabling File Change Audit in Diagnostic Settings if you must stay on Basic.
- Always cross-check the [supported log types](https://aka.ms/supported-log-types)
 before adding diagnostic logs to your Bicep templates.

</details>

<details>
 
<summary><b>AccountPropertyCannotBeUpdated</b></summary>
 
- The property **`isHnsEnabled`** (Hierarchical Namespace for Data Lake Gen2) is **read-only** and can only be set during **storage account creation**.  
- Once a storage account is created, this property **cannot be updated**.  
- Trying to update it via ARM template, Bicep, CLI, or Portal will fail.
 
- **Resolution**  
- Create a **new storage account** with `isHnsEnabled=true` if you require hierarchical namespace.  
- Migration may be needed if you already have data.  
- Refer to [Storage Account Update Restrictions](https://aka.ms/storageaccountupdate) for more details.  
 
</details>

<details><summary><b>InvalidRequestContent</b></summary>

- 	The deployment values either include values that aren't recognized, or required values are missing. Confirm the values for your resource type.
- You can refer [Invalid Request Content error](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors#:~:text=InvalidRequestContent,Template%20reference) documentation.

</details>

<details><summary><b>ReadOnlyDisabledSubscription</b></summary>

- Depending on the type of the Azure Subscription, the expiration date might have been reached.

- You have to activate the Azure Subscription before creating any Azure resource.
- You can refer [Reactivate a disabled Azure subscription](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-disabled) Documentation.

</details>


<details><summary><b>SkuNotAvailable</b></summary>

- You receive this error in the following scenarios:
    - When the resource SKU you've selected, such as VM size, isn't available for a location or zone.
    - If you're deploying an Azure Spot VM or Spot scale set instance, and there isn't any capacity for Azure Spot in this location. For more information, see Spot error messages.
</details>

<details><summary><b>CrossTenantDeploymentNotPermitted</b></summary>

- Check tenant match: Ensure your deployment identity (user/SP) and the target resource group are in the same tenant.
    ```
    az account show
    az group show --name <RG_NAME>
    ```

- Verify pipeline/service principal: If using CI/CD, confirm the service principal belongs to the same tenant and has permissions on the resource group.

- Avoid cross-tenant references: Make sure your Bicep doesn’t reference subscriptions, resource groups, or resources in another tenant.

- Test minimal deployment: Deploy a simple resource to the same resource group to confirm identity and tenant are correct.

- Guest/external accounts: Avoid using guest users from other tenants; use native accounts or SPs in the tenant.

</details>

<details><summary><b>RequestDisallowedByPolicy </b></summary>

- This typically indicates that an Azure Policy is preventing the requested action due to policy restrictions in your subscription.

- For more details and guidance on resolving this issue, please refer to the official Microsoft documentation: [RequestDisallowedByPolicy](https://learn.microsoft.com/en-us/troubleshoot/azure/azure-kubernetes/create-upgrade-delete/error-code-requestdisallowedbypolicy)

</details>

<details>
<summary><b>FlagMustBeSetForRestore/NameUnavailable/CustomDomainInUse</b></summary>

- This error occurs when you try to deploy a Cognitive Services resource that was **soft-deleted** earlier.  
- Azure requires you to explicitly set the **`restore` flag** to `true` if you want to recover the soft-deleted resource.  
- If you don’t want to restore the resource, you must **purge the deleted resource** first before redeploying.
Example causes:
- Trying to redeploy a Cognitive Services account with the same name as a previously deleted one.  
- The deleted resource still exists in a **soft-delete retention state**.  
**How to fix:**
1. If you want to restore → add `"restore": true` in your template properties.  
2. If you want a fresh deployment → purge the resource using:  
   ```bash
   az cognitiveservices account purge \
     --name <resource-name> \
     --resource-group <resource-group> \
     --location <location>
    ```
For more details, refer to [Soft delete and resource restore](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/delete-resource-group?tabs=azure-powershell).
</details>

<details>
<summary><b>PrincipalNotFound</b></summary>

- This error occurs when the **principal ID** (Service Principal, User, or Group) specified in a role assignment or deployment does not exist in the Azure Active Directory tenant.  
- It can also happen due to **replication delays** right after creating a new principal.  
**Example causes:**
- The specified **Object ID** is invalid or belongs to another tenant.  
- The principal was recently created but Azure AD has not yet replicated it.  
- Attempting to assign a role to a non-existing or deleted Service Principal/User/Group.  
**How to fix:**
1. Verify that the **principal ID is correct** and exists in the same directory/tenant.  
   ```bash
   az ad sp show --id <object-id>
    ```
2. If the principal was just created, wait a few minutes and retry.
3. Explicitly set the principalType property (ServicePrincipal, User, or Group) in your ARM/Bicep template to avoid replication delays.
4. If the principal does not exist, create it again before assigning roles.
For more details, see [Azure PrincipalType documentation](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting?tabs=bicep)
</details>
<details>
<summary><b>RedundancyConfigurationNotAvailableInRegion</b></summary>

- This issue happens when you try to create a **Storage Account** with a redundancy configuration (e.g., `Standard_GRS`) that is **not supported in the selected Azure region**.
- Example: Creating a storage account with **GRS** in **italynorth** will fail with this error.
```bash
az storage account create -n mystorageacct123 -g myResourceGroup -l italynorth --sku Standard_GRS --kind StorageV2
```
- To check supported SKUs for your region:
```bash
az storage account list-skus -l italynorth -o table
```
Use a supported redundancy option (e.g., Standard_LRS) in the same region
Or deploy the Storage Account in a region that supports your chosen redundancy.
For more details, refer to [Azure Storage redundancy documentation](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy?utm_source=chatgpt.com).
</details>

<details> <summary><b>DeploymentNotFound</b></summary>

- This issue occurs when the user deletes a previous deployment along with the resource group (RG), and then redeploys the same RG with the same environment name but in a different location.

- To avoid the DeploymentNotFound error, Do not change the location when redeploying a deleted RG, or Use new names for the RG and environment during redeployment.
</details>

<details><summary><b>ResourceGroupDeletionTimeout</b></summary>

- Some resources in the resource group may be stuck deleting or have dependencies; check RG resources and status.

- Ensure no resource locks or Azure Policies are blocking deletion.

- Retry deletion via CLI/PowerShell `(az group delete --name <RG_NAME> --yes --no-wait)`.

- Check Activity Log to identify failing resources; escalate to Azure Support if deletion is stuck.

</details>

<details>
<summary><b>SubscriptionDoesNotHaveServer</b></summary>
 
- This issue happens when you try to reference an **Azure SQL Server** (`Microsoft.Sql/servers`) that does not exist in the selected subscription.  
- It can occur if:  
  - The SQL server name is typed incorrectly.  
  - The SQL server was **deleted** but is still being referenced.  
  - You are working in the **wrong subscription context**.  
  - The server exists in a **different subscription/tenant** where you don’t have access.
 
**Reproduce:**  
1. Run an Azure CLI command with a non-existent server name:
```bash
   az sql db list --server sql-doesnotexist --resource-group myResourceGroup
```
 
  or
 
```bash
  az sql server show --name sql-caqfrhxr4i3hyj --resource-group myResourceGroup
 
```
   
Resolution:
 
Verify the SQL Server name exists in your subscription:
 
```bash
    az sql server list --output table
```
Make sure you are targeting the correct subscription:
 
```bash
    az account show
    az account set --subscription <subscription-id>
```
If the server was deleted, either restore it (if possible) or update references to use a valid existing server.
 
</details>


<details><summary><b>DeploymentCanceled(user.canceled)</b></summary>

- Indicates the deployment was manually canceled by the user (Portal, CLI, or pipeline).

- Check deployment history and logs to confirm who/when it was canceled.

- If accidental, retry the deployment.

- For pipelines, ensure no automation or timeout is triggering cancellation.

- Use deployment locks or retry logic to prevent accidental cancellations.

</details>

<details><summary><b>BadRequest - DatabaseAccount is in a failed provisioning state because the previous attempt to create it was not successful</b></summary>

- This error occurs when a user attempts to redeploy a resource that previously failed to provision.

- To resolve the issue, delete the failed deployment first, then start a new deployment.

- For guidance on deleting a resource from a Resource Group, refer to the following link: [Delete an Azure Cosmos DB account](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/manage-with-powershell#delete-account:~:text=%3A%24enableMultiMaster-,Delete%20an%20Azure%20Cosmos%20DB%20account,-This%20command%20deletes)

</details>

<details>

<summary><b>SpecialFeatureOrQuotaIdRequired</b></summary>

This error occurs when your subscription does not have access to certain Azure OpenAI models.  

**Example error message:**  
`SpecialFeatureOrQuotaIdRequired: The current subscription does not have access to this model 'Format:OpenAI,Name:o3,Version:2025-04-16'.`  

**Resolution:**  
To gain access, submit a request using the official form:  
👉 [Azure OpenAI Model Access Request](https://customervoice.microsoft.com/Pages/ResponsePage.aspx?id=v4j5cvGGr0GRqy180BHbR7en2Ais5pxKtso_Pz4b1_xUQ1VGQUEzRlBIMVU2UFlHSFpSNkpOR0paRSQlQCN0PWcu)  

You’ll need to use this form if you require access to the following restricted models:  
- gpt-5  
- o3  
- o3-pro  
- deep research  
- reasoning summary  
- gpt-image-1  

Once your request is approved, redeploy your resource.

</details>

<details>
<summary><b>ContainerAppOperationError</b></summary>
 
- The error is likely due to an improperly built container image. For resolution steps, refer to the [Azure Container Registry (ACR) – Build & Push Guide](./ACRBuildAndPushGuide.md)

Permission issue (UNAUTHORIZED):

- If you encounter this error, ensure the necessary permissions are granted. Refer to the following documentation for guidance: [Azure Container Registry Entra permissions and role assignments](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-rbac-built-in-roles-overview?tabs=registries-configured-with-rbac-registry-permissions).

- permission to read secrets from the Key Vault
  - The Azure Container App is configured to retrieve a secret from Azure Key Vault.

  - It uses a User-Assigned Managed Identity (UAMI) to access the Key Vault.

  - The issue occurs because this managed identity lacks the required permissions to read secrets from the Key Vault.

  - Refer to the following documentation to assign the necessary permissions: [Add Permission to get secret from Key Vault](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets?tabs=azure-portal#:~:text=Reference%20secret%20from%20Key%20Vault)

- Container image error during local deployment:
  - For custom deployments, the only valid image tag is **latest**. Using any other tag (e.g., latest_v3 or dev) will result in an error.

- Default valid container image tag for MACAE_v3 deployment:
  - dev_v3
  - demo_v3
  - latest_v3

- Default valid container image tag for MACAE_v2 deployment:
  - dev
  - demo
  - latest

 
</details>

</details>

<details>
<summary><b>ManagedEnvironmentNoAvailableCapacityInRegion</b></summary>
 
- **Check Azure Status:** Verify if the selected region has any capacity or service issues.

- **Try a Different Region:** Deploy the environment to another region with available capacity.

- **Check Quotas:** Ensure your subscription hasn’t reached limits for Container Apps or compute resources. See [Azure Container Apps quotas](https://learn.microsoft.com/en-us/azure/container-apps/quotas).

- **Retry Later:** Temporary capacity issues may resolve after some time.

- **Contact Support:** If deployment must be in the same region, raise a support request with Microsoft.
 
</details>


<details>
<summary><b>PreconditionFailed</b></summary>
 
- **Wait and Retry:** Exclusive locks are temporary—retry the operation after a few minutes.

- **Check Active Operations:** Look in Azure Portal → Cosmos DB → Activity log for ongoing updates or scaling operations.

- **Avoid Concurrent Changes:** Ensure no other operations or scripts are modifying the account at the same time.

- **Understand Locks:** Review [Cosmos DB resource locks](https://learn.microsoft.com/en-us/azure/cosmos-db/resource-locks?tabs=powershell%2Cjson)
 to see which operations require exclusive access.

- **Contact Support:** If the lock persists unusually long, raise a support request with Microsoft including the ActivityId.
 
</details>
<details>
<summary><b>InvalidCapacity</b></summary>
 
- **Check Capacity Value:** Ensure the capacity parameter in your deployment template is at least 1 (cannot be 0).

- **Validate Deployment:** Run a validation before deploying to catch errors:

- **Check Limits:** Ensure capacity does not exceed maximum allowed units. See [Azure OpenAI quotas and limits](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/quotas-limits?tabs=REST).

- **Redeploy:** After fixing the capacity value, redeploy the template.
 
</details>

<details>
<summary><b>'Microsoft.Compute/EncryptionAtHost' feature is not enabled for this subscription.</b></summary>

 - To enable encryptionAtHost, follow the steps outlined in the [Enable Enscryption at host](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/disks-enable-host-based-encryption-powershell#:~:text=Execute%20the%20following%20command%20to%20register%20the%20feature%20for%20your%20subscription) documentation.
 
</details>

<details>
<summary><b>RoleAssignmentUpdateNotPermitted</b></summary>

 - The RoleAssignmentUpdateNotPermitted error occurs when attempting to modify or overwrite an existing role assignment that cannot be changed.
 
 - Refer this link to resolve this issue: [Role assignment returns BadRequest status](https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting?tabs=bicep#:~:text=ARM%20template%20role%20assignment%20returns%20BadRequest%20status)
 
</details>

<details>
<summary><b>DeploymentScriptACIProvisioningTimeout</b></summary>

- The **DeploymentScriptACIProvisioningTimeout** error occurs when the Azure Container Instance (ACI) used by the deployment script fails to start or times out during provisioning.

- **Resolution:** Redeploy in another region, increase the script timeout, or verify ACI/VNet capacity and permissions.

</details>
<details>
<summary><b>VMSizeIsNotPermittedToEnableAcceleratedNetworking</b></summary>

- The **VMSizeIsNotPermittedToEnableAcceleratedNetworking** error occurs when a selected VM size (e.g., `Standard_A2m_v2`) does not support Accelerated Networking.

- To fix this issue, use a VM size that supports Accelerated Networking.  
  👉 Check the [Microsoft list of supported VM sizes](https://learn.microsoft.com/azure/virtual-network/accelerated-networking-overview#supported-vm-instances).

</details>

<details>
<summary><b>PropertyChangeNotAllowed</b></summary>

- This error occurs because the `osProfile.adminUsername` property of a Virtual Machine is **immutable** once the VM is created. If you modify the VM username or password in the deployment template and attempt to redeploy, Azure prevents the change and triggers this error.
- **Resolution:** Before redeployment, delete the existing VM deployment and then redeploy with the new credentials.
  ```bash
  # Redeploy with new credentials
  azd env set AZURE_ENV_VM_ADMIN_USERNAME "newusername"
  azd env set AZURE_ENV_VM_ADMIN_PASSWORD "NewSecurePassword123!
</details>
<details>
<summary><b>Conflict: Website with given name already exists</b></summary>

- This conflict occurs when a deployment attempts to create an **App Service** with a name (e.g., `app-multi-agent`) that already exists in another resource group or subscription. App Service names are **globally unique** across all Azure regions and subscriptions.
- **Resolution:**  
  1. Verify whether the App Service name already exists by running:  
     ```bash
     az webapp show --name app-multi-agent --resource-group <any-rg>
     ```  
  2. If the App Service exists, delete the existing App Service or resource group and redeploy with unique name.
</details>
<details>
<summary><b>InvalidParameter - Weak VM Admin Password</b></summary>

- This error occurs when the Virtual Machine admin password does not meet Azure's password complexity requirements.  
  The deployment fails validation because the provided password is too weak or insecure.

- **Resolution:**  
  Use a strong password that meets at least **3 of the following 4 conditions:**  
  - Uppercase letter (**A–Z**)  
  - Lowercase letter (**a–z**)  
  - Number (**0–9**)  
  - Special character (**!@#$%^&***)

</details>
<details>
<summary><b>InvalidParameter - Invalid Image Reference</b></summary>

- The VM deployment fails when the specified image reference — for example:  
  **Publisher:** `MicrosoftWindowsServer`, **Offer:** `WindowsServer`, **Sku:** `2019-datacenter-g2` —  
  is invalid or unavailable in the selected Azure region.
- **Resolution:**  
  1. Verify available images in the selected region by running:  
     ```bash
     az vm image list --location <region> --publisher MicrosoftWindowsServer --offer WindowsServer --output table
     ```  
  2. Choose a valid image SKU that exists in that region and update the template accordingly.  
  3. Redeploy the VM after correcting the image reference.

</details>
<details>
<summary><b>Conflict - Duplicate Data Sink Usage in Diagnostic Settings</b></summary>

- This issue occurs when two or more diagnostic settings are configured using the **same Log Analytics workspace** and **same category** on the **same resource**.  
  Azure does not allow reusing the same data sink (workspace) for identical category-resource combinations.

- To fix this issue, keep only **one diagnostic setting** per resource–category–workspace combination, **or** Change either the **category** or the **workspace** in one of the diagnostic settings.

</details>

<details>
<summary><b>SubscriptionNotFound</b></summary>
 
- This error occurs when the specified subscription ID or name is invalid, misspelled, or inaccessible to the logged-in user.
 
- Example:
  ```bash
  az group list --subscription "Git"
    ```
**Output:**
  ```
  SubscriptionNotFound: The subscription 'Git' could not be found.
  ```
 
- **Fix:**
  1. List available subscriptions:
  ```bash
  az account list -o table
  ```
  2. Set a valid subscription:
  ```bash
  az account set --subscription "<subscription-id>"
  ```
  3. Ensure the subscription exists and you have access to it.
 
</details>

<details>
<summary><b>DatabaseAccountNotOnline</b></summary>

- This error occurs when a Cosmos DB account is not yet in the **Online** state during operations such as database or container creation.

  - Example:
    ```json
    {"code":"BadRequest","message":"The requested operation cannot be performed because the database account cosmos-cps-omhkx7ntgoh5 state is not Online."}
    ```

- **Root Cause:**
  - The Cosmos DB account is still provisioning or failed to deploy.
  - A dependent operation was triggered too soon after account creation.

- **Fix:**
  1. Wait until the account state becomes **Online**:
     ```bash
     az cosmosdb show -n <account-name> -g <resource-group> --query "provisioningState"
     ```
  2. Retry the operation after the provisioning completes.
  3. If the state remains **Failed**, delete and recreate the Cosmos DB account.
  4. Check [Azure Status](https://status.azure.com) for any regional issues.

</details>

<details>
<summary><b>NoRegisteredProviderFound</b></summary>

- This error occurs when the **resource provider** or **API version** used in the deployment is not registered or supported in the selected Azure region.  
- It often appears while deploying resources (e.g., `Microsoft.Search/searchServices`) using an **unsupported API version** or to a **region that does not support the resource type**.

- **Possible Causes:**
  - The resource provider (e.g., `Microsoft.Search`) is not registered in the subscription.
  - The API version used (`2020-06-30`) is deprecated or unavailable in the target region.
  - The chosen Azure region does not support the resource type.

- **How to Fix:**
  1. Register the required provider:
     ```bash
     az provider register --namespace Microsoft.Search
     ```
  2. Verify available API versions and regions:
     ```bash
     az provider show --namespace Microsoft.Search --query "resourceTypes[?resourceType=='searchServices'].apiVersions"
     az provider show --namespace Microsoft.Search --query "resourceTypes[?resourceType=='searchServices'].locations" -o table
     ```
  3. Update the deployment template to use a **supported API version** (e.g., `2023-11-01` or later).
  4. Redeploy the resource in a **supported region** such as `northeurope`, `uksouth`, or `eastus`.

- **Reference Documentation:**
  - [Azure Resource Providers and Types](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types)
  - [Azure Cognitive Search REST API Versions](https://learn.microsoft.com/en-us/rest/api/searchservice/)

</details>

<details>
<summary><b>InvalidFailoverPriorityConfiguration</b></summary>

- This error occurs when configuring failover regions for **Azure Cosmos DB** with an invalid failover priority setup.

  - Example:
    ```json
    {"code":"BadRequest","message":"Failover priority value 0 supplied for region Sweden Central is invalid"}
    ```

- **Root Cause:**
  - Multiple regions were assigned the same **failoverPriority** value (e.g., two regions with `0`).
  - A secondary region was assigned failoverPriority = 0, which is reserved for the primary write region.

- **Fix:**
  1. Ensure each region has a unique failover priority.
  2. Only the **primary write region** should use `failoverPriority: 0`.
  3. Example of valid configuration:
     ```bash
     az cosmosdb update \
       -n <account-name> \
       -g <resource-group> \
       --locations regionName=westeurope failoverPriority=0 \
                     regionName=swedencentral failoverPriority=1
     ```
  4. Verify using:
     ```bash
     az cosmosdb show -n <account-name> -g <resource-group> --query "locations"
     ```

</details>
<details>
<summary><b>FailedIdentityOperation</b></summary>

- This issue occurs when an identity operation fails during deployment of a Managed Environment or Container App due to a **conflict** between an existing resource and a new deployment.

- **Possible Causes:**
  - A resource with the same name already exists.
  - A previous resource deletion is still pending.
  - A managed identity creation or update operation overlaps with another deployment.

- **How to Fix:**
  1. Verify if the resource exists or is in a deleting state:
     ```bash
     az resource show --ids "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.App/managedEnvironments/<env-name>"
     ```
  2. Wait for the delete operation to complete or use a new resource name.
  3. Retry deployment after a few minutes.

- **Reference Documentation:**
  - [Azure Resource Manager Deployment Errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/common-deployment-errors)

</details>

<details>
<summary><b>ServiceQuotaExceeded</b></summary>

- This error occurs when the deployment exceeds the allowed **Free tier (F)** quota for Azure Cognitive Search.  
  Each subscription can only have **one Free-tier** Cognitive Search service.

- **Possible Causes:**
  - A Free-tier Cognitive Search service already exists in the subscription.
  - The deployment template or script attempts to create another Free-tier resource.

- **How to Fix:**
  1. Delete the existing Free-tier service:
     ```bash
     az search service delete -n <existing-service> -g <resource-group>
     ```
  2. Or deploy with a different SKU, such as **Basic**:
     ```bash
     az search service create -n <new-service> -g <resource-group> --sku basic
     ```
  3. For quota increase requests, refer to:  
     [Quota Request Documentation](https://aka.ms/AddQuotaSubscription)

- **Reference Documentation:**
  - [Azure Cognitive Search Pricing](https://learn.microsoft.com/en-us/azure/search/search-sku-tier)
  - [Common Azure Deployment Errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/common-deployment-errors)

</details>

<details>
<summary><b>InvalidTemplate - Missing or Null Property</b></summary>

- This error occurs when a required property (such as `version`) in the ARM/Bicep deployment template is **missing** or **set to null**.  
  Azure Resource Manager (ARM) fails template validation before deployment.

- **Possible Causes:**
  - The `deployments[0].model` parameter is missing the required `version` field.
  - Incorrect or incomplete parameter values passed during deployment.
  - Template schema mismatch between resource type and provided properties.

- **How to Fix:**
  1. Ensure all required fields are defined in your template:
     ```json
     "model": {
       "name": "myAppModel",
       "version": "1.0.0"
     }
     ```
  2. Validate the template before deployment:
     ```bash
     az deployment group validate --resource-group <rg-name> --template-file <template.json>
     ```
  3. Refer to the official ARM template syntax guide:  
     [Azure ARM Template Parameters Syntax](https://aka.ms/arm-syntax-parameters)

</details>

<details>
<summary><b>InvalidResourceGroupLocation</b></summary>

- This error occurs when you try to **create or deploy resources in a Resource Group (RG)** that already exists **in a different Azure region**.

- **Root Cause:**
  - A Resource Group with the same name already exists, but in another location.
  - Azure Resource Groups are globally unique per subscription, and their location cannot be changed once created.
  - Attempting to redeploy a resource or template with the same RG name but a different location will trigger this error.

- **Example Scenario:**
  - Existing Resource Group: `rg-demo` in `eastus`
  - Deployment attempt: `az group create -n rg-demo -l westus`
  - Result:  
    ```
    {"error":{"code":"InvalidResourceGroupLocation","message":"The provided resource group location 'westus' is not the same as the existing resource group location 'eastus'."}}
    ```

- **Resolution Steps:**
  1. Use the **same location** as the existing resource group:
     ```bash
     az group create -n rg-demo -l eastus
     ```
  2. Or, create a **new Resource Group name** if you want to deploy in another region:
     ```bash
     az group create -n rg-demo-west -l westus
     ```
  3. Verify the location of existing Resource Groups:
     ```bash
     az group show -n rg-demo --query location -o tsv
     ```

- **References:**
  - [Azure Resource Manager Resource Groups Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal)
  - [az group create command](https://learn.microsoft.com/en-us/cli/azure/group#az-group-create)

</details>

💡 Note: If you encounter any other issues, you can refer to the [Common Deployment Errors](https://learn.microsoft.com/en-us/azure/azure-resource-manager/troubleshooting/common-deployment-errors) documentation.
If the problem persists, you can also raise an bug in our [MACAE Github Issues](https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/issues) for further support.

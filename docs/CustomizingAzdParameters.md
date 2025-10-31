## [Optional]: Customizing resource names 

By default this template will use the environment name as the prefix to prevent naming collisions within Azure. The parameters below show the default values. You only need to run the statements below if you need to change the values. 

> To override any of the parameters, run `azd env set <PARAMETER_NAME> <VALUE>` before running `azd up`. On the first azd command, it will prompt you for the environment name. Be sure to choose 3-20 characters alphanumeric unique name. 

## Parameters

| Name                            | Type   | Default Value     | Purpose                                                                                             |
| ------------------------------- | ------ | ----------------- | --------------------------------------------------------------------------------------------------- |
| `AZURE_ENV_NAME`                | string | `macae`           | Used as a prefix for all resource names to ensure uniqueness across environments.                   |
| `AZURE_LOCATION`                | string | `<User selects during deployment>`   | Location of the Azure resources. Controls where the infrastructure will be deployed.                |
| `AZURE_ENV_OPENAI_LOCATION`     | string | `<User selects during deployment>`   | Specifies the region for OpenAI resource deployment.                                                |
| `AZURE_ENV_MODEL_DEPLOYMENT_TYPE` | string | `GlobalStandard` | Defines the deployment type for the AI model (e.g., Standard, GlobalStandard).                     |
| `AZURE_ENV_MODEL_NAME`          | string | `gpt-4o`          | Specifies the name of the GPT model to be deployed.                                                |
| `AZURE_EXISTING_AI_PROJECT_RESOURCE_ID`          | string | `<Existing Workspace Id>`          | Set this if you want to reuse an AI Foundry Project instead of creating a new one.                                                |                        
| `AZURE_ENV_MODEL_VERSION`       | string | `2024-08-06`      | Version of the GPT model to be used for deployment.                                                |
| `AZURE_ENV_MODEL_CAPACITY`       | int | `150`      | Sets the GPT model capacity.                                                |
| `AZURE_ENV_IMAGETAG`            | string | `latest`          | Docker image tag used for container deployments.                                                   |
| `AZURE_ENV_ENABLE_TELEMETRY`    | bool   | `true`            | Enables telemetry for monitoring and diagnostics.                                                  |
| `AZURE_ENV_LOG_ANALYTICS_WORKSPACE_ID` | string  | Guide to get your [Existing Workspace ID](/docs/re-use-log-analytics.md) | Set this if you want to reuse an existing Log Analytics Workspace instead of creating a new one.     |
| `AZURE_ENV_VM_ADMIN_USERNAME`  | string | `take(newGuid(), 20)`               | The administrator username for the virtual machine.         |
| `AZURE_ENV_VM_ADMIN_PASSWORD`  | string | `newGuid()`               | The administrator password for the virtual machine.         |
---

## How to Set a Parameter

To customize any of the above values, run the following command **before** `azd up`:

```bash
azd env set <PARAMETER_NAME> <VALUE>
```

Set the Log Analytics Workspace Id if you need to reuse the existing workspace which is already existing
```shell
azd env set AZURE_ENV_LOG_ANALYTICS_WORKSPACE_ID '/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>'
```

**Example:**

```bash
azd env set AZURE_LOCATION westus2
```

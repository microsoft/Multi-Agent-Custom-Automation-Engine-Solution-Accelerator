# Deployment Guide

## **Pre-requisites**

To deploy this solution accelerator, ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the necessary permissions to create **resource groups, resources, app registrations, and assign roles at the resource group level**. This should include Contributor role at the subscription level and Role Based Access Control role on the subscription and/or resource group level. Follow the steps in [Azure Account Set Up](../docs/AzureAccountSetUp.md).

Check the [Azure Products by Region](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/?products=all&regions=all) page and select a **region** where the following services are available:

- [Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/)
- [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/)
- [GPT Model Capacity](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

Here are some example regions where the services are available: East US, East US2, Japan East, UK South, Sweden Central.

### **Important Note for PowerShell Users**

If you encounter issues running PowerShell scripts due to the policy of not being digitally signed, you can temporarily adjust the `ExecutionPolicy` by running the following command in an elevated PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This will allow the scripts to run for the current session without permanently changing your system's policy.

## Deployment Options & Steps

### Sandbox or WAF Aligned Deployment Options

The [`infra`](../infra) folder of the Multi Agent Solution Accelerator contains the [`main.bicep`](../infra/main.bicep) Bicep script, which defines all Azure infrastructure components for this solution.

When running `azd up`, you’ll now be prompted to choose between a **WAF-aligned configuration** and a **sandbox configuration** using a simple selection:

- A **sandbox environment** — ideal for development and proof-of-concept scenarios, with minimal security and cost controls for rapid iteration.

- A **production deployments environment**, which applies a [Well-Architected Framework (WAF) aligned](https://learn.microsoft.com/en-us/azure/well-architected/) configuration. This option enables additional Azure best practices for reliability, security, cost optimization, operational excellence, and performance efficiency, such as:
  - Enhanced network security (e.g., Network protection with private endpoints)
  - Stricter access controls and managed identities
  - Logging, monitoring, and diagnostics enabled by default
  - Resource tagging and cost management recommendations

**How to choose your deployment configuration:**

When prompted during `azd up`:

![useWAFAlignedArchitecture](images/macae_waf_prompt.png)

- Select **`true`** to deploy a **WAF-aligned, production-ready environment**  
- Select **`false`** to deploy a **lightweight sandbox/dev environment**

> [!TIP]
> Always review and adjust parameter values (such as region, capacity, security settings and log analytics workspace configuration) to match your organization’s requirements before deploying. For production, ensure you have sufficient quota and follow the principle of least privilege for all identities and role assignments.

> To reuse an existing Log Analytics workspace, update the existingWorkspaceResourceId field under the logAnalyticsWorkspaceConfiguration parameter in the .bicep file with the resource ID of your existing workspace.
For example: 
```
param logAnalyticsWorkspaceConfiguration = {
  dataRetentionInDays: 30
  existingWorkspaceResourceId: '/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>'
}
```

> [!IMPORTANT]
> The WAF-aligned configuration is under active development. More Azure Well-Architected recommendations will be added in future updates.

### Deployment Steps 

Pick from the options below to see step-by-step instructions for GitHub Codespaces, VS Code Dev Containers, Local Environments, and Bicep deployments.

| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator) |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

<details>
  <summary><b>Deploy in GitHub Codespaces</b></summary>

### GitHub Codespaces

You can run this solution using GitHub Codespaces. The button will open a web-based VS Code instance in your browser:

1. Open the solution accelerator (this may take several minutes):

   [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator)

2. Accept the default values on the create Codespaces page.
3. Open a terminal window if it is not already open.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<details>
  <summary><b>Deploy in VS Code</b></summary>

### VS Code Dev Containers

You can run this solution in VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed).
2. Open the project:

   [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<details>
  <summary><b>Deploy in your local Environment</b></summary>

### Local Environment

If you're not using one of the above options for opening the project, then you'll need to:

1. Make sure the following tools are installed:

   - [PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell?view=powershell-7.5) <small>(v7.0+)</small> - available for Windows, macOS, and Linux.
   - [Azure Developer CLI (azd)](https://aka.ms/install-azd) <small>(v1.15.0+)</small> - version
   - [Python 3.9+](https://www.python.org/downloads/)
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - [Git](https://git-scm.com/downloads)

2. Clone the repository or download the project code via command-line:

   ```shell
   azd init -t microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/
   ```

3. Open the project folder in your terminal or editor.
4. Continue with the [deploying steps](#deploying-with-azd).

</details>

<br/>

Consider the following settings during your deployment to modify specific settings:

<details>
  <summary><b>Configurable Deployment Settings</b></summary>

When you start the deployment, most parameters will have **default values**, but you can update the following settings [here](../docs/CustomizingAzdParameters.md):

| **Setting**                    | **Description**                                                                      | **Default value** |
| ------------------------------ | ------------------------------------------------------------------------------------ | ----------------- |
| **Environment Name**           | Used as a prefix for all resource names to ensure uniqueness across environments.    | macae             |
| **Azure Region**               | Location of the Azure resources. Controls where the infrastructure will be deployed. | swedencentral     |
| **OpenAI Deployment Location** | Specifies the region for OpenAI resource deployment.                                 | swedencentral     |
| **Model Deployment Type**      | Defines the deployment type for the AI model (e.g., Standard, GlobalStandard).      | GlobalStandard    |
| **GPT Model Name**             | Specifies the name of the GPT model to be deployed.                                 | gpt-4o            |
| **GPT Model Version**          | Version of the GPT model to be used for deployment.                                 | 2024-08-06        |
| **GPT Model Capacity**          | Sets the GPT model capacity.                                 | 150        |
| **Image Tag**                  | Docker image tag used for container deployments.                                    | latest            |
| **Enable Telemetry**           | Enables telemetry for monitoring and diagnostics.                                    | true              |
| **Existing Log Analytics Workspace**        | To reuse an existing Log Analytics Workspace ID instead of creating a new one.              | *(none)*          |
| **Existing Azure AI Foundry Project**        | To reuse an existing Azure AI Foundry Project ID instead of creating a new one.              | *(none)*          |

</details>

<details>
  <summary><b>[Optional] Quota Recommendations</b></summary>

By default, the **GPT model capacity** in deployment is set to **140k tokens**.

To adjust quota settings, follow these [steps](./AzureGPTQuotaSettings.md).

**⚠️ Warning:** Insufficient quota can cause deployment errors. Please ensure you have the recommended capacity or request additional capacity before deploying this solution.

</details>

<details>

  <summary><b>Reusing an Existing Log Analytics Workspace</b></summary>

  Guide to get your [Existing Workspace ID](/docs/re-use-log-analytics.md)

</details>

<details>

  <summary><b>Reusing an Existing Azure AI Foundry Project</b></summary>

  Guide to get your [Existing Project ID](/docs/re-use-foundry-project.md)

</details>

### Deploying with AZD

Once you've opened the project in [Codespaces](#github-codespaces), [Dev Containers](#vs-code-dev-containers), or [locally](#local-environment), you can deploy it to Azure by following these steps:

1. Login to Azure:

   ```shell
   azd auth login
   ```

   #### To authenticate with Azure Developer CLI (`azd`), use the following command with your **Tenant ID**:

   ```sh
   azd auth login --tenant-id <tenant-id>
   ```

2. Provision and deploy all the resources:

   ```shell
   azd up
   ```

3. Provide an `azd` environment name (e.g., "macaeapp").
4. Select a subscription from your Azure account and choose a location that has quota for all the resources.

   - This deployment will take _4-6 minutes_ to provision the resources in your account and set up the solution with sample data.
   - If you encounter an error or timeout during deployment, changing the location may help, as there could be availability constraints for the resources.

5. Once the deployment has completed successfully, open the [Azure Portal](https://portal.azure.com/), go to the deployed resource group, find the App Service, and get the app URL from `Default domain`.

6. When Deployment is complete, follow steps in [Set Up Authentication in Azure App Service](../docs/azure_app_service_auth_setup.md) to add app authentication to your web app running on Azure App Service

7. If you are done trying out the application, you can delete the resources by running `azd down`.


### 🛠️ Troubleshooting
 If you encounter any issues during the deployment process, please refer [troubleshooting](../docs/TroubleShootingSteps.md) document for detailed steps and solutions.

# Local setup

> **Note for macOS Developers**: If you are using macOS on Apple Silicon (ARM64) the DevContainer will **not** work. This is due to a limitation with the Azure Functions Core Tools (see [here](https://github.com/Azure/azure-functions-core-tools/issues/3112)).

The easiest way to run this accelerator is in a VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
1. Open the project:
   [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator)

1. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window

## Detailed Development Container setup instructions

The solution contains a [development container](https://code.visualstudio.com/docs/remote/containers) with all the required tooling to develop and deploy the accelerator. To deploy the Multi-Agent solutions accelerator using the provided development container you will also need:

- [Visual Studio Code](https://code.visualstudio.com)
- [Remote containers extension for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

If you are running this on Windows, we recommend you clone this repository in [WSL](https://code.visualstudio.com/docs/remote/wsl)

```cmd
git clone https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator
```

Open the cloned repository in Visual Studio Code and connect to the development container.

```cmd
code .
```

!!! tip
Visual Studio Code should recognize the available development container and ask you to open the folder using it. For additional details on connecting to remote containers, please see the [Open an existing folder in a container](https://code.visualstudio.com/docs/remote/containers#_quick-start-open-an-existing-folder-in-a-container) quickstart.

When you start the development container for the first time, the container will be built. This usually takes a few minutes. **Please use the development container for all further steps.**

The files for the dev container are located in `/.devcontainer/` folder.

## Local deployment and debugging:

1. **Clone the repository.**

2. **Log into the Azure CLI:**

   - Check your login status using:
     ```bash
     az account show
     ```
   - If not logged in, use:
     ```bash
     az login
     ```
   - To specify a tenant, use:
     ```bash
     az login --tenant <tenant_id>
     ```

3. **Create a Resource Group:**

   - You can create it either through the Azure Portal or the Azure CLI:
     ```bash
     az group create --name <resource-group-name> --location EastUS2
     ```

4. **Deploy the Bicep template:**

   - You can use the Bicep extension for VSCode (Right-click the `.bicep` file, then select "Show  deployment plan") or use the Azure CLI:
     ```bash
     az deployment group create -g <resource-group-name> -f infra/main.bicep --query 'properties.outputs'
     ```
   - **Note**: You will be prompted for a `principalId`, which is the ObjectID of your user in Entra ID. To find it, use the Azure Portal or run:

     ```bash
     az ad signed-in-user show --query id -o tsv
     ```

     You will also be prompted for locations for Cosmos and OpenAI services. This is to allow separate regions where there may be service quota restrictions.

   - **Additional Notes**:

     **Role Assignments in Bicep Deployment:**

     The **main.bicep** deployment includes the assignment of the appropriate roles to AOAI and Cosmos services. If you want to modify an existing implementation—for example, to use resources deployed as part of the simple deployment for local debugging—you will need to add your own credentials to access the Cosmos and AOAI services. You can add these permissions using the following commands:

     ```bash
     az cosmosdb sql role assignment create --resource-group <solution-accelerator-rg> --account-name <cosmos-db-account-name> --role-definition-name "Cosmos DB Built-in Data Contributor" --principal-id <aad-user-object-id> --scope /subscriptions/<subscription-id>/resourceGroups/<solution-accelerator-rg>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-db-account-name>
     ```

     ```bash
     az role assignment create --assignee <aad-user-upn> --role "Azure AI User" --scope /subscriptions/<subscription-id>/resourceGroups/<solution-accelerator-rg>/providers/Microsoft.CognitiveServices/accounts/<azure-ai-foundry-name>
     ```

     **Using a Different Database in Cosmos:**

     You can set the solution up to use a different database in Cosmos. For example, you can name it something like macae-dev. To do this:

   1. Change the environment variable **COSMOSDB_DATABASE** to the new database name.
   2. You will need to create the database in the Cosmos DB account. You can do this from the Data Explorer pane in the portal, click on the drop down labeled "_+ New Container_" and provide all the necessary details.

5. **Create a `.env` file:**

   - Navigate to the `src\backend` folder and create a `.env` file based on the provided `.env.sample` file.
   - Update the `.env` file with the required values from your Azure resource group in Azure Portal App Service environment variables.
   - Alternatively, if resources were
   provisioned using `azd provision` or `azd up`, a `.env` file is automatically generated in the `.azure/<env-name>/.env`
   file. You can copy the contents of this file into your backend `.env` file.

    _**Note**: To get your `<env-name>` run `azd env list` to see which env is default._

6. **Fill in the `.env` file:**

   - Use the output from the deployment or check the Azure Portal under "Deployments" in the resource group.
   - Make sure to set APP_ENV to "**dev**" in `.env` file.
   - For local development, make sure to include below env variables in the `.env`
     - `BACKEND_API_URL=http://localhost:8000`
     - `FRONTEND_SITE_NAME=http://127.0.0.1:3000` .

7. **(Optional) Set up a virtual environment:**

   - If you are using `venv`, create and activate your virtual environment for both the frontend and backend folders.

8. **Install requirements - frontend:**

   - In each of the frontend and backend folders -
     Open a terminal in the `src` folder and run:
     ```bash
     pip install -r requirements.txt
     ```
     
9. **Build the frontend (important):**

    - Before running the frontend server, you must build the frontend to generate the necessary `build/assets` directory.

      From the `src/frontend` directory, run:

      ```bash
      npm install
      npm run build
      ```

10. **Run the application:**

- From the src/backend directory:

```bash
python app_kernel.py
```

- In a new terminal from the src/frontend directory

```bash
 python frontend_server.py
```

10. Open a browser and navigate to `http://localhost:3000`
11. To see swagger API documentation, you can navigate to `http://localhost:8000/docs`

## Debugging the solution locally

You can debug the API backend running locally with VSCode using the following launch.json entry:

```
    {
      "name": "Python Debugger: Backend",
      "type": "debugpy",
      "request": "launch",
      "cwd": "${workspaceFolder}/src/backend",
      "module": "uvicorn",
      "args": ["app:app", "--reload"],
      "jinja": true
    }
```

To debug the python server in the frontend directory (frontend_server.py) and related, add the following launch.json entry:

```
    {
      "name": "Python Debugger: Frontend",
      "type": "debugpy",
      "request": "launch",
      "cwd": "${workspaceFolder}/src/frontend",
      "module": "uvicorn",
      "args": ["frontend_server:app", "--port", "3000", "--reload"],
      "jinja": true
    }
```

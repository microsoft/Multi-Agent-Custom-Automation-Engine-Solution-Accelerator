# Multi-Agent -Custom Automation Engine Solution Accelerator

MENU: [**USER STORY**](#user-story) \| [**SIMPLE DEPLOY**](#quick-deploy)  \| [**SUPPORTING DOCUMENTATION**](#supporting-documentation) \|

<h2><img src="./documentation/images/readme/userStory.png" width="64">
<br/>
User story
</h2>

### Overview

Problem:
Agentic AI systems are set to transform the way businesses operate, however it can be fairly complex to build an initial MVP to demonstrate this value. 

Solution:
The Multi-Agent -Custom Automation Engine Solution Accelerator provides a ready to go application to use as the base of the MVP, or as a reference, allowing you to hit the ground running.

### Technology Note
This accelerator uses the AutoGen framework from Microsoft Research.  This is an open source project that is maintained by [Microsoft Research’s AI Frontiers Lab](https://www.microsoft.com/research/lab/ai-frontiers/). Please see this [blog post](https://devblogs.microsoft.com/autogen/microsofts-agentic-frameworks-autogen-and-semantic-kernel/) for the latest information on using the AutoGen framework in production solutions.

### Use cases / scenarios
The multi-agent approach allows users to utilize multiple AI agents simultaneously for repeatable tasks, ensuring consistency and efficiency. 
The agents collaborate with a manager on various assignments for onboarding a new employee , such as HR and tech support AI working together to set up software accounts, configure hardware, schedule onboarding meetings, register employees for benefits, and send welcome emails. Additionally, these agents can handle tasks like procurement and drafting press releases.

### Business value
Multi-agent systems represent the next wave of Generative AI use cases, offering entirely new opportunities to drive efficiencies in your business. The Multi-Agent -Custom Automation Engine Solution Accelerator demonstrates several key benefits:

- **Allows people to focus on what matters:** by doing the heavy lifting involved with coordinating activities across an organization, peoples’ time is freed up to focus on their specializations.
- **Enabling GenAI to scale:** by not needing to build one application after another, organizations are able to reduce the friction of adopting GenAI across their entire organization. One capability can unlock almost unlimited use cases.
- **Applicable to most industries:** these are common challenges that most organizations face, across most industries.

Whilst still an emerging area, investing in agentic use cases, digitatization and developing tools will be key to ensuring you are able to leverage these new technologies and seize the GenAI moment.

### Technical key features

This application is an AI-driven orchestration system that manages a group of AI agents to accomplish tasks based on user input. It uses a FastAPI backend to handle HTTP requests, processes them through various specialized agents, and stores stateful information using Azure Cosmos DB. The system is designed to:

- Receive input tasks from users.
- Generate a detailed plan to accomplish the task using a Planner agent.
- Execute the plan by delegating steps to specialized agents (e.g., HR, Procurement, Marketing).
- Incorporate human feedback into the workflow.
- Maintain state across sessions with persistent storage.

This system is intended for developing and deploying custom AI solutions for specific customers. This code has not been tested as an end-to-end, reliable production application- it is a foundation to help accelerate building out multi-agent systems. You are encouraged to add your own data and functions to the agents, and then you must apply your own performance and safety evaluation testing frameworks to this system before deploying it.

\
![image](./documentation/images/readme/macae-application.png)



### Products used/licenses required

-   Azure Container Application

-   Azure OpenAI

-   Azure Cosmos DB

-   The user deploying the template must have permission to create
    resources and resource groups.

### Solution accelerator architecture
![image](./documentation/images/readme/macae-architecture.png)




### **How to install/deploy**

This guide provides step-by-step instructions for deploying your application using Azure Container Registry (ACR) and Azure Container Apps.

There are several ways to deploy the solution.  You can deploy to run in Azure in one click, or manually, or you can deploy locally.

## Quick Deploy

<h2><img src="./documentation/images/readme/oneClickDeploy.png" width="64"></h2>

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmicrosoft%2FMulti-Agent-Custom-Automation-Engine-Solution-Accelerator%2Frefs%2Fheads%2Fmain%2Fdeploy%2Fmacae-continer-oc.json)

When Deployment is complete, follow steps in [Set Up Authentication in Azure App Service](./documentation/azure_app_service_auth_setup.md) to add app authentication to your web app running on Azure App Service

## Local Deployment
To run the solution site and API backend locally, See the [local deployment guide](./documentation/LocalDeployment.md).

## Manual Azure Deployment
### Prerequisites

- Azure CLI installed
- Azure account with appropriate permissions
- Docker installed
- Azure Container Registry installed

### Get Admin Credentials from ACR

Retrieve the admin credentials for your Azure Container Registry (ACR):

```sh
az acr credential show \
--name acrcontoso7wx5mg43sbnl4 \
--resource-group rg-ssattiraju
```

### Login to ACR

Login to your Azure Container Registry:

```sh
az acr login --name acrcontoso7wx5mg43sbnl4
```

### Build Image

Build the Docker image and push it to your Azure Container Registry:

```sh
az acr build \
--registry acrcontoso7wx5mg43sbnl4 \
--resource-group rg-name \
--image macae:latest .
```

### List the Image Created

List the images in your Azure Container Registry:

```sh
az acr repository list --name acrcontoso7wx5mg43sbnl4
```

### Upgrade Container App Extension

Ensure you have the latest version of the Azure Container Apps extension:
`az extension add --name containerapp --upgrade`

### Get List of Available Locations

Retrieve a list of available Azure locations:
`az account list-locations -o table`

### Create Apps Environment

Create an environment for your Azure Container Apps:

```sh
az containerapp env create \
--name python-container-env \
--resource-group rg-name \
--location southeastasia
```

### Get Credentials

```sh
az acr credential show -n acrcontoso7wx5mg43sbnl4
```

### Create container app

create the container app with the config

```sh
az containerapp create \
 --name python-container-app \
 --resource-group rg-name \
 --image acrcontoso7wx5mg43sbnl4.azurecr.io/macae:latest \
 --environment python-container-env \
 --ingress external --target-port 8000 \
 --registry-server acrcontoso7wx5mg43sbnl4.azurecr.io \
 --registry-username password \
 --registry-password REGISTRY_PASSWORD \
 --query properties.configuration.ingress.fqdn

```
<br></br>

## Supporting documentation


### 

### How to customize

This solution is designed to be easily customizable. You can modify the front end site, or even build your own front end and attach to the backend API. You can further customize the backend by adding your own agents with their own specific capabilities. Deeper technical information to aid in this customization can be found in this [document](./documentation/CustomizeSolution.md).

### Additional resources

- [Python FastAPI documentation](https://fastapi.tiangolo.com/learn/)
- [AutoGen Framework Documentation](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/index.html)
- [Azure Container App documentation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-custom-container?tabs=core-tools%2Cacr%2Cazure-cli2%2Cazure-cli&pivots=container-apps)
- [Azure OpenAI Service - Documentation, quickstarts, API reference - Azure AI services | Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data)
- [Azure Cosmos DB documentation](https://learn.microsoft.com/en-us/azure/cosmos-db/)
  

<h2><img src="./documentation/images/readme/customerTruth.png" width="64">
</br>
Customer truth
</h2>
Customer stories coming soon.

<br/>
<br/>
<br/>

---

## Disclaimers

To the extent that the Software includes components or code used in or derived from Microsoft products or services, including without limitation Microsoft Azure Services (collectively, “Microsoft Products and Services”), you must also comply with the Product Terms applicable to such Microsoft Products and Services. You acknowledge and agree that the license governing the Software does not grant you a license or other right to use Microsoft Products and Services. Nothing in the license or this ReadMe file will serve to supersede, amend, terminate or modify any terms in the Product Terms for any Microsoft Products and Services. 

You must also comply with all domestic and international export laws and regulations that apply to the Software, which include restrictions on destinations, end users, and end use. For further information on export restrictions, visit https://aka.ms/exporting. 

You acknowledge that the Software and Microsoft Products and Services (1) are not designed, intended or made available as a medical device(s), and (2) are not designed or intended to be a substitute for professional medical advice, diagnosis, treatment, or judgment and should not be used to replace or as a substitute for professional medical advice, diagnosis, treatment, or judgment. Customer is solely responsible for displaying and/or obtaining appropriate consents, warnings, disclaimers, and acknowledgements to end users of Customer’s implementation of the Online Services. 

You acknowledge the Software is not subject to SOC 1 and SOC 2 compliance audits. No Microsoft technology, nor any of its component technologies, including the Software, is intended or made available as a substitute for the professional advice, opinion, or judgement of a certified financial services professional. Do not use the Software to replace, substitute, or provide professional financial advice or judgment.  

BY ACCESSING OR USING THE SOFTWARE, YOU ACKNOWLEDGE THAT THE SOFTWARE IS NOT DESIGNED OR INTENDED TO SUPPORT ANY USE IN WHICH A SERVICE INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE COULD RESULT IN THE DEATH OR SERIOUS BODILY INJURY OF ANY PERSON OR IN PHYSICAL OR ENVIRONMENTAL DAMAGE (COLLECTIVELY, “HIGH-RISK USE”), AND THAT YOU WILL ENSURE THAT, IN THE EVENT OF ANY INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE, THE SAFETY OF PEOPLE, PROPERTY, AND THE ENVIRONMENT ARE NOT REDUCED BELOW A LEVEL THAT IS REASONABLY, APPROPRIATE, AND LEGAL, WHETHER IN GENERAL OR IN A SPECIFIC INDUSTRY. BY ACCESSING THE SOFTWARE, YOU FURTHER ACKNOWLEDGE THAT YOUR HIGH-RISK USE OF THE SOFTWARE IS AT YOUR OWN RISK.  

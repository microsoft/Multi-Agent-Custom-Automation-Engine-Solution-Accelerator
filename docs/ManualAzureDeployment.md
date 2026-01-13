# Manual Azure Deployment

Manual Deployment differs from the ‘Quick Deploy’ option in that it will install an Azure Container Registry (ACR) service, and relies on the installer to build and push the necessary containers to this ACR. This allows you to build and push your own code changes and provides a sample solution you can customize based on your requirements.

## Prerequisites

- Current Azure CLI installed
  You can update to the latest version using `az upgrade`
- Azure account with appropriate permissions
- Docker installed

## Deploy the Azure Services

All of the necessary Azure services can be deployed using the /deploy/macae.bicep script. This script will require the following parameters:

```
az login
az account set --subscription <SUBSCRIPTION_ID>
az group create --name <RG_NAME> --location <RG_LOCATION>
```

To deploy the script you can use the Azure CLI.

```
az deployment group create \
  --resource-group <RG_NAME> \
  --template-file <BICEP_FILE> \
  --name <DEPLOYMENT_NAME>
```

Note: if you are using windows with PowerShell, the continuation character (currently ‘\’) should change to the tick mark (‘`’).

The template will require you fill in locations for Cosmos and OpenAI services. This is to avoid the possibility of regional quota errors for either of these resources.

## Create the Containers

- Get admin credentials from ACR

Retrieve the admin credentials for your Azure Container Registry (ACR):

```sh
az acr credential show \
--name <e.g. macaeacr2t62qyozi76bs> \
--resource-group <rg-name>
```

## Login to ACR

Login to your Azure Container Registry:

```sh
az acr login --name <e.g. macaeacr2t62qyozi76bs>
```

## Build and push the image

Build the frontend and backend Docker images and push them to your Azure Container Registry. Run the following from the src/backend and the src/frontend directory contexts:

```sh
az acr build \
--registry <e.g. macaeacr2t62qyozi76bs> \
--resource-group <rg-name> \
--image <e.g. backendmacae:latest> .
```

## Add images to the Container APP and Web App services

To add your newly created backend image:

- Navigate to the Container App Service in the Azure portal
- Click on Application/Containers in the left pane
- Click on the "Edit and deploy" button in the upper left of the containers pane
- In the "Create and deploy new revision" page, click on your container image 'backend'. This will give you the option of reconfiguring the container image, and also has an Environment variables tab
- Change the properties page to
  - point to your Azure Container registry with a private image type and your image name (e.g. backendmacae:latest)
  - under "Authentication type" select "Managed Identity" and choose the 'mace-containerapp-pull'... identity setup in the bicep template
- In the environment variables section add the following (each with a 'Manual entry' source):

        name: 'COSMOSDB_ENDPOINT'
        value: \<Cosmos endpoint>

        name: 'COSMOSDB_DATABASE'
        value: 'macae'
      Note: To change the default, you will need to create the database in Cosmos

        name: 'COSMOSDB_CONTAINER'
        value: 'memory'

        name: 'AZURE_OPENAI_ENDPOINT'
        value: <Azure OpenAI endpoint>

        name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
        value: 'gpt-4o'

        name: 'AZURE_OPENAI_API_VERSION'
        value: '2024-08-01-preview'
      Note: Version should be updated based on latest available

        name: 'FRONTEND_SITE_NAME'
        value: 'https://<website Name>.azurewebsites.net'

        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: <Application Insights Connection String>

- Click 'Save' and deploy your new revision

To add the new container to your website run the following:

```
az webapp config container set --resource-group <resource_group_name> \
--name <container_name> \
--container-image-name <e.g. macaeacr2t62qyozi76bs.azurecr.io/frontendmacae:latest>  \
--container-registry-url <e.g. https://macaeacr2t62qyozi76bs.azurecr.io>
```

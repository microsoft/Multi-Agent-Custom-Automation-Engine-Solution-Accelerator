# VS Code for the Web - Azure AI Foundry Templates

We've generated a simple development environment for you to deploy the templates.

The Azure AI Foundry extension provides tools to help you build, test, and deploy AI models and AI Applications directly from VS Code. It offers simplified operations for interacting with your models, agents, and threads without leaving your development environment. Click on the Azure AI Foundry Icon on the left to see more.

Follow the instructions below to get started!

You should see a terminal opened with the template code already cloned.

## Deploy the template 

You can provision and deploy this template using:

```bash
azd up
```

Follow any instructions from the deployment script and launch the application.


If you need to delete the deployment and stop incurring any charges, run:

```bash
azd down
```

## Continuing on your local desktop

You can keep working locally on VS Code Desktop by clicking "Continue On Desktop..." at the bottom left of this screen. Be sure to take the .env file with you using these steps:

- Right-click the .env file
- Select "Download"
- Move the file from your Downloads folder to the local git repo directory
- For Windows, you will need to rename the file back to .env using right-click "Rename..."

## More examples

Check out [Azure AI Projects client library for Python](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/README.md) for more information on using this SDK.

## Troubleshooting

- If you are instantiating your client via endpoint on an Azure AI Foundry project, ensure the endpoint is set in the `.env` as https://{your-foundry-resource-name}.services.ai.azure.com/api/projects/{your-foundry-project-name}`
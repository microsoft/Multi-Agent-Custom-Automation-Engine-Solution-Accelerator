# Guide to local development

## Requirements:

- Python 3.10 or higher + PIP
- Azure CLI, and an Azure Subscription
- Visual Studio Code IDE

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

   - You can use the Bicep extension for VSCode (Right-click the `.bicep` file, then select "Show deployment plane") or use the Azure CLI:
     ```bash
     az deployment group create -g <resource-group-name> -f deploy/macae-dev.bicep --query 'properties.outputs'
     ```
   - **Note**: You will be prompted for a `principalId`, which is the ObjectID of your user in Entra ID. To find it, use the Azure Portal or run:
     ```bash
     az ad signed-in-user show --query id -o tsv
     ```
     You will also be prompted for locations for Cosmos and Open AI services.  This is to allow separate regions where there may be service quota restrictions.

   - **Additional Notes**:

     **Role Assignments in Bicep Deployment:**
     
      The **macae-dev.bicep** deployment includes the assignment of the appropriate roles to AOAI and Cosmos services. If you want to modify an existing implementation—for example, to use resources deployed as part of the simple deployment for local debugging—you will need to add your own credentials to access the Cosmos and AOAI services. You can add these permissions using the following commands:
     ```bash
     az cosmosdb sql role assignment create --resource-group <solution-accelerator-rg> --account-name <cosmos-db-account-name> --role-definition-name "Cosmos DB Built-in Data Contributor" --principal-id <aad-user-object-id> --scope /subscriptions/<subscription-id>/resourceGroups/<solution-accelerator-rg>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-db-account-name>
     ```

     ```bash
     az role assignment create --assignee <aad-user-upn> --role "Cognitive Services OpenAI User" --scope /subscriptions/<subscription-id>/resourceGroups/<solution-accelerator-rg>/providers/Microsoft.CognitiveServices/accounts/<azure-openai-account-name>
     ```
		**Using a Different Database in Cosmos:**

		You can set the solution up to use a different database in Cosmos. For example, you can name it something like autogen-dev. To do this:
		1. Change the environment variable **COSMOSDB_DATABASE** to the new database name.
 		2. You will need to create the database in the Cosmos DB account. You can do this from the Data Explorer pane in the portal, click on the drop down labeled “_+ New Container_” and provide all the necessary details.

6. **Create a `.env` file:**

   - Navigate to the `src` folder and create a `.env` file based on the provided `.env.sample` file.

7. **Fill in the `.env` file:**

   - Use the output from the deployment or check the Azure Portal under "Deployments" in the resource group.

8. **(Optional) Set up a virtual environment:**

   - If you are using `venv`, create and activate your virtual environment for both the frontend and backend folders.

9. **Install requirements - frontend:**

   - In each of the frontend and backend folders -
     Open a terminal in the `src` folder and run:
     ```bash
     pip install -r requirements.txt
     ```

10. **Run the application:**
   - From the src/backend directory:
   ```bash
   python app.py
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


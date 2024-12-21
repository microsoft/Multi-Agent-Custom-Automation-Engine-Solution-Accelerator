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
     az login --tenant 16b3c013-0000-0000-0000-000000000
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
     You will also be prompted for locations for Cosmos and Open AI services.  This is to allow separate regions where there may be service quota restrictions

5. **Create a `.env` file:**

   - Navigate to the `src` folder and create a `.env` file based on the provided `.env.sample` file.

6. **Fill in the `.env` file:**

   - Use the output from the deployment or check the Azure Portal under "Deployments" in the resource group.

7. **(Optional) Set up a virtual environment:**

   - If you are using `venv`, create and activate your virtual environment for both the frontend and backend folders.

8. **Install requirements - frontend:**

   - In each of the frontend and backend folders -
     Open a terminal in the `src` folder and run:
     ```bash
     pip install -r requirements.txt
     ```

9. **Run the application:**
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


# Creating a new App Registration

1. Click on `Home` and select `Microsoft Entra ID`.

![Microsoft Entra ID](images/azure-app-service-auth-setup/MicrosoftEntraID.png)

2. Click on `App registrations`.

![App registrations](images/azure-app-service-auth-setup/Appregistrations.png)

3. Click on `+ New registration`.

![New Registrations](images/azure-app-service-auth-setup/NewRegistration.png)

4. Provide the `Name`, select supported account types as `Accounts in this organizational directory only(Contoso only - Single tenant)`, select platform as `Web`, enter/select the `URL` and register.

![Add Details](images/azure-app-service-auth-setup/AddDetails.png)

5. After application is created successfully, then click on `Add a Redirect URL`.

![Redirect URL](images/azure-app-service-auth-setup/AddRedirectURL.png)

6. Click on `+ Add a platform`.

![+ Add platform](images/azure-app-service-auth-setup/AddPlatform.png)

7. Click on `Web`.

![Web](images/azure-app-service-auth-setup/Web.png)

8. Enter the `web app URL` (Provide the app service name in place of XXXX) and Save. Then go back to [Set Up Authentication in Azure App Service](azure_app_service_auth_setup.md) Step 1 page and follow from _Point 4_ choose `Pick an existing app registration in this directory` from the Add an Identity Provider page and provide the newly registered App Name.

E.g. <<https://<< appservicename >>.azurewebsites.net/.auth/login/aad/callback>>

![Add Details](images/azure-app-service-auth-setup/WebAppURL.png)

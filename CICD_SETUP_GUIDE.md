# CI/CD Setup Guide

This guide will help you set up a complete CI/CD pipeline for the Multi-Agent Custom Automation Engine solution to automatically deploy changes from your local development to Azure.

## Prerequisites Checklist

✅ Azure subscription with admin access  
✅ GitHub account  
✅ Local development environment with git, azd, and Azure CLI  

## Step 1: Fork and Configure Repository

### 1.1 Fork the Repository
1. Go to https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator
2. Click "Fork" in the top right corner
3. Create the fork in your GitHub account

### 1.2 Update Local Repository
```powershell
# You've already done this step - just for reference
git remote rename origin upstream
git remote add origin https://github.com/YOUR-USERNAME/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator.git
```

## Step 2: Create Azure Service Principal

Since the automated setup failed due to permissions, create the service principal manually:

### 2.1 Create Service Principal via Azure Portal
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Click "New registration"
3. Name: `github-actions-macae-cicd`
4. Click "Register"
5. Note down:
   - Application (client) ID
   - Directory (tenant) ID

### 2.2 Create Client Secret
1. In your app registration, go to "Certificates & secrets"
2. Click "New client secret"
3. Add description: "GitHub Actions CICD"
4. Set expiration (recommended: 12 months)
5. Copy the secret value (you won't see it again)

### 2.3 Assign Permissions
1. Go to Subscriptions → Your Subscription → Access control (IAM)
2. Click "Add role assignment"
3. Role: "Contributor"
4. Assign access to: "User, group, or service principal"
5. Select your service principal
6. Click "Save"

## Step 3: Configure GitHub Secrets

In your GitHub repository, go to Settings → Secrets and variables → Actions:

### 3.1 Required Secrets
```
AZURE_CLIENT_ID: [Your service principal client ID]
AZURE_TENANT_ID: [Your tenant ID]
AZURE_SUBSCRIPTION_ID: 6e146a14-b670-478e-8581-2ace792c7675
```

### 3.2 Optional Variables (Repository Variables)
```
AZURE_LOCATION: eastus2
```

## Step 4: GitHub Environments (Optional but Recommended)

Create environments for better deployment control:

1. Go to Settings → Environments
2. Create "development" environment
3. Create "production" environment
4. Add protection rules for production (require reviews, restrict branches to main)

## Step 5: Test Your Pipeline

### 5.1 Initial Deployment Test
1. Create a small change in your repository
2. Commit and push to a feature branch
3. Create a Pull Request to see tests run
4. Merge to main to trigger deployment

### 5.2 Local Development Workflow

For local development and testing:

```powershell
# Set up local environment
azd env new your-dev-env
azd env select your-dev-env
azd env set AZURE_LOCATION eastus2

# Test deployment locally first
azd provision --preview
azd up

# After making changes, test locally then push
git add .
git commit -m "Your changes"
git push origin your-feature-branch
```

## Step 6: Monitoring and Troubleshooting

### 6.1 Monitor Deployments
- GitHub Actions tab for pipeline status
- Azure Portal for resource status
- Application Insights for application logs

### 6.2 Common Issues
1. **Permission errors**: Ensure service principal has Contributor role
2. **Quota issues**: Check Azure OpenAI quota in your region
3. **Build failures**: Check Docker build logs in Actions

### 6.3 Getting Deployment Logs
```powershell
# Local debugging
azd logs

# In GitHub Actions, logs are available in the workflow run
```

## Step 7: Advanced Configuration

### 7.1 Multi-Environment Setup
Modify the `azure.yaml` and Bicep parameters for different environments:
- Development: Smaller SKUs, basic security
- Production: Production SKUs, enhanced security

### 7.2 Custom Domains and SSL
Configure custom domains in Azure Container Apps after deployment.

### 7.3 Monitoring and Alerts
Set up Azure Monitor alerts for application health and performance.

## Security Best Practices

1. **Secrets Management**: Never commit secrets to code
2. **Least Privilege**: Service principal should have minimal required permissions
3. **Environment Protection**: Use GitHub environment protection rules
4. **Regular Rotation**: Rotate service principal secrets regularly
5. **Monitoring**: Monitor deployment activities and access

## Troubleshooting Commands

```powershell
# Check azd status
azd env list
azd env get-values

# Check Azure resources
az group list --output table
az resource list --resource-group YOUR-RG --output table

# Check GitHub Actions locally
gh run list
gh run view [run-id]
```

## Next Steps

1. Complete the service principal setup
2. Configure GitHub secrets
3. Test the pipeline with a small change
4. Set up monitoring and alerts
5. Configure custom domains if needed

This setup provides you with:
- ✅ Automated testing on every PR
- ✅ Automatic deployment to Azure on main branch
- ✅ Security scanning
- ✅ Environment-specific deployments
- ✅ Easy rollback capabilities
- ✅ Comprehensive logging and monitoring

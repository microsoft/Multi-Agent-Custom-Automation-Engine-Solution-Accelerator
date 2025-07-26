# Multi-Agent Custom Automation Engine - Local Development Guide

## Quick Setup for Local Development and CI/CD

This guide helps you set up local development and CI/CD for the Multi-Agent Custom Automation Engine.

## 🚀 Quick Start

### 1. Test Local Deployment
```bash
# Make the script executable
chmod +x scripts/test-deployment.sh

# Run the test deployment
./scripts/test-deployment.sh
```

### 2. Set Up CI/CD Pipeline

Follow these steps to enable automated deployments:

#### Option A: Using Service Principal (Traditional)
1. **Fork the repository** to your GitHub account
2. **Create Azure Service Principal:**
   ```bash
   az ad sp create-for-rbac --name "github-actions-macae" --role contributor --scopes /subscriptions/6e146a14-b670-478e-8581-2ace792c7675
   ```
3. **Configure GitHub Secrets:**
   - `AZURE_CLIENT_ID`: Service principal client ID
   - `AZURE_CLIENT_SECRET`: Service principal secret
   - `AZURE_TENANT_ID`: Your tenant ID
   - `AZURE_SUBSCRIPTION_ID`: `6e146a14-b670-478e-8581-2ace792c7675`

#### Option B: Using Federated Credentials (Recommended)
1. **Create App Registration** in Azure Portal
2. **Configure Federated Credentials** for GitHub Actions
3. **Set GitHub Variables** (not secrets):
   - `AZURE_CLIENT_ID`: App registration client ID
   - `AZURE_TENANT_ID`: Your tenant ID
   - `AZURE_SUBSCRIPTION_ID`: `6e146a14-b670-478e-8581-2ace792c7675`

## 🔄 Development Workflow

### Daily Development
```bash
# 1. Make your changes
git checkout -b feature/your-feature

# 2. Test locally
./scripts/test-deployment.sh

# 3. Commit and push
git add .
git commit -m "Add your feature"
git push origin feature/your-feature

# 4. Create Pull Request
# 5. After review, merge to main
# 6. CI/CD automatically deploys to production
```

### Environment Management
```bash
# List environments
azd env list

# Switch environment
azd env select your-env

# View environment variables
azd env get-values

# Clean up test environment
azd down --force --purge
```

## 📁 Repository Structure

```
├── .github/workflows/          # CI/CD pipelines
│   ├── cicd-deploy.yml        # Main CI/CD pipeline
│   └── deploy-federated.yml   # Federated credential deployment
├── infra/                     # Infrastructure as Code (Bicep)
├── src/
│   ├── backend/              # Python FastAPI backend
│   └── frontend/             # React frontend
├── scripts/
│   └── test-deployment.sh    # Local deployment testing
├── azure.yaml                # Azure Developer CLI configuration
└── CICD_SETUP_GUIDE.md      # Detailed setup guide
```

## 🛠️ Key Commands

```bash
# Azure Developer CLI
azd up                        # Deploy everything
azd provision                 # Deploy infrastructure only
azd deploy                    # Deploy application only
azd down                      # Delete resources

# Local testing
azd provision --preview       # Preview changes
azd logs                      # View application logs

# Docker testing
docker build -t macae-backend src/backend/
docker build -t macae-frontend src/frontend/
```

## 🔧 Configuration

### Environment Variables
Set these in your azd environment:
```bash
azd env set AZURE_LOCATION eastus2
azd env set AZURE_SUBSCRIPTION_ID 6e146a14-b670-478e-8581-2ace792c7675
```

### Bicep Parameters
Customize deployment in `infra/main.parameters.json`:
- `useWafAlignedArchitecture`: true for production, false for dev
- `gptModelCapacity`: Adjust based on your needs
- `solutionLocation`: Your preferred Azure region

## 🚨 Troubleshooting

### Common Issues
1. **Permission Errors**: Ensure service principal has Contributor role
2. **Quota Issues**: Check Azure OpenAI quota in your region
3. **Build Failures**: Check Docker build context and dependencies

### Getting Help
```bash
# Check deployment status
azd env get-values

# View logs
azd logs

# Check Azure resources
az resource list --resource-group $(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2)
```

## 📊 Monitoring

After deployment, monitor your application:
- **Application URL**: Check `azd env get-values` for WEBAPP_URL
- **Azure Portal**: Monitor resources and costs
- **Application Insights**: View telemetry and logs
- **GitHub Actions**: Monitor deployment pipelines

## 🔐 Security

- Never commit secrets to code
- Use managed identities when possible
- Rotate service principal secrets regularly
- Use GitHub environment protection rules
- Enable security scanning in CI/CD

This setup gives you:
✅ Local development and testing  
✅ Automated CI/CD pipeline  
✅ Infrastructure as Code  
✅ Environment isolation  
✅ Security best practices  
✅ Monitoring and logging  

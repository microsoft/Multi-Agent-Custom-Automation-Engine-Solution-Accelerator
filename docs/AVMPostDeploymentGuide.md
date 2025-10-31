# AVM Post Deployment Guide

> **📋 Note**: This guide is specifically for post-deployment steps after using the AVM template. For complete deployment from scratch, see the main [Deployment Guide](./DeploymentGuide.md).

---

This document provides guidance on post-deployment steps after deploying the Multi-Agent Custom Automation Engine Solution Accelerator from the [AVM (Azure Verified Modules) repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/multi-agent-custom-automation-engine).

## Overview

After deploying the infrastructure using AVM, you'll need to complete the application layer setup, which includes:
- Configuring team agent configurations
- Processing and uploading sample datasets
- Setting up Azure AI Search indexes
- Configuring blob storage containers
- Setting up application authentication

## Prerequisites

Before starting the post-deployment process, ensure you have the following:

### Required Software

1. **[PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell?view=powershell-7.4)** <small>(v7.0+ recommended)</small> - Available for Windows, macOS, and Linux

2. **[Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)** <small>(v2.50+)</small> - Command-line tool for managing Azure resources

3. **[Python](https://www.python.org/downloads/)** <small>(v3.9+ recommended)</small> - Required for data processing scripts

4. **[Git](https://git-scm.com/downloads/)** - Version control system for cloning the repository

### Azure Requirements

5. **Azure Access** - One of the following roles on the subscription or resource group:
   - `Contributor` 
   - `Owner`

6. **Deployed Infrastructure** - A successful Multi-Agent Custom Automation Engine deployment from the [AVM repository](https://github.com/Azure/bicep-registry-modules/tree/main/avm/ptn/sa/multi-agent-custom-automation-engine)

#### **Important Note for PowerShell Users**

If you encounter issues running PowerShell scripts due to execution policy restrictions, you can temporarily adjust the `ExecutionPolicy` by running the following command in an elevated PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

This will allow the scripts to run for the current session without permanently changing your system's policy.

## Post-Deployment Steps

### Step 1: Clone the Repository

First, clone this repository to access the post-deployment scripts:

```powershell
git clone https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator.git
```
```powershell
cd Multi-Agent-Custom-Automation-Engine-Solution-Accelerator
```

### Step 2: Run the Post-Deployment Script

The post-deployment process is automated through a single PowerShell or Bash script that completes the following tasks in approximately 5-10 minutes:

#### What the Script Does:
1. **Configure Team Agent Settings** - Upload HR, Marketing, and Retail team configurations
2. **Process Sample Datasets** - Upload and index sample customer data, analytics, and business metrics
3. **Set Up Azure AI Search** - Create and configure search indexes for agent data retrieval
4. **Configure Blob Storage** - Set up containers for document and data storage

#### Execute the Script:

1. **Choose the appropriate command based on your deployment method and OS:**

   **If you deployed using custom templates, ARM/Bicep deployments, or `az deployment group` commands:**

   - **For PowerShell (Windows/Linux/macOS):**
     ```powershell
     .\infra\scripts\Team-Config-And-Data.ps1 -ResourceGroup "<your-resource-group-name>"
     ```

   - **For Bash (Linux/macOS/WSL):**
     ```bash
     bash infra/scripts/team_config_and_data.sh "<your-resource-group-name>"
     ```
   
   **If you deployed using `azd up` command:**

   - **For PowerShell (Windows/Linux/macOS):**
     ```powershell
     .\infra\scripts\Team-Config-And-Data.ps1
     ```

   - **For Bash (Linux/macOS/WSL):**
     ```bash
     bash infra/scripts/team_config_and_data.sh
     ```
   
   > **Note**: Replace `<your-resource-group-name>` with the actual name of the resource group containing your deployed Azure resources.

   > **💡 Tip**: Since this guide is for AVM deployments, you'll most likely use the first command with the `-ResourceGroup` parameter.

### Step 3: Provide Required Information

During script execution, you'll be prompted for:

- You'll be prompted to authenticate with Azure if not already logged in
- Select the appropriate Azure subscription

#### Resource Validation
- The script will automatically detect and validate your deployed Azure resources
- Confirmation prompts will appear before making configuration changes

### Step 4: Post Deployment Script Completion

Upon successful completion, you'll see a success message.

**🎉 Congratulations!** Your post-deployment configuration is complete.

### Step 5: Set Up App Authentication (Optional)

Follow the steps in [Set Up Authentication in Azure App Service](azure_app_service_auth_setup.md) to add app authentication to your web app running on Azure App Service.
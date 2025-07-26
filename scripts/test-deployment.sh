#!/bin/bash

# Quick deployment test script
# This script helps you test your deployment locally before pushing to CI/CD

set -e

echo "🚀 Multi-Agent Custom Automation Engine - Local Deployment Test"
echo "================================================================"

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v azd >/dev/null 2>&1 || { echo "❌ azd is required but not installed. Install from https://aka.ms/install-azd"; exit 1; }
command -v az >/dev/null 2>&1 || { echo "❌ Azure CLI is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }

echo "✅ All prerequisites found"

# Check Azure login
echo "🔐 Checking Azure authentication..."
if ! az account show >/dev/null 2>&1; then
    echo "❌ Not logged in to Azure. Please run 'az login'"
    exit 1
fi

echo "✅ Azure authentication verified"

# Set environment variables
export AZURE_SUBSCRIPTION_ID="6e146a14-b670-478e-8581-2ace792c7675"
export AZURE_LOCATION="eastus2"
export AZURE_ENV_NAME="test-$(date +%s)"

echo "🎯 Using environment: $AZURE_ENV_NAME"
echo "📍 Using location: $AZURE_LOCATION"

# Initialize environment
echo "🔧 Initializing azd environment..."
azd env new $AZURE_ENV_NAME --location $AZURE_LOCATION --subscription $AZURE_SUBSCRIPTION_ID

# Run pre-flight checks
echo "🔍 Running pre-flight checks..."
echo "Checking quota availability..."

# Preview deployment
echo "👀 Previewing deployment (what-if analysis)..."
azd provision --preview

read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Deploy
echo "🚀 Starting deployment..."
azd up --no-prompt

# Get deployment results
echo "📊 Deployment Results:"
echo "====================="
azd env get-values

# Test endpoints
echo "🧪 Testing deployment..."
WEBAPP_URL=$(azd env get-values | grep WEBAPP_URL | cut -d'=' -f2 | tr -d '"')
if [ ! -z "$WEBAPP_URL" ]; then
    echo "🌐 Application URL: $WEBAPP_URL"
    echo "Testing health endpoint..."
    curl -f "$WEBAPP_URL/health" || echo "⚠️  Health check failed"
else
    echo "⚠️  Could not find application URL"
fi

echo ""
echo "✅ Deployment completed successfully!"
echo "🗂️  Environment: $AZURE_ENV_NAME"
echo "🌐 URL: $WEBAPP_URL"
echo ""
echo "💡 To clean up this test deployment, run:"
echo "   azd down --force --purge"

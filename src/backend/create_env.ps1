@"
# Multi-Agent Custom Automation Engine - Backend Configuration
# Development Environment

# Application Environment
APP_ENV=dev

# Application Insights (required - use dummy value for local dev)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=00000000-0000-0000-0000-000000000000

# Azure OpenAI (required - replace with your values)
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-11-20

# Azure AI Project (required - replace with your values)
AZURE_AI_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
AZURE_AI_RESOURCE_GROUP=your-resource-group
AZURE_AI_PROJECT_NAME=your-project-name
AZURE_AI_AGENT_ENDPOINT=https://your-ai-project.api.azureml.ms

# Azure AD / Identity (optional for local dev)
AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000
AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000000

# MCP Server Configuration
MCP_SERVER_ENDPOINT=http://localhost:8001
MCP_SERVER_NAME=MACAE MCP Server
MCP_SERVER_DESCRIPTION=Multi-Agent Custom Automation Engine MCP Tools

# Frontend Configuration
FRONTEND_SITE_NAME=http://127.0.0.1:3001

# Supported AI Models (JSON array)
SUPPORTED_MODELS=["gpt-4o","gpt-4.1-mini","gpt-4","o1-preview","o3-mini","o3"]
"@ | Out-File -FilePath ".env" -Encoding UTF8
Write-Host ".env file created successfully!"


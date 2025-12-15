"""
Root test configuration - minimal setup for all tests.
Only environment variables that should be set globally.
"""

import os
import sys
import types
from pathlib import Path

# Add backend path to sys.path for proper imports
current_file = Path(__file__)
backend_path = current_file.parent / "src" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Add agent_framework mock EARLY to avoid import errors during collection
if 'agent_framework' not in sys.modules:
    agent_framework_module = types.ModuleType('agent_framework')
    agent_framework_module.ChatOptions = type('ChatOptions', (), {'__init__': lambda self, *args, **kwargs: None})
    agent_framework_module.ChatMessage = type('ChatMessage', (), {'__init__': lambda self, *args, **kwargs: None})
    agent_framework_module.ChatAgent = type('ChatAgent', (), {'__init__': lambda self, *args, **kwargs: None})
    agent_framework_module.HostedCodeInterpreterTool = type('HostedCodeInterpreterTool', (), {'__init__': lambda self, *args, **kwargs: None})
    agent_framework_module.OpenAIModel = type('OpenAIModel', (), {'__init__': lambda self, *args, **kwargs: None})
    agent_framework_module.AzureOpenAIModel = type('AzureOpenAIModel', (), {'__init__': lambda self, *args, **kwargs: None})
    
    # Add azure submodule
    azure_module = types.ModuleType('agent_framework.azure')
    azure_module.AzureOpenAIChatClient = type('AzureOpenAIChatClient', (), {})
    agent_framework_module.azure = azure_module
    
    # Add workflows submodule
    workflows_module = types.ModuleType('agent_framework._workflows')
    workflows_module._magentic = types.ModuleType('agent_framework._workflows._magentic')
    workflows_module._magentic.AgentRunResponseUpdate = type('AgentRunResponseUpdate', (), {})
    agent_framework_module._workflows = workflows_module
    
    sys.modules['agent_framework'] = agent_framework_module
    sys.modules['agent_framework.azure'] = azure_module
    sys.modules['agent_framework._workflows'] = workflows_module
    sys.modules['agent_framework._workflows._magentic'] = workflows_module._magentic

# Add Azure monitor module mocks EARLY to avoid import errors
if 'azure.monitor.opentelemetry' not in sys.modules:
    azure_monitor_module = types.ModuleType('azure.monitor.opentelemetry')
    azure_monitor_module.configure_azure_monitor = lambda *args, **kwargs: None
    sys.modules['azure.monitor.opentelemetry'] = azure_monitor_module
    sys.modules['azure.monitor'] = types.ModuleType('azure.monitor')

# Add ALL Azure dependencies
azure_modules = [
    'azure.cosmos', 'azure.cosmos.aio', 'azure.cosmos.aio._database',
    'azure.identity', 'azure.identity.aio', 'azure.identity.aio._internal',
    'azure.ai.projects', 'azure.ai.projects.aio', 'azure.ai.projects.models',
    'azure.search', 'azure.search.documents', 'azure.search.documents.indexes',
    'azure.core', 'azure.core.exceptions'
]
for module_name in azure_modules:
    if module_name not in sys.modules:
        mock_module = types.ModuleType(module_name)
        # Add common classes and functions
        mock_module.CosmosClient = type('CosmosClient', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.PartitionKey = type('PartitionKey', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.DefaultAzureCredential = type('DefaultAzureCredential', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.AIProjectClient = type('AIProjectClient', (), {'__init__': lambda self, *args, **kwargs: None})
        # Add Azure Search classes
        mock_module.SearchIndexClient = type('SearchIndexClient', (), {'__init__': lambda self, *args, **kwargs: None})
        # Add Azure Core exceptions
        mock_module.ClientAuthenticationError = type('ClientAuthenticationError', (Exception,), {})
        mock_module.HttpResponseError = type('HttpResponseError', (Exception,), {})
        mock_module.ResourceNotFoundError = type('ResourceNotFoundError', (Exception,), {})
        sys.modules[module_name] = mock_module

# Add FastAPI and related mocks
fastapi_modules = [
    'fastapi', 'fastapi.middleware.cors', 'fastapi.encoders', 'fastapi.responses',
    'fastapi.security', 'fastapi.routing', 'fastapi.exceptions'
]
for module_name in fastapi_modules:
    if module_name not in sys.modules:
        mock_module = types.ModuleType(module_name)
        # Add common FastAPI classes
        mock_module.FastAPI = type('FastAPI', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.Request = type('Request', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.WebSocket = type('WebSocket', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.HTTPException = type('HTTPException', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.Depends = lambda x: x
        mock_module.BackgroundTasks = type('BackgroundTasks', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.CORSMiddleware = type('CORSMiddleware', (), {})
        mock_module.JSONResponse = type('JSONResponse', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.PlainTextResponse = type('PlainTextResponse', (), {'__init__': lambda self, *args, **kwargs: None})
        mock_module.jsonable_encoder = lambda x: x
        sys.modules[module_name] = mock_module

if 'uvicorn' not in sys.modules:
    uvicorn_module = types.ModuleType('uvicorn')
    uvicorn_module.run = lambda *args, **kwargs: None
    sys.modules['uvicorn'] = uvicorn_module

# Add mock for common.models.messages_af with proper classes for type annotations
if 'common.models.messages_af' not in sys.modules:
    messages_af_module = types.ModuleType('common.models.messages_af')
    
    # Define all classes found in messages_af.py to avoid import errors
    class_names = [
        'DataType', 'AgentType', 'StepStatus', 'PlanStatus', 'HumanFeedbackStatus', 
        'MessageRole', 'AgentMessageType', 'BaseDataModel', 'AgentMessage', 'Session',
        'UserCurrentTeam', 'CurrentTeamAgent', 'Plan', 'Step', 'TeamSelectionRequest',
        'TeamAgent', 'StartingTask', 'TeamConfiguration', 'PlanWithSteps', 'InputTask',
        'UserLanguage', 'AgentMessageData'
    ]
    
    # Create all classes dynamically
    for class_name in class_names:
        # Create a generic class that can be used in type annotations
        class_type = type(class_name, (), {
            '__init__': lambda self, **kwargs: setattr(self, '__dict__', kwargs)
        })
        setattr(messages_af_module, class_name, class_type)
    
    # Add some enum-like attributes for classes that need them
    messages_af_module.DataType.session = "session"
    messages_af_module.DataType.plan = "plan"
    messages_af_module.DataType.step = "step"
    messages_af_module.DataType.agent_message = "agent_message"
    messages_af_module.DataType.team_config = "team_config"
    messages_af_module.DataType.user_current_team = "user_current_team"
    messages_af_module.DataType.current_team_agent = "current_team_agent"
    messages_af_module.DataType.m_plan = "m_plan"
    messages_af_module.DataType.m_plan_message = "m_plan_message"
    
    messages_af_module.AgentType.HUMAN = "Human_Agent"
    messages_af_module.AgentType.AI = "AI_Agent"
    messages_af_module.AgentMessageType.HUMAN_AGENT = "Human_Agent"
    messages_af_module.AgentMessageType.AI_AGENT = "AI_Agent"
    
    sys.modules['common.models.messages_af'] = messages_af_module

# Set default environment variables if not already set
os.environ.setdefault('APPLICATIONINSIGHTS_CONNECTION_STRING', 'test_connection_string')
os.environ.setdefault('APP_ENV', 'dev')
os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://test.openai.azure.com/')
os.environ.setdefault('AZURE_OPENAI_API_KEY', 'test_key')
os.environ.setdefault('AZURE_OPENAI_DEPLOYMENT_NAME', 'test_deployment')
os.environ.setdefault('AZURE_OPENAI_API_VERSION', '2023-12-01-preview')
os.environ.setdefault('AZURE_AI_SUBSCRIPTION_ID', 'test_subscription_id')
os.environ.setdefault('AZURE_AI_RESOURCE_GROUP', 'test_resource_group')
os.environ.setdefault('AZURE_AI_PROJECT_NAME', 'test_project_name')
os.environ.setdefault('AZURE_AI_AGENT_ENDPOINT', 'https://test.agent.azure.com/')
os.environ.setdefault('COSMOSDB_ENDPOINT', 'https://test.documents.azure.com:443/')
os.environ.setdefault('COSMOSDB_DATABASE', 'test_database')
os.environ.setdefault('COSMOSDB_CONTAINER', 'test_container')
os.environ.setdefault('AZURE_CLIENT_ID', 'test_client_id')
os.environ.setdefault('AZURE_TENANT_ID', 'test_tenant_id')
os.environ.setdefault('AZURE_COSMOS_DB_ENDPOINT', 'https://test.cosmos.azure.com')
os.environ.setdefault('AZURE_COSMOS_DB_KEY', 'test_cosmos_key')
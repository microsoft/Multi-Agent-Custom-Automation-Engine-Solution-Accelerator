import os
import sys
import pytest
import types
import asyncio
 
# --- Provide minimal env vars so AppConfig() import doesn't fail ---
os.environ.setdefault('AZURE_OPENAI_ENDPOINT', 'https://dummy')
os.environ.setdefault('AZURE_OPENAI_API_VERSION', 'v')
os.environ.setdefault('AZURE_OPENAI_DEPLOYMENT_NAME', 'd')
os.environ.setdefault('AZURE_AI_SUBSCRIPTION_ID', 'sub')
os.environ.setdefault('AZURE_AI_RESOURCE_GROUP', 'rg')
os.environ.setdefault('AZURE_AI_PROJECT_NAME', 'pn')
os.environ.setdefault('AZURE_AI_AGENT_PROJECT_CONNECTION_STRING', 'cs')
 
# --- Stub external modules before importing app_config ---
# Stub dotenv.load_dotenv
dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda: None
sys.modules['dotenv'] = dotenv_mod
sys.modules['dotenv.load_dotenv'] = dotenv_mod
 
# Stub azure.identity
azure_pkg = types.ModuleType('azure')
identity_pkg = types.ModuleType('azure.identity')
def DummyDefaultAzureCredential():
    class C:
        def __init__(self): pass
    return C()
identity_pkg.DefaultAzureCredential = DummyDefaultAzureCredential
identity_pkg.ClientSecretCredential = lambda *args, **kwargs: 'secret'
azure_pkg.identity = identity_pkg
sys.modules['azure'] = azure_pkg
sys.modules['azure.identity'] = identity_pkg
 
# Stub azure.cosmos.aio.CosmosClient
cosmos_aio_pkg = types.ModuleType('azure.cosmos.aio')
class DummyCosmosClient:
    def __init__(self, endpoint, credential):
        self.endpoint = endpoint
        self.credential = credential
    def get_database_client(self, name):
        return f"db_client:{name}"
cosmos_aio_pkg.CosmosClient = DummyCosmosClient
sys.modules['azure.cosmos.aio'] = cosmos_aio_pkg
 
# Stub azure.ai.projects.aio.AIProjectClient
ai_projects_pkg = types.ModuleType('azure.ai.projects.aio')
class DummyAgentDefinition: pass
class DummyAgents:
    async def create_agent(self, **kwargs):
        return DummyAgentDefinition()
class DummyClient:
    agents = DummyAgents()
DummyAIProjectClient = types.SimpleNamespace(
    from_connection_string=lambda credential, conn_str: DummyClient()
)
ai_projects_pkg.AIProjectClient = DummyAIProjectClient
sys.modules['azure.ai.projects.aio'] = ai_projects_pkg
 
# Stub semantic_kernel.kernel.Kernel
sk_kernel_pkg = types.ModuleType('semantic_kernel.kernel')
sk_kernel_pkg.Kernel = lambda: 'kernel'
sys.modules['semantic_kernel.kernel'] = sk_kernel_pkg
 
# Stub semantic_kernel.contents.ChatHistory
sk_contents_pkg = types.ModuleType('semantic_kernel.contents')
sk_contents_pkg.ChatHistory = lambda *args, **kwargs: None
sys.modules['semantic_kernel.contents'] = sk_contents_pkg
 
# Stub AzureAIAgent
az_ai_agent_pkg = types.ModuleType('semantic_kernel.agents.azure_ai.azure_ai_agent')
class DummyAzureAIAgent:
    def __init__(self, client, definition, plugins):
        self.client = client
        self.definition = definition
        self.plugins = plugins
az_ai_agent_pkg.AzureAIAgent = DummyAzureAIAgent
sys.modules['semantic_kernel.agents.azure_ai.azure_ai_agent'] = az_ai_agent_pkg
 
# Stub KernelFunction for type
sk_funcs_pkg = types.ModuleType('semantic_kernel.functions')
sk_funcs_pkg.KernelFunction = lambda *args, **kwargs: (lambda f: f)
sys.modules['semantic_kernel.functions'] = sk_funcs_pkg
 
# Now import AppConfig
after_stubs = True
import importlib
AppConfig_mod = importlib.import_module('backend.app_config')
AppConfig = AppConfig_mod.AppConfig
 
@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Clear relevant env vars before each test
    for key in list(os.environ):
        if key.startswith(('AZURE_', 'COSMOSDB_', 'FRONTEND_')):
            monkeypatch.delenv(key, raising=False)
    # Re-set mandatory ones for import
    os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://dummy'
    os.environ['AZURE_OPENAI_API_VERSION'] = 'v'
    os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'] = 'd'
    os.environ['AZURE_AI_SUBSCRIPTION_ID'] = 'sub'
    os.environ['AZURE_AI_RESOURCE_GROUP'] = 'rg'
    os.environ['AZURE_AI_PROJECT_NAME'] = 'pn'
    os.environ['AZURE_AI_AGENT_PROJECT_CONNECTION_STRING'] = 'cs'
    yield
 
@pytest.fixture
def config():
    return AppConfig()
 
# Test required/optional env getters
def test_get_required_with_default(config, monkeypatch):
    monkeypatch.delenv('AZURE_OPENAI_API_VERSION', raising=False)
    # default provided
    assert config._get_required('AZURE_OPENAI_API_VERSION', 'x') == 'x'
 
@pytest.mark.parametrize('name,default,expected', [
    ('NON_EXISTENT', None, pytest.raises(ValueError)),
    ('AZURE_OPENAI_ENDPOINT', None, 'https://dummy'),
])
def test_get_required_raises_or_returns(config, name, default, expected):
    if default is None and name == 'NON_EXISTENT':
        with expected:
            config._get_required(name)
    else:
        assert config._get_required(name) == expected
 
# _get_optional
 
def test_get_optional(config, monkeypatch):
    monkeypatch.delenv('COSMOSDB_ENDPOINT', raising=False)
    assert config._get_optional('COSMOSDB_ENDPOINT', 'ep') == 'ep'
    os.environ['COSMOSDB_ENDPOINT'] = 'real'
    assert config._get_optional('COSMOSDB_ENDPOINT', 'ep') == 'real'
 
# _get_bool
 
def test_get_bool(config, monkeypatch):
    monkeypatch.setenv('FEATURE_FLAG', 'true')
    assert config._get_bool('FEATURE_FLAG')
    monkeypatch.setenv('FEATURE_FLAG', '0')
    assert not config._get_bool('FEATURE_FLAG')
 
# credentials
 
def test_get_azure_credentials_caches(config):
    cred1 = config.get_azure_credentials()
    cred2 = config.get_azure_credentials()
    assert cred1 is cred2
 
# Cosmos DB client
 
def test_get_cosmos_database_client(config):
    db = config.get_cosmos_database_client()
    assert db == 'db_client:' + config.COSMOSDB_DATABASE
 
# Kernel creation
 
def test_create_kernel(config):
    assert config.create_kernel() == 'kernel'
 
# AI project client
 
def test_get_ai_project_client(config):
    client = config.get_ai_project_client()
    assert hasattr(client, 'agents')
 
# create_azure_ai_agent
 
@pytest.mark.asyncio
async def test_create_azure_ai_agent(config):
    client = config.get_ai_project_client()
    agent = await config.create_azure_ai_agent('agent1', 'instr', tools=['t'], client=client)
    assert isinstance(agent, DummyAzureAIAgent)
    assert agent.plugins == ['t']
 
 
# ensure global config instance exists
 
def test_global_config_instance():
    from backend.app_config import config as global_config
    assert isinstance(global_config, AppConfig)
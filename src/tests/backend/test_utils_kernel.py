# src/tests/backend/test_utils_kernel.py
import os
import sys
import json
import asyncio
import pytest
import types
import requests

# Stub out app_config.config so utils_kernel can import it
import types as _types
import sys as _sys

class _DummyConfigImport:
    def create_kernel(self):
        from backend.utils_kernel import DummyKernel
        return DummyKernel()

app_cfg = _types.ModuleType("app_config")
app_cfg.config = _DummyConfigImport()
_sys.modules["app_config"] = app_cfg

# Ensure src is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Stub semantic_kernel and its submodules
sk_pkg = types.ModuleType('semantic_kernel')
sk_pkg.__path__ = []
sk_funcs = types.ModuleType('semantic_kernel.functions')
def kernel_function(name=None, description=None):
    def decorator(func): return func
    return decorator
sk_funcs.kernel_function = kernel_function
sk_funcs.KernelFunction = lambda *args, **kwargs: (lambda f: f)
sk_pkg.Kernel = type('Kernel', (), {})

sys.modules['semantic_kernel'] = sk_pkg
sys.modules['semantic_kernel.functions'] = sk_funcs

# Stub semantic_kernel.agents.azure_ai.azure_ai_agent.AzureAIAgent
agents_pkg = types.ModuleType('semantic_kernel.agents')
agents_pkg.__path__ = []
az_pkg = types.ModuleType('semantic_kernel.agents.azure_ai')
az_pkg.__path__ = []
aazure_pkg = types.ModuleType('semantic_kernel.agents.azure_ai.azure_ai_agent')
class AzureAIAgent:
    def __init__(self): pass
aazure_pkg.AzureAIAgent = AzureAIAgent

sys.modules['semantic_kernel.agents'] = agents_pkg
sys.modules['semantic_kernel.agents.azure_ai'] = az_pkg
sys.modules['semantic_kernel.agents.azure_ai.azure_ai_agent'] = aazure_pkg

# Stub azure.identity.DefaultAzureCredential
azure_pkg = types.ModuleType('azure')
identity_pkg = types.ModuleType('azure.identity')
def dummy_credential():
    class C:
        def get_token(self, scope): return types.SimpleNamespace(token='token')
    return C()
identity_pkg.DefaultAzureCredential = dummy_credential
azure_pkg.identity = identity_pkg
sys.modules['azure'] = azure_pkg
sys.modules['azure.identity'] = identity_pkg

# Stub models.messages_kernel.AgentType
models_pkg = types.ModuleType('models')
msgs_mod = types.ModuleType('models.messages_kernel')
from enum import Enum
class AgentType(Enum):
    HR = 'hr_agent'
    PROCUREMENT = 'procurement_agent'
    GENERIC = 'generic'
    PRODUCT = 'product_agent'
    MARKETING = 'marketing_agent'
    TECH_SUPPORT = 'tech_support_agent'
    HUMAN = 'human_agent'
    PLANNER = 'planner_agent'
    GROUP_CHAT_MANAGER = 'group_chat_manager'
msgs_mod.AgentType = AgentType
models_pkg.messages_kernel = msgs_mod
sys.modules['models'] = models_pkg
sys.modules['models.messages_kernel'] = msgs_mod

# Stub context.cosmos_memory_kernel.CosmosMemoryContext
context_pkg = types.ModuleType('context')
cos_pkg = types.ModuleType('context.cosmos_memory_kernel')
class _TempCosmos:
    def __init__(self, session_id, user_id):
        self.session_id = session_id
        self.user_id = user_id
cos_pkg.CosmosMemoryContext = _TempCosmos
context_pkg.cosmos_memory_kernel = cos_pkg
sys.modules['context'] = context_pkg
sys.modules['context.cosmos_memory_kernel'] = cos_pkg

# Stub kernel_agents and agent classes
ka_pkg = types.ModuleType('kernel_agents')
ka_pkg.__path__ = []
submods = [
    'agent_factory','generic_agent','group_chat_manager','hr_agent',
    'human_agent','marketing_agent','planner_agent','procurement_agent',
    'product_agent','tech_support_agent'
]
for sub in submods:
    m = types.ModuleType(f'kernel_agents.{sub}')
    sys.modules[f'kernel_agents.{sub}'] = m
    setattr(ka_pkg, sub, m)
# Stub AgentFactory
class AgentFactory:
    @staticmethod
    async def create_all_agents(session_id, user_id, temperature):
        return {}
sys.modules['kernel_agents.agent_factory'].AgentFactory = AgentFactory
# Stub other agent classes
for sub in submods:
    mod = sys.modules[f'kernel_agents.{sub}']
    cls_name = ''.join(part.title() for part in sub.split('_'))
    setattr(mod, cls_name, type(cls_name, (), {}))
sys.modules['kernel_agents'] = ka_pkg

# Import module under test
from backend.utils_kernel import (
    initialize_runtime_and_context,
    get_agents,
    load_tools_from_json_files,
    rai_success,
    agent_instances,
    config,
    CosmosMemoryContext
)

# Dummy Kernel for testing
class DummyKernel:
    pass

class DummyConfig:
    def create_kernel(self): return DummyKernel()

# Setup overrides
def setup_module(module):
    import backend.utils_kernel as uk
    uk.config = DummyConfig()
    uk.CosmosMemoryContext = _TempCosmos

@pytest.mark.asyncio
async def test_initialize_runtime_and_context_valid():
    kernel, mem = await initialize_runtime_and_context(user_id='u1')
    assert isinstance(kernel, DummyKernel)
    assert mem.user_id == 'u1'

@pytest.mark.asyncio
async def test_initialize_runtime_and_context_invalid():
    with pytest.raises(ValueError):
        await initialize_runtime_and_context()

@pytest.mark.asyncio
async def test_get_agents_caching(monkeypatch):
    class DummyAgent:
        def __init__(self, name): self.name = name
    async def fake_create_all_agents(session_id, user_id, temperature):
        return {AgentType.HR: DummyAgent('hr'), AgentType.PRODUCT: DummyAgent('prod')}
    import backend.utils_kernel as uk
    # Override the AgentFactory class in utils_kernel module completely
    FakeFactory = type('AgentFactory', (), {'create_all_agents': staticmethod(fake_create_all_agents)})
    monkeypatch.setattr(uk, 'AgentFactory', FakeFactory)

    agent_instances.clear()
    agents = await get_agents('s', 'u')
    assert isinstance(agents, dict)
    agents2 = await get_agents('s', 'u')
    assert agents2 is agents

def test_load_tools_from_json_files(tmp_path, monkeypatch, caplog):
    tools_dir = tmp_path / 'tools'
    tools_dir.mkdir()
    data = {'tools':[{'name':'foo','description':'desc','parameters':{'a':1}}]}
    (tools_dir / 'hr_tools.json').write_text(json.dumps(data))
    (tools_dir / 'bad.json').write_text('{bad')
    import backend.utils_kernel as uk
    monkeypatch.setattr(uk.os.path, 'dirname', lambda _: str(tmp_path))
    caplog.set_level('WARNING')
    funcs = load_tools_from_json_files()
    assert any(f['function']=='foo' for f in funcs)
    assert 'Error loading tool file bad.json' in caplog.text

@pytest.mark.asyncio
async def test_rai_success_missing_env(monkeypatch):
    monkeypatch.delenv('AZURE_OPENAI_ENDPOINT', raising=False)
    monkeypatch.delenv('AZURE_OPENAI_API_VERSION', raising=False)
    monkeypatch.delenv('AZURE_OPENAI_MODEL_NAME', raising=False)
    class Cred:
        def get_token(self, _): return types.SimpleNamespace(token='t')
    monkeypatch.setattr('backend.utils_kernel.DefaultAzureCredential', lambda: Cred())
    res = await rai_success('x')
    assert res is True

@pytest.mark.asyncio
async def test_rai_success_api(monkeypatch):
    monkeypatch.setenv('AZURE_OPENAI_ENDPOINT','http://e')
    monkeypatch.setenv('AZURE_OPENAI_API_VERSION','v')
    monkeypatch.setenv('AZURE_OPENAI_MODEL_NAME','n')
    class Cred:
        def get_token(self, _): return types.SimpleNamespace(token='t')
    monkeypatch.setattr('backend.utils_kernel.DefaultAzureCredential', lambda: Cred())
    class Resp:
        status_code=200
        def json(self): return {'choices':[{'message':{'content':'FALSE'}}]}
        def raise_for_status(self): pass
    monkeypatch.setattr(requests, 'post', lambda *a, **k: Resp())
    res = await rai_success('y')
    assert res is True

# New test to cover no-tools-dir path

def test_load_tools_from_json_files_no_dir(tmp_path, monkeypatch):
    # No 'tools' subdirectory exists
    import backend.utils_kernel as uk
    # Make dirname() point to a path without tools folder
    monkeypatch.setattr(uk.os.path, 'dirname', lambda _: str(tmp_path))
    funcs = load_tools_from_json_files()
    assert funcs == []

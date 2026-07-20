"""
Pytest configuration for backend tests.

This module handles proper test isolation and minimal external module mocking.
"""

import importlib.util
import os
import sys
from types import ModuleType
from unittest.mock import Mock, MagicMock

import pytest


def _setup_environment_variables():
    """Set up required environment variables for testing."""
    env_vars = {
        'APPLICATIONINSIGHTS_CONNECTION_STRING': 'InstrumentationKey=test-key',
        'AZURE_AI_SUBSCRIPTION_ID': 'test-subscription',
        'AZURE_AI_RESOURCE_GROUP': 'test-rg',
        'AZURE_AI_PROJECT_NAME': 'test-project',
        'AZURE_AI_AGENT_ENDPOINT': 'https://test.agent.endpoint.com',
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key',
        'AZURE_OPENAI_API_VERSION': '2023-05-15',
        'AZURE_OPENAI_DEPLOYMENT_NAME': 'test-deployment',
        'PROJECT_CONNECTION_STRING': 'test-connection',
        'AZURE_COSMOS_ENDPOINT': 'https://test.cosmos.azure.com',
        'AZURE_COSMOS_KEY': 'test-key',
        'AZURE_COSMOS_DATABASE_NAME': 'test-db',
        'AZURE_COSMOS_CONTAINER_NAME': 'test-container',
        'FRONTEND_SITE_NAME': 'http://localhost:3000',
        'APP_ENV': 'dev',
        'AZURE_OPENAI_RAI_DEPLOYMENT_NAME': 'test-rai-deployment',
    }
    for key, value in env_vars.items():
        os.environ.setdefault(key, value)


class _LazyClassMeta(type):
    """Metaclass for fabricated stub classes.

    Allows arbitrary *class-level* attribute access (e.g.
    ``MagenticOrchestrator._handle_response``) used by import-time monkey-patches
    in ``patches/*.py``, while the class itself remains a real, instantiable type
    usable as a base class or in ``Union`` type hints. Unknown attributes are
    lazily created as ``MagicMock`` and cached on the class so they can be read
    and reassigned.
    """

    def __getattr__(cls, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        value = MagicMock()
        setattr(cls, name, value)
        return value


def _stub_class(name, **attrs):
    """Create a real (instantiable) stub class that tolerates arbitrary
    class-attribute access via :class:`_LazyClassMeta`."""
    namespace = {'__init__': lambda self, *args, **kwargs: None}
    namespace.update(attrs)
    return _LazyClassMeta(name, (), namespace)


def _install_lazy_attrs(module):
    """Make ``from module import <AnyName>`` succeed for names not explicitly
    defined on a mock module.

    The modularity refactor imports a growing set of symbols from
    ``agent_framework`` and ``agent_framework_orchestrations`` (e.g.
    ``WorkflowRunState``, ``MagenticPlanReviewRequest``). Rather than enumerate
    every one, install a PEP 562 module ``__getattr__`` that lazily fabricates a
    real (instantiable) class for any missing attribute. Real classes—not
    ``MagicMock``—are required so names used as base classes or in ``Union``
    type hints don't raise at import time.
    """
    _cache = {}

    def __getattr__(name):  # noqa: N807 (PEP 562 module hook)
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        if name not in _cache:
            if name.isupper() or name.endswith('_PROMPT'):
                # Module-level constants (e.g. ORCHESTRATOR_*_PROMPT) are used as
                # string templates; fabricate a string rather than a class.
                _cache[name] = 'mock_prompt_string'
            else:
                _cache[name] = _stub_class(name)
        return _cache[name]

    module.__getattr__ = __getattr__


def _setup_agent_framework_mock():
    """
    Set up mock for agent_framework which is not a pip-installable package.
    This framework is used for Azure AI Agents and needs proper mocking.
    Uses ModuleType with real stub classes for names used in type annotations
    or as base classes, and MagicMock for everything else.

    When the real ``agent_framework`` distribution is installed (the CI/dev
    path that installs backend deps from ``src/backend/pyproject.toml``), the
    real packages are used and no top-level mocking is applied — installing
    mocks on top of the real packages would shadow internals they depend on
    (e.g. ``agent_framework._clients``) and break imports.
    """
    if importlib.util.find_spec('agent_framework') is not None:
        # Real agent_framework (and its companion distributions) are installed;
        # use them directly instead of substituting stubs.
        return

    if 'agent_framework' not in sys.modules:
        # Top-level: agent_framework
        mock_af = ModuleType('agent_framework')

        # Names used as base classes or in Union type hints MUST be real classes
        # to avoid SyntaxError from typing module's forward reference evaluation.
        _class_names = [
            'Agent', 'AgentResponse', 'AgentResponseUpdate', 'AgentRunUpdateEvent',
            'AgentSession', 'AgentThread', 'BaseAgent', 'ChatAgent', 'ChatMessage',
            'ChatOptions', 'Content', 'ExecutorCompletedEvent',
            'GroupChatRequestSentEvent', 'GroupChatResponseReceivedEvent',
            'HostedCodeInterpreterTool', 'HostedMCPTool',
            'InMemoryCheckpointStorage', 'MCPStreamableHTTPTool',
            'MagenticBuilder', 'MagenticOrchestratorEvent',
            'MagenticProgressLedger', 'Message', 'Role', 'UsageDetails',
            'WorkflowOutputEvent',
        ]
        for name in _class_names:
            setattr(mock_af, name, _stub_class(name))

        # Sub-module: agent_framework._types
        mock_af_types = ModuleType('agent_framework._types')
        mock_af_types.ResponseStream = _stub_class('ResponseStream')
        mock_af._types = mock_af_types
        sys.modules['agent_framework._types'] = mock_af_types

        # Sub-module: agent_framework.azure
        mock_af_azure = ModuleType('agent_framework.azure')
        mock_af_azure.AzureOpenAIChatClient = _stub_class('AzureOpenAIChatClient')
        mock_af.azure = mock_af_azure

        # Sub-module: agent_framework._workflows._magentic
        mock_af_workflows = ModuleType('agent_framework._workflows')
        mock_af_magentic = ModuleType('agent_framework._workflows._magentic')
        for name in [
            'MagenticContext', 'StandardMagenticManager',
        ]:
            setattr(mock_af_magentic, name, _stub_class(name))
        for name in [
            'ORCHESTRATOR_FINAL_ANSWER_PROMPT',
            'ORCHESTRATOR_PROGRESS_LEDGER_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT',
        ]:
            setattr(mock_af_magentic, name, "mock_prompt_string")
        mock_af_workflows._magentic = mock_af_magentic
        mock_af._workflows = mock_af_workflows
        _install_lazy_attrs(mock_af_magentic)

        # Sub-module: agent_framework._tools (provides the @tool decorator used
        # by tools/clarification_tool.py as @tool(approval_mode="always_require")).
        mock_af_tools = ModuleType('agent_framework._tools')

        def _mock_tool(*args, **kwargs):
            # Support both bare @tool and parametrized @tool(...) usage.
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]

            def _decorator(func):
                return func

            return _decorator

        mock_af_tools.tool = _mock_tool
        mock_af._tools = mock_af_tools

        _install_lazy_attrs(mock_af)

        sys.modules['agent_framework'] = mock_af
        sys.modules['agent_framework.azure'] = mock_af_azure
        sys.modules['agent_framework._workflows'] = mock_af_workflows
        sys.modules['agent_framework._workflows._magentic'] = mock_af_magentic
        sys.modules['agent_framework._tools'] = mock_af_tools

    if 'agent_framework_orchestrations' not in sys.modules:
        mock_af_orch = ModuleType('agent_framework_orchestrations')
        mock_af_orch.MagenticBuilder = _stub_class(
            'MagenticBuilder', build=lambda self: Mock())
        _install_lazy_attrs(mock_af_orch)
        sys.modules['agent_framework_orchestrations'] = mock_af_orch

        mock_af_orch_base = ModuleType('agent_framework_orchestrations._base_group_chat_orchestrator')
        for name in ['GroupChatRequestSentEvent', 'GroupChatResponseReceivedEvent']:
            setattr(mock_af_orch_base, name, _stub_class(name))
        sys.modules['agent_framework_orchestrations._base_group_chat_orchestrator'] = mock_af_orch_base

        mock_af_orch_mag = ModuleType('agent_framework_orchestrations._magentic')
        for name in ['MagenticContext', 'MagenticProgressLedger']:
            setattr(mock_af_orch_mag, name, _stub_class(name))
        # StandardMagenticManager needs a proper __init__ that accepts args/kwargs
        # because HumanApprovalMagenticManager calls super().__init__(agent, *args, **kwargs)
        setattr(mock_af_orch_mag, 'StandardMagenticManager',
                _stub_class('StandardMagenticManager'))
        for name in [
            'ORCHESTRATOR_FINAL_ANSWER_PROMPT',
            'ORCHESTRATOR_PROGRESS_LEDGER_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT',
        ]:
            setattr(mock_af_orch_mag, name, 'mock_prompt_string')
        _install_lazy_attrs(mock_af_orch_mag)
        sys.modules['agent_framework_orchestrations._magentic'] = mock_af_orch_mag

    if 'agent_framework_azure_ai' not in sys.modules:
        mock_af_ai = ModuleType('agent_framework_azure_ai')
        mock_af_ai.AzureAIClient = _stub_class('AzureAIClient')
        sys.modules['agent_framework_azure_ai'] = mock_af_ai

    if 'agent_framework_foundry' not in sys.modules:
        # agent_framework_foundry provides FoundryChatClient, imported by
        # agents/agent_template.py and orchestration/orchestration_manager.py.
        # It is not pip-installable in CI, so provide a stub. Even when the real
        # package is installed locally, its import chain depends on
        # agent_framework internals that are themselves mocked, so we always
        # substitute a lightweight stub for deterministic test collection.
        mock_af_foundry = ModuleType('agent_framework_foundry')
        mock_af_foundry.FoundryChatClient = _stub_class('FoundryChatClient')
        sys.modules['agent_framework_foundry'] = mock_af_foundry

    if 'agent_framework_openai' not in sys.modules:
        # agent_framework_openai provides OpenAIChatOptions, imported by
        # agents/agent_template.py.
        mock_af_openai = ModuleType('agent_framework_openai')
        mock_af_openai.OpenAIChatOptions = _stub_class('OpenAIChatOptions')
        sys.modules['agent_framework_openai'] = mock_af_openai


def _setup_azure_monitor_mock():
    """Mock azure.monitor.opentelemetry which may not be installed."""
    if 'azure.monitor.opentelemetry' not in sys.modules:
        mock_module = ModuleType('azure.monitor.opentelemetry')
        mock_module.configure_azure_monitor = lambda *args, **kwargs: None
        sys.modules['azure.monitor.opentelemetry'] = mock_module


def _patch_azure_ai_projects_models():
    """
    Patch azure.ai.projects.models to add names that may be missing
    in older SDK versions (e.g. PromptAgentDefinition).
    """
    try:
        import azure.ai.projects.models as models_mod
        missing_names = [
            'PromptAgentDefinition',
            'AzureAISearchAgentTool',
            'AzureAISearchToolResource',
            'AISearchIndexResource',
            'CodeInterpreterTool',
            'FileSearchTool',
            'MCPTool',
        ]
        for name in missing_names:
            if not hasattr(models_mod, name):
                setattr(models_mod, name, MagicMock())
    except ImportError:
        # azure-ai-projects not installed at all — create full mock
        sys.modules['azure.ai.projects'] = MagicMock()
        sys.modules['azure.ai.projects.models'] = MagicMock()


# Set up environment and minimal mocks before any test imports
_setup_environment_variables()
_setup_agent_framework_mock()
_setup_azure_monitor_mock()
_patch_azure_ai_projects_models()


@pytest.fixture
def mock_azure_services():
    """Fixture to provide common Azure service mocks."""
    return {
        'cosmos_client': Mock(),
        'openai_client': Mock(),
        'ai_project_client': Mock(),
        'credential': Mock(),
    }

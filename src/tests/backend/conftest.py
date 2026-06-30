"""
Pytest configuration for backend tests.

This module handles proper test isolation and minimal external module mocking.
"""

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


def _setup_agent_framework_mock():
    """
    Set up mock for agent_framework which is not a pip-installable package.
    This framework is used for Azure AI Agents and needs proper mocking.
    Uses ModuleType with real stub classes for names used in type annotations
    or as base classes, and MagicMock for everything else.
    """
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
            setattr(mock_af, name, type(name, (), {
                '__init__': lambda self, *args, **kwargs: None,
            }))

        # Sub-module: agent_framework._types
        mock_af_types = ModuleType('agent_framework._types')
        mock_af_types.ResponseStream = type('ResponseStream', (), {})
        mock_af._types = mock_af_types
        sys.modules['agent_framework._types'] = mock_af_types

        # Sub-module: agent_framework.azure
        mock_af_azure = ModuleType('agent_framework.azure')
        mock_af_azure.AzureOpenAIChatClient = type('AzureOpenAIChatClient', (), {})
        mock_af.azure = mock_af_azure

        # Sub-module: agent_framework._workflows._magentic
        mock_af_workflows = ModuleType('agent_framework._workflows')
        mock_af_magentic = ModuleType('agent_framework._workflows._magentic')
        for name in [
            'MagenticContext', 'StandardMagenticManager',
        ]:
            setattr(mock_af_magentic, name, type(name, (), {}))
        for name in [
            'ORCHESTRATOR_FINAL_ANSWER_PROMPT',
            'ORCHESTRATOR_PROGRESS_LEDGER_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT',
        ]:
            setattr(mock_af_magentic, name, "mock_prompt_string")
        mock_af_workflows._magentic = mock_af_magentic
        mock_af._workflows = mock_af_workflows

        sys.modules['agent_framework'] = mock_af
        sys.modules['agent_framework.azure'] = mock_af_azure
        sys.modules['agent_framework._workflows'] = mock_af_workflows
        sys.modules['agent_framework._workflows._magentic'] = mock_af_magentic

    if 'agent_framework_orchestrations' not in sys.modules:
        mock_af_orch = ModuleType('agent_framework_orchestrations')
        mock_af_orch.MagenticBuilder = type('MagenticBuilder', (), {
            '__init__': lambda self, *args, **kwargs: None,
            'build': lambda self: Mock(),
        })
        sys.modules['agent_framework_orchestrations'] = mock_af_orch

        mock_af_orch_base = ModuleType('agent_framework_orchestrations._base_group_chat_orchestrator')
        for name in ['GroupChatRequestSentEvent', 'GroupChatResponseReceivedEvent']:
            setattr(mock_af_orch_base, name, type(name, (), {}))
        sys.modules['agent_framework_orchestrations._base_group_chat_orchestrator'] = mock_af_orch_base

        mock_af_orch_mag = ModuleType('agent_framework_orchestrations._magentic')
        for name in ['MagenticContext', 'MagenticProgressLedger']:
            setattr(mock_af_orch_mag, name, type(name, (), {}))
        # StandardMagenticManager needs a proper __init__ that accepts args/kwargs
        # because HumanApprovalMagenticManager calls super().__init__(agent, *args, **kwargs)
        setattr(mock_af_orch_mag, 'StandardMagenticManager',
                type('StandardMagenticManager', (), {
                    '__init__': lambda self, *args, **kwargs: None
                }))
        for name in [
            'ORCHESTRATOR_FINAL_ANSWER_PROMPT',
            'ORCHESTRATOR_PROGRESS_LEDGER_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT',
            'ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT',
        ]:
            setattr(mock_af_orch_mag, name, 'mock_prompt_string')
        sys.modules['agent_framework_orchestrations._magentic'] = mock_af_orch_mag

    if 'agent_framework_azure_ai' not in sys.modules:
        mock_af_ai = ModuleType('agent_framework_azure_ai')
        mock_af_ai.AzureAIClient = type('AzureAIClient', (), {})
        sys.modules['agent_framework_azure_ai'] = mock_af_ai


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

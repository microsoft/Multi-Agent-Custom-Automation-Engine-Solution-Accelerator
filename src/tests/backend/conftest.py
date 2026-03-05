"""
Pytest configuration for backend tests.

This module handles proper test isolation and minimal external module mocking.
"""

import os
import sys
from pathlib import Path
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
    """
    if 'agent_framework' not in sys.modules:
        # Create mock agent_framework module hierarchy
        mock_af = ModuleType('agent_framework')
        mock_af_azure = ModuleType('agent_framework.azure')
        
        # Create mock classes for agent_framework
        mock_af.ChatOptions = MagicMock()
        mock_af_azure.AzureOpenAIChatClient = MagicMock()
        
        # Set up the module hierarchy
        mock_af.azure = mock_af_azure
        
        sys.modules['agent_framework'] = mock_af
        sys.modules['agent_framework.azure'] = mock_af_azure
    
    if 'agent_framework_azure_ai' not in sys.modules:
        sys.modules['agent_framework_azure_ai'] = MagicMock()


def _setup_azure_monitor_mock():
    """Mock azure.monitor.opentelemetry which may not be installed."""
    if 'azure.monitor.opentelemetry' not in sys.modules:
        mock_module = ModuleType('azure.monitor.opentelemetry')
        mock_module.configure_azure_monitor = lambda *args, **kwargs: None
        sys.modules['azure.monitor.opentelemetry'] = mock_module


# Set up environment and minimal mocks before any test imports
_setup_environment_variables()
_setup_agent_framework_mock()
_setup_azure_monitor_mock()


@pytest.fixture
def mock_azure_services():
    """Fixture to provide common Azure service mocks."""
    return {
        'cosmos_client': Mock(),
        'openai_client': Mock(),
        'ai_project_client': Mock(),
        'credential': Mock(),
    }

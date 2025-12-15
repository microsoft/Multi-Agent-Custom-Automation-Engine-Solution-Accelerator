"""
Unit tests for v4 lifecycle module (MCPEnabledBase and AzureAgentBase).

Tests cover:
- MCPEnabledBase initialization
- MCPEnabledBase open/close lifecycle
- Context manager protocol
- MCP tool preparation
- Agent registration/unregistration
- Database team agent operations
- AzureAgentBase initialization and lifecycle
- Error handling and edge cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from contextlib import AsyncExitStack
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import logging
import re
from dataclasses import dataclass

# Mock classes for dependencies
@dataclass
class MCPConfig:
    name: str
    description: str = ""
    url: str = ""

@dataclass
class TeamConfiguration:
    team_id: str
    session_id: str
    name: str
    status: str
    created: str
    created_by: str
    deployment_name: str
    user_id: str

@dataclass
class CurrentTeamAgent:
    team_id: str
    team_name: str = ""
    user_id: str = ""
    agent_foundry_id: str = ""
    agent_name: str = ""
    agent_description: str = ""
    agent_instructions: str = ""

# REMOVED massive sys.modules pollution (39 lines!) that causes test failures
# These lines were creating empty mock modules and polluting sys.modules at import time
# This prevents isinstance() checks from working properly in other test files
# REMOVED additional sys.modules pollution that causes KeyError in other test files
# This pollution was preventing test files from importing correctly

# Mock agent_framework classes (needed for local use but not polluting sys.modules)
ChatAgent = type('ChatAgent', (), {})
HostedMCPTool = type('HostedMCPTool', (), {})
MCPStreamableHTTPTool = type('MCPStreamableHTTPTool', (), {})

# Mock Azure classes - need to support async context manager protocol
class MockAsyncContextManager:
    """Base class for mocks that support async context manager protocol."""
    def __init__(self, *args, **kwargs):
        # Accept any args/kwargs to be flexible
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

class MockAgentsClient(MockAsyncContextManager):
    pass

class MockDefaultAzureCredential(MockAsyncContextManager):
    pass

class MockAzureAIAgentClient:
    def __init__(self, *args, **kwargs):
        pass

AgentsClient = MockAgentsClient
DefaultAzureCredential = MockDefaultAzureCredential
AzureAIAgentClient = MockAzureAIAgentClient
# REMOVED: More sys.modules pollution that causes KeyError in other test files
# Each test should use @patch decorators for its specific mocking needs

# Add backend path to sys.path for proper imports
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Read and exec the lifecycle.py file
lifecycle_path = Path(__file__).parent.parent.parent.parent.parent.parent / "backend" / "v4" / "magentic_agents" / "common" / "lifecycle.py"
lifecycle_content = lifecycle_path.read_text()

# Replace imports
modified_content = lifecycle_content.replace(
    "from agent_framework import (",
    "# agent_framework imported via mock #("
).replace(
    "from agent_framework_azure_ai import AzureAIAgentClient",
    "# AzureAIAgentClient imported via mock"
).replace(
    "from azure.ai.agents.aio import AgentsClient",
    "# AgentsClient imported via mock"
).replace(
    "from azure.identity.aio import DefaultAzureCredential",
    "# DefaultAzureCredential imported via mock"
).replace(
    "from common.database.database_base import DatabaseBase",
    "# DatabaseBase imported via mock"
).replace(
    "from common.models.messages_af import CurrentTeamAgent, TeamConfiguration",
    "# messages_af imported via mock"
).replace(
    "from common.utils.utils_agents import (",
    "# utils_agents imported via mock #("
).replace(
    "from v4.common.services.team_service import TeamService",
    "# TeamService imported via mock"
).replace(
    "from v4.config.agent_registry import agent_registry",
    "# agent_registry imported via mock"
).replace(
    "from v4.magentic_agents.models.agent_models import MCPConfig",
    "# MCPConfig imported via mock"
)

# Remove commented import lines
modified_content = re.sub(r'# agent_framework imported via mock #\([^)]+\)', '', modified_content)
modified_content = re.sub(r'# utils_agents imported via mock #\([^)]+\)', '', modified_content)

# Create namespace for exec
lifecycle_namespace = {
    'logging': logging,
    'AsyncExitStack': AsyncExitStack,
    'Optional': Optional,
    'Any': Any,
    'ChatAgent': ChatAgent,
    'HostedMCPTool': HostedMCPTool,
    'MCPStreamableHTTPTool': MCPStreamableHTTPTool,
    'AzureAIAgentClient': AzureAIAgentClient,
    'AgentsClient': AgentsClient,
    'DefaultAzureCredential': DefaultAzureCredential,
    'DatabaseBase': Mock,
    'CurrentTeamAgent': CurrentTeamAgent,
    'TeamConfiguration': TeamConfiguration,
    'generate_assistant_id': Mock(),
    'get_database_team_agent_id': Mock(),
    'TeamService': Mock,
    'agent_registry': Mock(),
    'MCPConfig': MCPConfig,
}

exec(modified_content, lifecycle_namespace)

# Extract the classes we need
MCPEnabledBase = lifecycle_namespace['MCPEnabledBase']
AzureAgentBase = lifecycle_namespace['AzureAgentBase']

# Create mock module for patches
lifecycle_module = type(sys)('lifecycle')
lifecycle_module.MCPEnabledBase = MCPEnabledBase
# REMOVED: Final sys.modules pollution that causes KeyError


class TestMCPEnabledBaseInit:
    """Test cases for MCPEnabledBase initialization."""

    def test_init_minimal(self):
        """Test initialization with minimal parameters."""
        base = MCPEnabledBase()
        
        assert base._stack is None
        assert base.mcp_cfg is None
        assert base.mcp_tool is None
        assert base._agent is None
        assert base.team_service is None
        assert base.team_config is None
        assert base.client is None
        assert base.project_endpoint is None
        assert base.creds is None
        assert base.memory_store is None
        assert base.agent_name is None
        assert base.agent_description is None
        assert base.agent_instructions is None
        assert base.model_deployment_name is None
        assert base.logger is not None

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        mcp_cfg = MCPConfig(name="test-mcp", description="Test MCP", url="http://test.com")
        team_service = Mock()
        team_config = Mock()
        memory_store = Mock()
        
        base = MCPEnabledBase(
            mcp=mcp_cfg,
            team_service=team_service,
            team_config=team_config,
            project_endpoint="https://project.example.com",
            memory_store=memory_store,
            agent_name="TestAgent",
            agent_description="Test agent description",
            agent_instructions="Test instructions",
            model_deployment_name="gpt-4"
        )
        
        assert base.mcp_cfg == mcp_cfg
        assert base.team_service == team_service
        assert base.team_config == team_config
        assert base.project_endpoint == "https://project.example.com"
        assert base.memory_store == memory_store
        assert base.agent_name == "TestAgent"
        assert base.agent_description == "Test agent description"
        assert base.agent_instructions == "Test instructions"
        assert base.model_deployment_name == "gpt-4"


class TestMCPEnabledBaseOpen:
    """Test cases for MCPEnabledBase open method."""

    @pytest.mark.asyncio
    async def test_open_creates_resources(self):
        """Test that open creates necessary resources."""
        # Mock agent_registry in namespace
        mock_registry = Mock()
        original_registry = lifecycle_namespace['agent_registry']
        lifecycle_namespace['agent_registry'] = mock_registry
        
        try:
            # Create a concrete subclass for testing
            class TestMCPEnabledBase(MCPEnabledBase):
                async def _after_open(self):
                    self._agent = Mock()
            
            base = TestMCPEnabledBase(project_endpoint="https://project.example.com")
            
            result = await base.open()
            
            assert result == base
            assert base._stack is not None
            assert base.creds is not None
            assert base.client is not None
            mock_registry.register_agent.assert_called_once_with(base)
        finally:
            lifecycle_namespace['agent_registry'] = original_registry

    @pytest.mark.asyncio
    @patch("v4.magentic_agents.common.lifecycle.DefaultAzureCredential")
    @patch("v4.magentic_agents.common.lifecycle.AgentsClient")
    async def test_open_already_opened(self, mock_agents_client, mock_creds):
        """Test that opening an already opened instance returns immediately."""
        class TestMCPEnabledBase(MCPEnabledBase):
            async def _after_open(self):
                self._agent = Mock()
        
        base = TestMCPEnabledBase()
        base._stack = AsyncExitStack()
        
        result = await base.open()
        
        assert result == base
        # Should not create new credentials
        mock_creds.assert_not_called()

    @pytest.mark.asyncio
    @patch("v4.magentic_agents.common.lifecycle.DefaultAzureCredential")
    @patch("v4.magentic_agents.common.lifecycle.AgentsClient")
    @patch("v4.magentic_agents.common.lifecycle.agent_registry")
    async def test_open_registry_error_handled(self, mock_registry, mock_agents_client, mock_creds):
        """Test that registry registration errors are handled gracefully."""
        mock_cred_instance = AsyncMock()
        mock_creds.return_value = mock_cred_instance
        
        mock_client_instance = AsyncMock()
        mock_agents_client.return_value = mock_client_instance
        
        mock_registry.register_agent.side_effect = Exception("Registry error")
        
        class TestMCPEnabledBase(MCPEnabledBase):
            async def _after_open(self):
                self._agent = Mock()
        
        base = TestMCPEnabledBase(project_endpoint="https://project.example.com")
        
        # Should not raise exception
        result = await base.open()
        assert result == base

    @pytest.mark.asyncio
    async def test_open_not_implemented_error(self):
        """Test that open raises NotImplementedError if _after_open not implemented."""
        base = MCPEnabledBase(project_endpoint="https://project.example.com")
        
        with patch("v4.magentic_agents.common.lifecycle.DefaultAzureCredential"):
            with patch("v4.magentic_agents.common.lifecycle.AgentsClient"):
                with pytest.raises(NotImplementedError):
                    await base.open()


class TestMCPEnabledBaseClose:
    """Test cases for MCPEnabledBase close method."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_resources(self):
        """Test that close cleans up all resources."""
        # Mock agent_registry in namespace
        mock_registry = Mock()
        original_registry = lifecycle_namespace['agent_registry']
        lifecycle_namespace['agent_registry'] = mock_registry
        
        try:
            class TestMCPEnabledBase(MCPEnabledBase):
                async def _after_open(self):
                    self._agent = Mock()
            
            base = TestMCPEnabledBase()
            mock_stack = AsyncMock()
            base._stack = mock_stack
            
            mock_agent = AsyncMock()
            mock_agent.close = AsyncMock()
            base._agent = mock_agent
            
            await base.close()
            
            mock_agent.close.assert_called_once()
            mock_registry.unregister_agent.assert_called_once_with(base)
            mock_stack.aclose.assert_called_once()
            assert base._stack is None
            assert base.mcp_tool is None
            assert base._agent is None
        finally:
            lifecycle_namespace['agent_registry'] = original_registry

    @pytest.mark.asyncio
    async def test_close_when_not_opened(self):
        """Test that close does nothing when not opened."""
        base = MCPEnabledBase()
        
        # Should not raise exception
        await base.close()
        
        assert base._stack is None

    @pytest.mark.asyncio
    @patch("v4.magentic_agents.common.lifecycle.agent_registry")
    async def test_close_handles_agent_close_error(self, mock_registry):
        """Test that close handles agent close errors gracefully."""
        class TestMCPEnabledBase(MCPEnabledBase):
            async def _after_open(self):
                pass
        
        base = TestMCPEnabledBase()
        mock_stack = AsyncMock()
        base._stack = mock_stack
        
        mock_agent = Mock()
        mock_agent.close = AsyncMock(side_effect=Exception("Close error"))
        base._agent = mock_agent
        
        # Should not raise exception
        await base.close()
        
        assert base._stack is None

    @pytest.mark.asyncio
    @patch("v4.magentic_agents.common.lifecycle.agent_registry")
    async def test_close_handles_registry_error(self, mock_registry):
        """Test that close handles registry unregister errors gracefully."""
        mock_registry.unregister_agent.side_effect = Exception("Registry error")
        
        class TestMCPEnabledBase(MCPEnabledBase):
            async def _after_open(self):
                pass
        
        base = TestMCPEnabledBase()
        mock_stack = AsyncMock()
        base._stack = mock_stack
        
        # Should not raise exception
        await base.close()
        
        assert base._stack is None


class TestMCPEnabledBaseContextManager:
    """Test cases for MCPEnabledBase context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self):
        """Test async context manager protocol."""
        class TestMCPEnabledBase(MCPEnabledBase):
            async def _after_open(self):
                self._agent = Mock()
        
        base = TestMCPEnabledBase(project_endpoint="https://project.example.com")
        
        async with base as opened_base:
            assert opened_base == base
            assert opened_base._stack is not None
        
        # After exiting context, should be closed
        assert base._stack is None


class TestMCPEnabledBaseGetAttr:
    """Test cases for MCPEnabledBase __getattr__ delegation."""

    def test_getattr_delegates_to_agent(self):
        """Test that attribute access delegates to underlying agent."""
        mock_agent = Mock()
        mock_agent.some_method = Mock(return_value="result")
        
        base = MCPEnabledBase()
        base._agent = mock_agent
        
        result = base.some_method()
        
        assert result == "result"
        mock_agent.some_method.assert_called_once()

    def test_getattr_raises_when_no_agent(self):
        """Test that attribute access raises AttributeError when no agent."""
        base = MCPEnabledBase()
        
        with pytest.raises(AttributeError) as exc_info:
            _ = base.nonexistent_attr
        
        assert "has no attribute" in str(exc_info.value)


class TestGetChatClient:
    """Test cases for get_chat_client method."""

    def test_get_chat_client_with_existing_client(self):
        """Test get_chat_client returns provided client."""
        existing_client = Mock()
        
        base = MCPEnabledBase()
        
        result = base.get_chat_client(existing_client)
        
        assert result == existing_client

    def test_get_chat_client_from_agent(self):
        """Test get_chat_client returns client from agent."""
        mock_agent = Mock()
        mock_chat_client = Mock()
        mock_chat_client.agent_id = "agent-123"
        mock_agent.chat_client = mock_chat_client
        
        base = MCPEnabledBase()
        base._agent = mock_agent
        
        result = base.get_chat_client(None)
        
        assert result == mock_chat_client

    def test_get_chat_client_creates_new(self):
        """Test get_chat_client creates new client when needed."""
        mock_new_client = Mock()
        mock_client_class = Mock(return_value=mock_new_client)
        original_client = lifecycle_namespace['AzureAIAgentClient']
        lifecycle_namespace['AzureAIAgentClient'] = mock_client_class
        
        try:
            base = MCPEnabledBase(
                project_endpoint="https://project.example.com",
                model_deployment_name="gpt-4"
            )
            base.creds = Mock()
            
            result = base.get_chat_client(None)
            
            assert result == mock_new_client
            mock_client_class.assert_called_once()
        finally:
            lifecycle_namespace['AzureAIAgentClient'] = original_client


class TestGetAgentId:
    """Test cases for get_agent_id method."""

    def test_get_agent_id_from_chat_client(self):
        """Test get_agent_id returns id from provided chat_client."""
        mock_chat_client = Mock()
        mock_chat_client.agent_id = "client-agent-123"
        
        base = MCPEnabledBase()
        
        result = base.get_agent_id(mock_chat_client)
        
        assert result == "client-agent-123"

    def test_get_agent_id_from_agent(self):
        """Test get_agent_id returns id from internal agent."""
        mock_agent = Mock()
        mock_chat_client = Mock()
        mock_chat_client.agent_id = "agent-456"
        mock_agent.chat_client = mock_chat_client
        
        base = MCPEnabledBase()
        base._agent = mock_agent
        
        result = base.get_agent_id(None)
        
        assert result == "agent-456"

    def test_get_agent_id_generates_new(self):
        """Test get_agent_id generates new id when needed."""
        mock_generate = Mock(return_value="generated-789")
        original_generate = lifecycle_namespace['generate_assistant_id']
        lifecycle_namespace['generate_assistant_id'] = mock_generate
        
        try:
            base = MCPEnabledBase()
            
            result = base.get_agent_id(None)
            
            assert result == "generated-789"
            mock_generate.assert_called_once()
        finally:
            lifecycle_namespace['generate_assistant_id'] = original_generate


class TestGetDatabaseTeamAgent:
    """Test cases for get_database_team_agent method."""

    @pytest.mark.asyncio
    async def test_get_database_team_agent_success(self):
        """Test successful database team agent retrieval."""
        mock_get_id = AsyncMock(return_value="db-agent-123")
        original_get_id = lifecycle_namespace['get_database_team_agent_id']
        lifecycle_namespace['get_database_team_agent_id'] = mock_get_id
        
        mock_new_client = Mock()
        mock_client_class = Mock(return_value=mock_new_client)
        original_client = lifecycle_namespace['AzureAIAgentClient']
        lifecycle_namespace['AzureAIAgentClient'] = mock_client_class
        
        try:
            mock_agent = Mock()
            mock_agent.id = "db-agent-123"
            
            mock_client = AsyncMock()
            mock_client.get_agent = AsyncMock(return_value=mock_agent)
            
            base = MCPEnabledBase(
                project_endpoint="https://project.example.com",
                model_deployment_name="gpt-4",
                team_config=Mock(),
                memory_store=Mock(),
                agent_name="TestAgent"
            )
            base.client = mock_client
            base.creds = Mock()
            
            result = await base.get_database_team_agent()
            
            assert result == mock_new_client
            mock_get_id.assert_called_once()
            mock_client.get_agent.assert_called_once_with(agent_id="db-agent-123")
        finally:
            lifecycle_namespace['get_database_team_agent_id'] = original_get_id
            lifecycle_namespace['AzureAIAgentClient'] = original_client

    @pytest.mark.asyncio
    async def test_get_database_team_agent_no_id(self):
        """Test database team agent retrieval when no id exists."""
        mock_get_id = AsyncMock(return_value=None)
        original_get_id = lifecycle_namespace['get_database_team_agent_id']
        lifecycle_namespace['get_database_team_agent_id'] = mock_get_id
        
        try:
            base = MCPEnabledBase(
                team_config=Mock(),
                memory_store=Mock(),
                agent_name="TestAgent"
            )
            
            result = await base.get_database_team_agent()
            
            assert result is None
        finally:
            lifecycle_namespace['get_database_team_agent_id'] = original_get_id

    @pytest.mark.asyncio
    async def test_get_database_team_agent_exception(self):
        """Test database team agent retrieval handles exceptions."""
        mock_get_id = AsyncMock(side_effect=Exception("Database error"))
        original_get_id = lifecycle_namespace['get_database_team_agent_id']
        lifecycle_namespace['get_database_team_agent_id'] = mock_get_id
        
        try:
            base = MCPEnabledBase(
                team_config=Mock(),
                memory_store=Mock(),
                agent_name="TestAgent"
            )
            
            result = await base.get_database_team_agent()
            
            assert result is None
        finally:
            lifecycle_namespace['get_database_team_agent_id'] = original_get_id


class TestSaveDatabaseTeamAgent:
    """Test cases for save_database_team_agent method."""

    @pytest.mark.asyncio
    async def test_save_database_team_agent_success(self):
        """Test successful database team agent save."""
        mock_memory = AsyncMock()
        mock_memory.add_team_agent = AsyncMock()
        
        mock_team_config = Mock()
        mock_team_config.team_id = "team-123"
        mock_team_config.name = "Test Team"
        
        mock_agent = Mock()
        mock_agent.id = "agent-456"  # Set as simple attribute
        
        base = MCPEnabledBase(
            team_config=mock_team_config,
            memory_store=mock_memory,
            agent_name="TestAgent",
            agent_description="Test Description",
            agent_instructions="Test Instructions"
        )
        base._agent = mock_agent
        
        await base.save_database_team_agent()
        
        mock_memory.add_team_agent.assert_called_once()
        call_args = mock_memory.add_team_agent.call_args[0][0]
        assert isinstance(call_args, CurrentTeamAgent)
        assert call_args.team_id == "team-123"

    @pytest.mark.asyncio
    async def test_save_database_team_agent_no_agent_id(self):
        """Test save when agent id is None."""
        mock_agent = Mock()
        mock_agent.id = None
        
        base = MCPEnabledBase(
            team_config=Mock(),
            memory_store=AsyncMock(),
            agent_name="TestAgent"
        )
        base._agent = mock_agent
        
        # Should not raise exception
        await base.save_database_team_agent()

    @pytest.mark.asyncio
    async def test_save_database_team_agent_exception(self):
        """Test save handles exceptions gracefully."""
        mock_memory = AsyncMock()
        mock_memory.add_team_agent = AsyncMock(side_effect=Exception("Database error"))
        
        mock_agent = Mock()
        mock_agent.id = "agent-456"
        
        base = MCPEnabledBase(
            team_config=Mock(team_id="team-123", name="Test"),
            memory_store=mock_memory,
            agent_name="TestAgent"
        )
        base._agent = mock_agent
        
        # Should not raise exception
        await base.save_database_team_agent()


class TestPrepareMCPTool:
    """Test cases for _prepare_mcp_tool method."""

    @pytest.mark.asyncio
    async def test_prepare_mcp_tool_success(self):
        """Test successful MCP tool preparation."""
        mock_tool = AsyncMock()
        mock_tool_class = Mock(return_value=mock_tool)
        original_tool = lifecycle_namespace['MCPStreamableHTTPTool']
        lifecycle_namespace['MCPStreamableHTTPTool'] = mock_tool_class
        
        try:
            mcp_cfg = MCPConfig(
                name="test-mcp",
                description="Test MCP",
                url="http://test.com"
            )
            
            base = MCPEnabledBase(mcp=mcp_cfg)
            base._stack = AsyncMock()
            
            await base._prepare_mcp_tool()
            
            assert base.mcp_tool == mock_tool
            mock_tool_class.assert_called_once_with(
                name="test-mcp",
                description="Test MCP",
                url="http://test.com"
            )
        finally:
            lifecycle_namespace['MCPStreamableHTTPTool'] = original_tool

    @pytest.mark.asyncio
    async def test_prepare_mcp_tool_no_config(self):
        """Test MCP tool preparation when no config provided."""
        base = MCPEnabledBase()
        base._stack = AsyncMock()
        
        await base._prepare_mcp_tool()
        
        assert base.mcp_tool is None

    @pytest.mark.asyncio
    async def test_prepare_mcp_tool_exception(self):
        """Test MCP tool preparation handles exceptions."""
        mock_tool_class = Mock(side_effect=Exception("MCP error"))
        original_tool = lifecycle_namespace['MCPStreamableHTTPTool']
        lifecycle_namespace['MCPStreamableHTTPTool'] = mock_tool_class
        
        try:
            mcp_cfg = MCPConfig(
                name="test-mcp",
                description="Test MCP",
                url="http://test.com"
            )
            
            base = MCPEnabledBase(mcp=mcp_cfg)
            base._stack = AsyncMock()
            
            await base._prepare_mcp_tool()
            
            assert base.mcp_tool is None
        finally:
            lifecycle_namespace['MCPStreamableHTTPTool'] = original_tool


class TestAzureAgentBaseInit:
    """Test cases for AzureAgentBase initialization."""

    def test_azure_agent_base_init(self):
        """Test AzureAgentBase initialization."""
        mcp_cfg = MCPConfig(name="test-mcp", description="Test", url="http://test.com")
        
        base = AzureAgentBase(
            mcp=mcp_cfg,
            model_deployment_name="gpt-4",
            project_endpoint="https://project.example.com",
            agent_name="TestAgent"
        )
        
        assert base.mcp_cfg == mcp_cfg
        assert base.model_deployment_name == "gpt-4"
        assert base.project_endpoint == "https://project.example.com"
        assert base.agent_name == "TestAgent"
        assert base._created_ephemeral is False


class TestAzureAgentBaseClose:
    """Test cases for AzureAgentBase close method."""

    @pytest.mark.asyncio
    async def test_azure_agent_base_close(self):
        """Test AzureAgentBase close method."""
        mock_registry = Mock()
        original_registry = lifecycle_namespace['agent_registry']
        lifecycle_namespace['agent_registry'] = mock_registry
        
        try:
            mock_agent = AsyncMock()
            mock_agent.close = AsyncMock()
            
            mock_client = AsyncMock()
            mock_client.close = AsyncMock()
            
            mock_creds = AsyncMock()
            mock_creds.close = AsyncMock()
            
            base = AzureAgentBase(project_endpoint="https://project.example.com")
            base._stack = AsyncMock()
            base._agent = mock_agent
            base.client = mock_client
            base.creds = mock_creds
            
            await base.close()
            
            # AzureAgentBase.close() calls agent.close(), then super().close() also calls it
            # so agent.close is called twice
            assert mock_agent.close.call_count == 2
            # client and creds are only closed once in AzureAgentBase.close()
            # super().close() doesn't close them again
            mock_client.close.assert_called_once()
            mock_creds.close.assert_called_once()
            # unregister_agent is also called twice: once in AzureAgentBase, once in super().close()
            assert mock_registry.unregister_agent.call_count == 2
            assert base.client is None
            assert base.creds is None
            assert base.project_endpoint is None
        finally:
            lifecycle_namespace['agent_registry'] = original_registry

    @pytest.mark.asyncio
    @patch("v4.magentic_agents.common.lifecycle.agent_registry")
    async def test_azure_agent_base_close_handles_errors(self, mock_registry):
        """Test AzureAgentBase close handles errors gracefully."""
        mock_agent = AsyncMock()
        mock_agent.close = AsyncMock(side_effect=Exception("Close error"))
        
        mock_client = AsyncMock()
        mock_client.close = AsyncMock(side_effect=Exception("Client error"))
        
        mock_creds = AsyncMock()
        mock_creds.close = AsyncMock(side_effect=Exception("Creds error"))
        
        base = AzureAgentBase()
        base._stack = AsyncMock()
        base._agent = mock_agent
        base.client = mock_client
        base.creds = mock_creds
        
        # Should not raise exception
        await base.close()
        
        assert base.client is None
        assert base.creds is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_multiple_open_close_cycles(self):
        """Test multiple open/close cycles."""
        class TestMCPEnabledBase(MCPEnabledBase):
            async def _after_open(self):
                self._agent = Mock()
        
        base = TestMCPEnabledBase(project_endpoint="https://project.example.com")
        
        with patch("v4.magentic_agents.common.lifecycle.DefaultAzureCredential"):
            with patch("v4.magentic_agents.common.lifecycle.AgentsClient"):
                # First cycle
                await base.open()
                assert base._stack is not None
                await base.close()
                assert base._stack is None
                
                # Second cycle
                await base.open()
                assert base._stack is not None
                await base.close()
                assert base._stack is None

    def test_mcp_config_values(self):
        """Test MCPConfig with various values."""
        mcp_cfg = MCPConfig(
            name="complex-mcp",
            description="A complex MCP tool with special chars: @#$%",
            url="https://example.com:8080/api/v1/mcp"
        )
        
        base = MCPEnabledBase(mcp=mcp_cfg)
        
        assert base.mcp_cfg.name == "complex-mcp"
        assert "@#$%" in base.mcp_cfg.description
        assert "8080" in base.mcp_cfg.url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

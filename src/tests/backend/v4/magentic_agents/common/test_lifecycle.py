"""Unit tests for backend.v4.magentic_agents.common.lifecycle module."""
import asyncio
import logging
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

# Mock the dependencies before importing the module under test
sys.modules['agent_framework'] = Mock()
sys.modules['agent_framework.azure'] = Mock() 
sys.modules['agent_framework_azure_ai'] = Mock()
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.agents'] = Mock()
sys.modules['azure.ai.agents.aio'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['common'] = Mock()
sys.modules['common.database'] = Mock()
sys.modules['common.database.database_base'] = Mock()
sys.modules['common.models'] = Mock()
sys.modules['common.models.messages_af'] = Mock()
sys.modules['common.utils'] = Mock()
sys.modules['common.utils.utils_agents'] = Mock()
sys.modules['v4'] = Mock()
sys.modules['v4.common'] = Mock()
sys.modules['v4.common.services'] = Mock()
sys.modules['v4.common.services.team_service'] = Mock()
sys.modules['v4.config'] = Mock()
sys.modules['v4.config.agent_registry'] = Mock()
sys.modules['v4.magentic_agents'] = Mock()
sys.modules['v4.magentic_agents.models'] = Mock()
sys.modules['v4.magentic_agents.models.agent_models'] = Mock()

# Create mock classes
mock_chat_agent = Mock()
mock_hosted_mcp_tool = Mock()
mock_mcp_streamable_http_tool = Mock()
mock_azure_ai_agent_client = Mock()
mock_agents_client = Mock()
mock_default_azure_credential = Mock()
mock_database_base = Mock()
mock_current_team_agent = Mock()
mock_team_configuration = Mock()
mock_team_service = Mock()
mock_agent_registry = Mock()
mock_mcp_config = Mock()

# Set up the mock modules
sys.modules['agent_framework'].ChatAgent = mock_chat_agent
sys.modules['agent_framework'].HostedMCPTool = mock_hosted_mcp_tool
sys.modules['agent_framework'].MCPStreamableHTTPTool = mock_mcp_streamable_http_tool
sys.modules['agent_framework_azure_ai'].AzureAIAgentClient = mock_azure_ai_agent_client
sys.modules['azure.ai.agents.aio'].AgentsClient = mock_agents_client
sys.modules['azure.identity.aio'].DefaultAzureCredential = mock_default_azure_credential
sys.modules['common.database.database_base'].DatabaseBase = mock_database_base
sys.modules['common.models.messages_af'].CurrentTeamAgent = mock_current_team_agent
sys.modules['common.models.messages_af'].TeamConfiguration = mock_team_configuration
sys.modules['v4.common.services.team_service'].TeamService = mock_team_service
sys.modules['v4.config.agent_registry'].agent_registry = mock_agent_registry
sys.modules['v4.magentic_agents.models.agent_models'].MCPConfig = mock_mcp_config

# Mock utility functions
sys.modules['common.utils.utils_agents'].generate_assistant_id = Mock(return_value="test-agent-id-123")
sys.modules['common.utils.utils_agents'].get_database_team_agent_id = AsyncMock(return_value="test-db-agent-id")

# Import the module under test
from backend.v4.magentic_agents.common.lifecycle import MCPEnabledBase, AzureAgentBase


class TestMCPEnabledBase:
    """Test cases for MCPEnabledBase class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_mcp_config = Mock()
        self.mock_mcp_config.name = "test-mcp"
        self.mock_mcp_config.description = "Test MCP Tool"
        self.mock_mcp_config.url = "http://test-mcp.com"
        
        self.mock_team_service = Mock()
        self.mock_team_config = Mock()
        self.mock_team_config.team_id = "team-123"
        self.mock_team_config.name = "Test Team"
        
        self.mock_memory_store = Mock()
        
        # Reset mocks
        mock_agent_registry.reset_mock()

    def test_init_with_minimal_params(self):
        """Test MCPEnabledBase initialization with minimal parameters."""
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
        assert isinstance(base.logger, logging.Logger)

    def test_init_with_full_params(self):
        """Test MCPEnabledBase initialization with all parameters."""
        base = MCPEnabledBase(
            mcp=self.mock_mcp_config,
            team_service=self.mock_team_service,
            team_config=self.mock_team_config,
            project_endpoint="https://test-endpoint.com",
            memory_store=self.mock_memory_store,
            agent_name="TestAgent",
            agent_description="Test agent description",
            agent_instructions="Test instructions",
            model_deployment_name="gpt-4"
        )
        
        assert base.mcp_cfg is self.mock_mcp_config
        assert base.team_service is self.mock_team_service
        assert base.team_config is self.mock_team_config
        assert base.project_endpoint == "https://test-endpoint.com"
        assert base.memory_store is self.mock_memory_store
        assert base.agent_name == "TestAgent"
        assert base.agent_description == "Test agent description"
        assert base.agent_instructions == "Test instructions"
        assert base.model_deployment_name == "gpt-4"

    def test_init_with_none_values(self):
        """Test MCPEnabledBase initialization with explicit None values."""
        base = MCPEnabledBase(
            mcp=None,
            team_service=None,
            team_config=None,
            project_endpoint=None,
            memory_store=None,
            agent_name=None,
            agent_description=None,
            agent_instructions=None,
            model_deployment_name=None
        )
        
        assert base.mcp_cfg is None
        assert base.team_service is None
        assert base.team_config is None
        assert base.project_endpoint is None
        assert base.memory_store is None
        assert base.agent_name is None
        assert base.agent_description is None
        assert base.agent_instructions is None
        assert base.model_deployment_name is None

    @pytest.mark.asyncio
    async def test_open_method_success(self):
        """Test successful open method execution."""
        base = MCPEnabledBase(
            project_endpoint="https://test-endpoint.com",
            mcp=self.mock_mcp_config
        )
        
        # Mock AsyncExitStack
        mock_stack = AsyncMock()
        mock_creds = AsyncMock()
        mock_client = AsyncMock()
        mock_mcp_tool = AsyncMock()
        
        with patch('backend.v4.magentic_agents.common.lifecycle.AsyncExitStack', return_value=mock_stack):
            with patch('backend.v4.magentic_agents.common.lifecycle.DefaultAzureCredential', return_value=mock_creds):
                with patch('backend.v4.magentic_agents.common.lifecycle.AgentsClient', return_value=mock_client):
                    with patch('backend.v4.magentic_agents.common.lifecycle.MCPStreamableHTTPTool', return_value=mock_mcp_tool):
                        with patch.object(base, '_after_open', new_callable=AsyncMock) as mock_after_open:
                            
                            result = await base.open()
                            
                            assert result is base
                            assert base._stack is mock_stack
                            assert base.creds is mock_creds
                            assert base.client is mock_client
                            mock_after_open.assert_called_once()
                            mock_agent_registry.register_agent.assert_called_once_with(base)

    @pytest.mark.asyncio
    async def test_open_method_already_open(self):
        """Test open method when already opened."""
        base = MCPEnabledBase()
        mock_stack = AsyncMock()
        base._stack = mock_stack
        
        result = await base.open()
        
        assert result is base
        assert base._stack is mock_stack

    @pytest.mark.asyncio
    async def test_open_method_registration_failure(self):
        """Test open method with agent registration failure."""
        base = MCPEnabledBase(project_endpoint="https://test-endpoint.com")
        
        mock_stack = AsyncMock()
        mock_creds = AsyncMock()
        mock_client = AsyncMock()
        
        with patch('backend.v4.magentic_agents.common.lifecycle.AsyncExitStack', return_value=mock_stack):
            with patch('backend.v4.magentic_agents.common.lifecycle.DefaultAzureCredential', return_value=mock_creds):
                with patch('backend.v4.magentic_agents.common.lifecycle.AgentsClient', return_value=mock_client):
                    with patch.object(base, '_after_open', new_callable=AsyncMock):
                        mock_agent_registry.register_agent.side_effect = Exception("Registration failed")
                        
                        # Should not raise exception
                        result = await base.open()
                        
                        assert result is base
                        mock_agent_registry.register_agent.assert_called_once_with(base)

    @pytest.mark.asyncio
    async def test_close_method_success(self):
        """Test successful close method execution."""
        base = MCPEnabledBase()
        
        # Set up mocks
        mock_stack = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.close = AsyncMock()
        
        base._stack = mock_stack
        base._agent = mock_agent
        
        await base.close()
        
        mock_agent.close.assert_called_once()
        mock_agent_registry.unregister_agent.assert_called_once_with(base)
        mock_stack.aclose.assert_called_once()
        
        assert base._stack is None
        assert base.mcp_tool is None
        assert base._agent is None

    @pytest.mark.asyncio
    async def test_close_method_no_stack(self):
        """Test close method when no stack exists."""
        base = MCPEnabledBase()
        base._stack = None
        
        await base.close()
        
        # Should not raise exception
        mock_agent_registry.unregister_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_method_with_exceptions(self):
        """Test close method with exceptions in cleanup."""
        base = MCPEnabledBase()
        
        mock_stack = AsyncMock()
        mock_agent = AsyncMock()
        mock_agent.close.side_effect = Exception("Close failed")
        
        base._stack = mock_stack
        base._agent = mock_agent
        
        mock_agent_registry.unregister_agent.side_effect = Exception("Unregister failed")
        
        # Should not raise exceptions
        await base.close()
        
        mock_stack.aclose.assert_called_once()
        assert base._stack is None

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self):
        """Test async context manager protocol."""
        base = MCPEnabledBase()
        
        with patch.object(base, 'open', new_callable=AsyncMock) as mock_open:
            with patch.object(base, 'close', new_callable=AsyncMock) as mock_close:
                mock_open.return_value = base
                
                async with base as result:
                    assert result is base
                    mock_open.assert_called_once()
                
                mock_close.assert_called_once()

    def test_getattr_delegation_success(self):
        """Test __getattr__ delegation to underlying agent."""
        base = MCPEnabledBase()
        mock_agent = Mock()
        mock_agent.test_method = Mock(return_value="test_result")
        base._agent = mock_agent
        
        result = base.test_method()
        
        assert result == "test_result"
        mock_agent.test_method.assert_called_once()

    def test_getattr_delegation_no_agent(self):
        """Test __getattr__ when no agent exists."""
        base = MCPEnabledBase()
        base._agent = None
        
        with pytest.raises(AttributeError) as exc_info:
            _ = base.nonexistent_method()
        
        assert "MCPEnabledBase has no attribute 'nonexistent_method'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_after_open_not_implemented(self):
        """Test that _after_open raises NotImplementedError."""
        base = MCPEnabledBase()
        
        with pytest.raises(NotImplementedError):
            await base._after_open()

    def test_get_chat_client_with_existing_client(self):
        """Test get_chat_client with provided chat_client."""
        base = MCPEnabledBase()
        mock_provided_client = Mock()
        
        result = base.get_chat_client(mock_provided_client)
        
        assert result is mock_provided_client

    def test_get_chat_client_from_agent(self):
        """Test get_chat_client from existing agent."""
        base = MCPEnabledBase()
        mock_agent = Mock()
        mock_chat_client = Mock()
        mock_chat_client.agent_id = "agent-123"
        mock_agent.chat_client = mock_chat_client
        base._agent = mock_agent
        
        result = base.get_chat_client(None)
        
        assert result is mock_chat_client

    def test_get_chat_client_create_new(self):
        """Test get_chat_client creates new client."""
        base = MCPEnabledBase(
            project_endpoint="https://test.com",
            model_deployment_name="gpt-4"
        )
        mock_creds = Mock()
        base.creds = mock_creds
        
        mock_new_client = Mock()
        
        with patch('backend.v4.magentic_agents.common.lifecycle.AzureAIAgentClient', return_value=mock_new_client) as mock_client_class:
            result = base.get_chat_client(None)
            
            assert result is mock_new_client
            mock_client_class.assert_called_once_with(
                project_endpoint="https://test.com",
                model_deployment_name="gpt-4",
                async_credential=mock_creds
            )

    def test_get_agent_id_with_existing_client(self):
        """Test get_agent_id with provided chat_client."""
        base = MCPEnabledBase()
        mock_chat_client = Mock()
        mock_chat_client.agent_id = "provided-agent-id"
        
        result = base.get_agent_id(mock_chat_client)
        
        assert result == "provided-agent-id"

    def test_get_agent_id_from_agent(self):
        """Test get_agent_id from existing agent."""
        base = MCPEnabledBase()
        mock_agent = Mock()
        mock_chat_client = Mock()
        mock_chat_client.agent_id = "agent-from-agent"
        mock_agent.chat_client = mock_chat_client
        base._agent = mock_agent
        
        result = base.get_agent_id(None)
        
        assert result == "agent-from-agent"

    def test_get_agent_id_generate_new(self):
        """Test get_agent_id generates new ID."""
        base = MCPEnabledBase()
        
        with patch('backend.v4.magentic_agents.common.lifecycle.generate_assistant_id', return_value="new-generated-id"):
            result = base.get_agent_id(None)
            
            assert result == "new-generated-id"

    @pytest.mark.asyncio
    async def test_get_database_team_agent_success(self):
        """Test successful get_database_team_agent."""
        base = MCPEnabledBase(
            team_config=self.mock_team_config,
            agent_name="TestAgent",
            project_endpoint="https://test.com",
            model_deployment_name="gpt-4"
        )
        base.memory_store = self.mock_memory_store
        base.creds = Mock()
        
        mock_client = AsyncMock()
        mock_agent = Mock()
        mock_agent.id = "database-agent-id"
        mock_client.get_agent.return_value = mock_agent
        base.client = mock_client
        
        mock_azure_client = Mock()
        
        with patch('backend.v4.magentic_agents.common.lifecycle.get_database_team_agent_id', return_value="database-agent-id"):
            with patch('backend.v4.magentic_agents.common.lifecycle.AzureAIAgentClient', return_value=mock_azure_client):
                result = await base.get_database_team_agent()
                
                assert result is mock_azure_client
                mock_client.get_agent.assert_called_once_with(agent_id="database-agent-id")

    @pytest.mark.asyncio
    async def test_get_database_team_agent_no_agent_id(self):
        """Test get_database_team_agent with no agent ID."""
        base = MCPEnabledBase()
        base.memory_store = self.mock_memory_store
        
        with patch('backend.v4.magentic_agents.common.lifecycle.get_database_team_agent_id', return_value=None):
            result = await base.get_database_team_agent()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_database_team_agent_exception(self):
        """Test get_database_team_agent with exception."""
        base = MCPEnabledBase()
        base.memory_store = self.mock_memory_store
        
        with patch('backend.v4.magentic_agents.common.lifecycle.get_database_team_agent_id', side_effect=Exception("Database error")):
            result = await base.get_database_team_agent()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_save_database_team_agent_success(self):
        """Test successful save_database_team_agent."""
        base = MCPEnabledBase(
            team_config=self.mock_team_config,
            agent_name="TestAgent",
            agent_description="Test Description",
            agent_instructions="Test Instructions"
        )
        base.memory_store = AsyncMock()
        
        mock_agent = Mock()
        mock_agent.id = "agent-123"
        mock_agent.chat_client = Mock()
        mock_agent.chat_client.agent_id = "agent-123"
        base._agent = mock_agent
        
        with patch('backend.v4.magentic_agents.common.lifecycle.CurrentTeamAgent') as mock_team_agent_class:
            mock_team_agent_instance = Mock()
            mock_team_agent_class.return_value = mock_team_agent_instance
            
            await base.save_database_team_agent()
            
            mock_team_agent_class.assert_called_once_with(
                team_id=self.mock_team_config.team_id,
                team_name=self.mock_team_config.name,
                agent_name="TestAgent",
                agent_foundry_id="agent-123",
                agent_description="Test Description",
                agent_instructions="Test Instructions"
            )
            base.memory_store.add_team_agent.assert_called_once_with(mock_team_agent_instance)

    @pytest.mark.asyncio
    async def test_save_database_team_agent_no_agent_id(self):
        """Test save_database_team_agent with no agent ID."""
        base = MCPEnabledBase()
        mock_agent = Mock()
        mock_agent.id = None
        base._agent = mock_agent
        
        await base.save_database_team_agent()
        
        # Should log error and return early

    @pytest.mark.asyncio
    async def test_save_database_team_agent_exception(self):
        """Test save_database_team_agent with exception."""
        base = MCPEnabledBase(team_config=self.mock_team_config)
        base.memory_store = AsyncMock()
        base.memory_store.add_team_agent.side_effect = Exception("Save error")
        
        mock_agent = Mock()
        mock_agent.id = "agent-123"
        base._agent = mock_agent
        
        # Should not raise exception
        await base.save_database_team_agent()

    @pytest.mark.asyncio
    async def test_prepare_mcp_tool_success(self):
        """Test successful _prepare_mcp_tool."""
        base = MCPEnabledBase(mcp=self.mock_mcp_config)
        mock_stack = AsyncMock()
        base._stack = mock_stack
        
        mock_mcp_tool = AsyncMock()
        
        with patch('backend.v4.magentic_agents.common.lifecycle.MCPStreamableHTTPTool', return_value=mock_mcp_tool) as mock_tool_class:
            await base._prepare_mcp_tool()
            
            mock_tool_class.assert_called_once_with(
                name=self.mock_mcp_config.name,
                description=self.mock_mcp_config.description,
                url=self.mock_mcp_config.url
            )
            mock_stack.enter_async_context.assert_called_once_with(mock_mcp_tool)
            assert base.mcp_tool is mock_mcp_tool

    @pytest.mark.asyncio
    async def test_prepare_mcp_tool_no_config(self):
        """Test _prepare_mcp_tool with no MCP config."""
        base = MCPEnabledBase(mcp=None)
        
        await base._prepare_mcp_tool()
        
        assert base.mcp_tool is None

    @pytest.mark.asyncio
    async def test_prepare_mcp_tool_exception(self):
        """Test _prepare_mcp_tool with exception."""
        base = MCPEnabledBase(mcp=self.mock_mcp_config)
        mock_stack = AsyncMock()
        base._stack = mock_stack
        
        with patch('backend.v4.magentic_agents.common.lifecycle.MCPStreamableHTTPTool', side_effect=Exception("MCP error")):
            await base._prepare_mcp_tool()
            
            assert base.mcp_tool is None


class TestAzureAgentBase:
    """Test cases for AzureAgentBase class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_mcp_config = Mock()
        self.mock_team_service = Mock()
        self.mock_team_config = Mock()
        self.mock_memory_store = Mock()
        
        # Reset mocks
        mock_agent_registry.reset_mock()

    def test_init_with_minimal_params(self):
        """Test AzureAgentBase initialization with minimal parameters."""
        base = AzureAgentBase()
        
        # Check inherited attributes
        assert base._stack is None
        assert base.mcp_cfg is None
        assert base._agent is None
        
        # Check AzureAgentBase specific attributes
        assert base._created_ephemeral is False

    def test_init_with_full_params(self):
        """Test AzureAgentBase initialization with all parameters."""
        base = AzureAgentBase(
            mcp=self.mock_mcp_config,
            model_deployment_name="gpt-4",
            project_endpoint="https://test-endpoint.com",
            team_service=self.mock_team_service,
            team_config=self.mock_team_config,
            memory_store=self.mock_memory_store,
            agent_name="TestAgent",
            agent_description="Test agent description",
            agent_instructions="Test instructions"
        )
        
        # Verify all parameters are set correctly via parent class
        assert base.mcp_cfg is self.mock_mcp_config
        assert base.model_deployment_name == "gpt-4"
        assert base.project_endpoint == "https://test-endpoint.com"
        assert base.team_service is self.mock_team_service
        assert base.team_config is self.mock_team_config
        assert base.memory_store is self.mock_memory_store
        assert base.agent_name == "TestAgent"
        assert base.agent_description == "Test agent description"
        assert base.agent_instructions == "Test instructions"
        assert base._created_ephemeral is False

    @pytest.mark.asyncio
    async def test_close_method_success(self):
        """Test successful close method execution."""
        base = AzureAgentBase()
        
        # Set up mocks
        mock_agent = AsyncMock()
        mock_agent.close = AsyncMock()
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_creds = AsyncMock()
        mock_creds.close = AsyncMock()
        
        base._agent = mock_agent
        base.client = mock_client
        base.creds = mock_creds
        base.project_endpoint = "https://test.com"
        
        # Mock parent close
        with patch('backend.v4.magentic_agents.common.lifecycle.MCPEnabledBase.close', new_callable=AsyncMock) as mock_parent_close:
            await base.close()
            
            mock_agent.close.assert_called_once()
            mock_agent_registry.unregister_agent.assert_called_once_with(base)
            mock_client.close.assert_called_once()
            mock_creds.close.assert_called_once()
            mock_parent_close.assert_called_once()
            
            assert base.client is None
            assert base.creds is None
            assert base.project_endpoint is None

    @pytest.mark.asyncio
    async def test_close_method_with_exceptions(self):
        """Test close method with exceptions in cleanup."""
        base = AzureAgentBase()
        
        # Set up mocks that raise exceptions
        mock_agent = AsyncMock()
        mock_agent.close.side_effect = Exception("Agent close failed")
        mock_client = AsyncMock()
        mock_client.close.side_effect = Exception("Client close failed")
        mock_creds = AsyncMock()
        mock_creds.close.side_effect = Exception("Creds close failed")
        
        base._agent = mock_agent
        base.client = mock_client
        base.creds = mock_creds
        
        mock_agent_registry.unregister_agent.side_effect = Exception("Unregister failed")
        
        # Mock parent close
        with patch('backend.v4.magentic_agents.common.lifecycle.MCPEnabledBase.close', new_callable=AsyncMock) as mock_parent_close:
            # Should not raise exceptions
            await base.close()
            
            mock_parent_close.assert_called_once()
            assert base.client is None
            assert base.creds is None

    @pytest.mark.asyncio
    async def test_close_method_no_resources(self):
        """Test close method when no resources to close."""
        base = AzureAgentBase()
        
        base._agent = None
        base.client = None
        base.creds = None
        
        with patch('backend.v4.magentic_agents.common.lifecycle.MCPEnabledBase.close', new_callable=AsyncMock) as mock_parent_close:
            await base.close()
            
            mock_parent_close.assert_called_once()
            mock_agent_registry.unregister_agent.assert_called_once_with(base)

    def test_inheritance_from_mcp_enabled_base(self):
        """Test that AzureAgentBase properly inherits from MCPEnabledBase."""
        base = AzureAgentBase()
        
        assert isinstance(base, MCPEnabledBase)
        # Should have access to parent methods
        assert hasattr(base, 'open')
        assert hasattr(base, '_prepare_mcp_tool')
        assert hasattr(base, 'get_chat_client')
        assert hasattr(base, 'get_agent_id')

    def test_azure_specific_attributes(self):
        """Test AzureAgentBase specific attributes."""
        base = AzureAgentBase()
        
        # Check Azure-specific attribute
        assert hasattr(base, '_created_ephemeral')
        assert base._created_ephemeral is False

    @pytest.mark.asyncio
    async def test_context_manager_inheritance(self):
        """Test that context manager functionality is inherited."""
        base = AzureAgentBase()
        
        with patch.object(base, 'open', new_callable=AsyncMock) as mock_open:
            with patch.object(base, 'close', new_callable=AsyncMock) as mock_close:
                mock_open.return_value = base
                
                async with base as result:
                    assert result is base
                    mock_open.assert_called_once()
                
                mock_close.assert_called_once()

    def test_getattr_delegation_inheritance(self):
        """Test that __getattr__ delegation is inherited."""
        base = AzureAgentBase()
        mock_agent = Mock()
        mock_agent.inherited_method = Mock(return_value="inherited_result")
        base._agent = mock_agent
        
        result = base.inherited_method()
        
        assert result == "inherited_result"
        mock_agent.inherited_method.assert_called_once()
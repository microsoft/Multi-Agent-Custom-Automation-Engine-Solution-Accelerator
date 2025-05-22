import sys
import os
import pytest
import logging
import inspect
import json
import asyncio
from unittest import mock
from typing import Any, Dict, List, Optional

# Ensure src/backend is on the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_kernel import Config
from kernel_agents.agent_factory import AgentFactory
from models.messages_kernel import AgentType
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel import Kernel

# Import agent types to test
from kernel_agents.hr_agent import HrAgent
from kernel_agents.human_agent import HumanAgent
from kernel_agents.marketing_agent import MarketingAgent
from kernel_agents.procurement_agent import ProcurementAgent
from kernel_agents.tech_support_agent import TechSupportAgent

# Configure logging for the tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define test data
TEST_SESSION_ID = "integration-test-session"
TEST_USER_ID = "integration-test-user"

# Check if required Azure environment variables are present
def azure_env_available():
    """Check if all required Azure environment variables are present."""
    required_vars = [
        "AZURE_AI_AGENT_PROJECT_CONNECTION_STRING",
        "AZURE_AI_SUBSCRIPTION_ID",
        "AZURE_AI_RESOURCE_GROUP",
        "AZURE_AI_PROJECT_NAME",
        "AZURE_OPENAI_DEPLOYMENT_NAME"
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logger.warning(f"Missing required environment variables for Azure tests: {missing}")
        return False
    return True

# Skip tests if Azure environment is not configured
skip_if_no_azure = pytest.mark.skipif(not azure_env_available(), 
                                     reason="Azure environment not configured")

def find_tools_json_file(agent_type_str):
    """Find the appropriate tools JSON file for an agent type."""
    tools_dir = os.path.join(os.path.dirname(__file__), '..', 'tools')
    tools_file = os.path.join(tools_dir, f"{agent_type_str}_tools.json")
    
    if os.path.exists(tools_file):
        return tools_file
    
    # Try alternatives if the direct match isn't found
    alt_file = os.path.join(tools_dir, f"{agent_type_str.replace('_', '')}_tools.json")
    if os.path.exists(alt_file):
        return alt_file
        
    # If nothing is found, log a warning but don't fail
    logger.warning(f"No tools JSON file found for agent type {agent_type_str}")
    return None

# Fixture for isolated event loop per test
@pytest.fixture
def event_loop():
    """Create an isolated event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    # Clean up
    if not loop.is_closed():
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

# Fixture for AI project client
@pytest.fixture
async def ai_project_client():
    """Create a fresh AI project client for each test."""
    old_client = Config._Config__ai_project_client
    Config._Config__ai_project_client = None  # Reset the cached client
    
    # Get a fresh client
    client = Config.GetAIProjectClient()
    yield client
    
    # Restore original client if needed
    Config._Config__ai_project_client = old_client

@skip_if_no_azure
@pytest.mark.asyncio
async def test_azure_project_client_connection():
    """
    Integration test to verify that we can successfully create a connection to Azure using the project client.
    This is the most basic test to ensure our Azure connectivity is working properly before testing agents.
    """
    # Get the Azure AI Project client
    project_client = Config.GetAIProjectClient()
    
    # Verify the project client has been created successfully
    assert project_client is not None, "Failed to create Azure AI Project client"
    
    # Check that the connection string environment variable is set
    conn_str_env = os.environ.get("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
    assert conn_str_env is not None, "AZURE_AI_AGENT_PROJECT_CONNECTION_STRING environment variable not set"
    
    # Log success
    logger.info("Successfully connected to Azure using the project client")

@skip_if_no_azure
@pytest.mark.parametrize(
    "agent_type,expected_agent_class", 
    [
        (AgentType.HR, HrAgent),
        (AgentType.HUMAN, HumanAgent),
        (AgentType.MARKETING, MarketingAgent),
        (AgentType.PROCUREMENT, ProcurementAgent),
        (AgentType.TECH_SUPPORT, TechSupportAgent),
    ]
)
@pytest.mark.asyncio
async def test_create_real_agent(agent_type, expected_agent_class, ai_project_client):
    """
    Parameterized integration test to verify that we can create real agents of different types.
    Tests that:
    1. The agent is created without errors using the real project_client
    2. The agent is an instance of the expected class
    3. The agent has the required AzureAIAgent property
    """
    # Create a real agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=agent_type,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    agent_type_name = agent_type.name.lower()
    logger.info(f"Testing agent of type: {agent_type_name}")
    
    # Check that the agent was created successfully
    assert agent is not None, f"Failed to create a {agent_type_name} agent"
    
    # Verify the agent type
    assert isinstance(agent, expected_agent_class), f"Agent is not an instance of {expected_agent_class.__name__}"
    
    # Verify that the agent is or contains an AzureAIAgent
    assert hasattr(agent, '_agent'), f"{agent_type_name} agent does not have an _agent attribute"
    assert isinstance(agent._agent, AzureAIAgent), f"The _agent attribute of {agent_type_name} agent is not an AzureAIAgent"
    
    # Verify that the agent has a client attribute that was created by the project_client
    assert hasattr(agent._agent, 'client'), f"{agent_type_name} agent does not have a client attribute"
    assert agent._agent.client is not None, f"{agent_type_name} agent client is None"
    
    # Check that the agent has the correct session_id
    assert agent._session_id == TEST_SESSION_ID, f"{agent_type_name} agent has incorrect session_id"
    
    # Check that the agent has the correct user_id
    assert agent._user_id == TEST_USER_ID, f"{agent_type_name} agent has incorrect user_id"
    
    # Log success
    logger.info(f"Successfully created a real {agent_type_name} agent using project_client")
    return agent

@skip_if_no_azure
@pytest.mark.parametrize(
    "agent_type", 
    [
        AgentType.HR,
        AgentType.HUMAN, 
        AgentType.MARKETING,
        AgentType.PROCUREMENT,
        AgentType.TECH_SUPPORT,
    ]
)
@pytest.mark.asyncio
async def test_agent_loads_tools_from_json(agent_type, ai_project_client):
    """
    Parameterized integration test to verify that each agent loads tools from its
    corresponding tools/*_tools.json file.
    """
    # Create a real agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=agent_type,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    agent_type_name = agent_type.name.lower()
    agent_type_str = AgentFactory._agent_type_strings.get(agent_type, agent_type_name)
    logger.info(f"Testing tool loading for agent type: {agent_type_name} (type string: {agent_type_str})")
    
    # Check that the agent was created successfully
    assert agent is not None, f"Failed to create a {agent_type_name} agent"
    
    # Check that tools were loaded
    assert hasattr(agent, '_tools'), f"{agent_type_name} agent does not have tools"
    assert len(agent._tools) > 0, f"{agent_type_name} agent has no tools loaded"
    
    # Find the tools JSON file for this agent type
    tools_file = find_tools_json_file(agent_type_str)
    
    # If a tools file exists, verify the tools were loaded from it
    if tools_file:
        with open(tools_file, 'r') as f:
            tools_config = json.load(f)
        
        # Get tool names from the config
        config_tool_names = [tool.get("name", "") for tool in tools_config.get("tools", [])]
        config_tool_names = [name.lower() for name in config_tool_names if name]
        
        # Get tool names from the agent
        agent_tool_names = [t.name.lower() if hasattr(t, 'name') and t.name else "" for t in agent._tools]
        agent_tool_names = [name for name in agent_tool_names if name]
        
        # Log the tool names for debugging
        logger.info(f"Tools in JSON config for {agent_type_name}: {config_tool_names}")
        logger.info(f"Tools loaded in {agent_type_name} agent: {agent_tool_names}")
        
        # Check that at least one tool from the config was loaded
        if config_tool_names:
            # Find intersection between config tools and agent tools
            common_tools = [name for name in agent_tool_names if any(config_name in name or name in config_name 
                                                                    for config_name in config_tool_names)]
            
            assert common_tools, f"None of the tools from {tools_file} were loaded in the {agent_type_name} agent"
            logger.info(f"Found common tools: {common_tools}")
    
    # Log success
    logger.info(f"Successfully verified {agent_type_name} agent loaded {len(agent._tools)} tools")
    return agent

@skip_if_no_azure
@pytest.mark.parametrize(
    "agent_type", 
    [
        AgentType.HR,
        AgentType.HUMAN,
        AgentType.MARKETING,
        AgentType.PROCUREMENT,
        AgentType.TECH_SUPPORT,
    ]
)
@pytest.mark.asyncio
async def test_agent_has_system_message(agent_type, ai_project_client):
    """
    Parameterized integration test to verify that each agent is created with a domain-specific system message.
    """
    # Create a real agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=agent_type,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    agent_type_name = agent_type.name.lower()
    logger.info(f"Testing system message for agent type: {agent_type_name}")
    
    # Check that the agent was created successfully
    assert agent is not None, f"Failed to create a {agent_type_name} agent"
    
    # Get the system message from the agent
    system_message = None
    if hasattr(agent._agent, 'definition') and agent._agent.definition is not None:
        system_message = agent._agent.definition.get('instructions', '')
    
    # Verify that a system message is present
    assert system_message, f"No system message found for {agent_type_name} agent"
    
    # Check that the system message is domain-specific
    domain_terms = {
        AgentType.HR: ["hr", "human resource", "onboarding", "employee"],
        AgentType.HUMAN: ["human", "user", "feedback", "conversation"],
        AgentType.MARKETING: ["marketing", "campaign", "market", "advertising"],
        AgentType.PROCUREMENT: ["procurement", "purchasing", "vendor", "supplier"],
        AgentType.TECH_SUPPORT: ["tech", "support", "technical", "IT"]
    }
    
    # Check that at least one domain-specific term is in the system message
    terms = domain_terms.get(agent_type, [])
    assert any(term.lower() in system_message.lower() for term in terms), \
        f"System message for {agent_type_name} agent does not contain any domain-specific terms"
        
    # Log success
    logger.info(f"Successfully verified system message for {agent_type_name} agent")
    return True

@skip_if_no_azure
@pytest.mark.asyncio
async def test_human_agent_can_execute_method(ai_project_client):
    """
    Test that the Human agent can execute the handle_action_request method.
    """
    # Create a real Human agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    logger.info("Testing handle_action_request method on Human agent")
    
    # Check that the agent was created successfully
    assert agent is not None, "Failed to create a Human agent"
    
    # Create a simple action request JSON for the Human agent
    action_request = {
        "session_id": TEST_SESSION_ID,
        "step_id": "test-step-id",
        "plan_id": "test-plan-id",
        "action": "Test action",
        "parameters": {}
    }
    
    # Convert to JSON string
    action_request_json = json.dumps(action_request)
    
    # Execute the handle_action_request method
    assert hasattr(agent, 'handle_action_request'), "Human agent does not have handle_action_request method"
    
    # Call the method
    result = await agent.handle_action_request(action_request_json)
    
    # Check that we got a result
    assert result is not None, "handle_action_request returned None"
    assert isinstance(result, str), "handle_action_request did not return a string"
    
    # Log success
    logger.info("Successfully executed handle_action_request on Human agent")
    return result
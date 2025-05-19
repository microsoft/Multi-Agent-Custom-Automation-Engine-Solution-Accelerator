import sys
import os
import pytest
import logging
import json

# Ensure src/backend is on the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_kernel import Config
from kernel_agents.agent_factory import AgentFactory
from models.messages_kernel import AgentType
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from kernel_agents.human_agent import HumanAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from models.messages_kernel import HumanFeedback

# Configure logging for the tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define test data
TEST_SESSION_ID = "human-integration-test-session"
TEST_USER_ID = "human-integration-test-user"

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
@pytest.mark.asyncio
async def test_create_human_agent():
    """Test that we can create a Human agent."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create a real agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Check that the agent was created successfully
    assert agent is not None, "Failed to create a Human agent"
    
    # Verify the agent type
    assert isinstance(agent, HumanAgent), "Agent is not an instance of HumanAgent"
    
    # Verify that the agent is or contains an AzureAIAgent
    assert hasattr(agent, '_agent'), "Human agent does not have an _agent attribute"
    assert isinstance(agent._agent, AzureAIAgent), "The _agent attribute of Human agent is not an AzureAIAgent"
    
    # Verify that the agent has a client attribute that was created by the project_client
    assert hasattr(agent._agent, 'client'), "Human agent does not have a client attribute"
    assert agent._agent.client is not None, "Human agent client is None"
    
    # Check that the agent has the correct session_id
    assert agent._session_id == TEST_SESSION_ID, "Human agent has incorrect session_id"
    
    # Check that the agent has the correct user_id
    assert agent._user_id == TEST_USER_ID, "Human agent has incorrect user_id"
    
    # Log success
    logger.info("Successfully created a real Human agent using project_client")
    return agent


@skip_if_no_azure
@pytest.mark.asyncio 
async def test_human_agent_loads_tools():
    """Test that the Human agent loads tools from its JSON file."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create a Human agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Check that tools were loaded
    assert hasattr(agent, '_tools'), "Human agent does not have tools"
    assert len(agent._tools) > 0, "Human agent has no tools loaded"
    
    # Find the tools JSON file for Human
    agent_type_str = AgentFactory._agent_type_strings.get(AgentType.HUMAN, "human_agent")
    tools_file = find_tools_json_file(agent_type_str)
    
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
        logger.info(f"Tools in JSON config for Human: {config_tool_names}")
        logger.info(f"Tools loaded in Human agent: {agent_tool_names}")
        
        # Check that at least one tool from the config was loaded
        if config_tool_names:
            # Find intersection between config tools and agent tools
            common_tools = [name for name in agent_tool_names if any(config_name in name or name in config_name 
                                                                    for config_name in config_tool_names)]
            
            assert common_tools, f"None of the tools from {tools_file} were loaded in the Human agent"
            logger.info(f"Found common tools: {common_tools}")
    
    # Log success
    logger.info(f"Successfully verified Human agent loaded {len(agent._tools)} tools")


@skip_if_no_azure
@pytest.mark.asyncio
async def test_human_agent_has_system_message():
    """Test that the Human agent is created with a domain-specific system message."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create a Human agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Get the system message from the agent
    system_message = None
    if hasattr(agent._agent, 'definition') and agent._agent.definition is not None:
        system_message = agent._agent.definition.get('instructions', '')
    
    # Verify that a system message is present
    assert system_message, "No system message found for Human agent"
    
    # Check that the system message is domain-specific
    human_terms = ["human", "user", "feedback", "conversation"]
    
    # Check that at least one domain-specific term is in the system message
    assert any(term.lower() in system_message.lower() for term in human_terms), \
        "System message for Human agent does not contain any Human-specific terms"
        
    # Log success
    logger.info("Successfully verified system message for Human agent")


@skip_if_no_azure
@pytest.mark.asyncio
async def test_human_agent_has_methods():
    """Test that the Human agent has the expected methods."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create a real Human agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HUMAN,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    logger.info("Testing for expected methods on Human agent")
    
    # Check that the agent was created successfully
    assert agent is not None, "Failed to create a Human agent"
    
    # Check that the agent has the expected methods
    assert hasattr(agent, 'handle_human_feedback'), "Human agent does not have handle_human_feedback method"
    assert hasattr(agent, 'provide_clarification'), "Human agent does not have provide_clarification method"
    
    # Log success
    logger.info("Successfully verified Human agent has expected methods")
    
    # Return the agent for potential further testing
    return agent
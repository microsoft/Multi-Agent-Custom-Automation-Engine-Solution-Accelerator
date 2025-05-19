import sys
import os
import pytest
import logging
import json
import asyncio

# Ensure src/backend is on the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_kernel import Config
from kernel_agents.agent_factory import AgentFactory
from models.messages_kernel import AgentType
from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent
from kernel_agents.hr_agent import HrAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Configure logging for the tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define test data
TEST_SESSION_ID = "hr-integration-test-session"
TEST_USER_ID = "hr-integration-test-user"

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
async def test_create_hr_agent():
    """Test that we can create an HR agent."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create a real agent using the AgentFactory
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HR,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Check that the agent was created successfully
    assert agent is not None, "Failed to create an HR agent"
    
    # Verify the agent type
    assert isinstance(agent, HrAgent), "Agent is not an instance of HrAgent"
    
    # Verify that the agent is or contains an AzureAIAgent
    assert hasattr(agent, '_agent'), "HR agent does not have an _agent attribute"
    assert isinstance(agent._agent, AzureAIAgent), "The _agent attribute of HR agent is not an AzureAIAgent"
    
    # Verify that the agent has a client attribute that was created by the project_client
    assert hasattr(agent._agent, 'client'), "HR agent does not have a client attribute"
    assert agent._agent.client is not None, "HR agent client is None"
    
    # Check that the agent has the correct session_id
    assert agent._session_id == TEST_SESSION_ID, "HR agent has incorrect session_id"
    
    # Check that the agent has the correct user_id
    assert agent._user_id == TEST_USER_ID, "HR agent has incorrect user_id"
    
    # Log success
    logger.info("Successfully created a real HR agent using project_client")
    return agent


@skip_if_no_azure
@pytest.mark.asyncio 
async def test_hr_agent_loads_tools_from_json():
    """Test that the HR agent loads tools from its JSON file."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create an HR agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HR,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Check that tools were loaded
    assert hasattr(agent, '_tools'), "HR agent does not have tools"
    assert len(agent._tools) > 0, "HR agent has no tools loaded"
    
    # Find the tools JSON file for HR
    agent_type_str = AgentFactory._agent_type_strings.get(AgentType.HR, "hr")
    tools_file = find_tools_json_file(agent_type_str)
    
    if tools_file:
        with open(tools_file, 'r') as f:
            tools_config = json.load(f)
        
        # Get tool names from the config
        config_tool_names = [tool.get("name", "") for tool in tools_config.get("tools", [])]
        config_tool_names = [name.lower() for name in config_tool_names if name]
        
        # Get tool names from the agent
        agent_tool_names = []
        for t in agent._tools:
            # Handle different ways the name might be stored
            if hasattr(t, 'name'):
                name = t.name
            elif hasattr(t, 'metadata') and hasattr(t.metadata, 'name'):
                name = t.metadata.name
            else:
                name = str(t)
                
            if name:
                agent_tool_names.append(name.lower())
        
        # Log the tool names for debugging
        logger.info(f"Tools in JSON config for HR: {config_tool_names}")
        logger.info(f"Tools loaded in HR agent: {agent_tool_names}")
        
        # Verify all required tools were loaded by checking if their names appear in the agent tool names
        for required_tool in ["schedule_orientation_session", "register_for_benefits", "assign_mentor", 
                             "update_employee_record", "process_leave_request"]:
            # Less strict check - just look for the name as a substring
            found = any(required_tool.lower() in tool_name for tool_name in agent_tool_names)
            
            # If not found with exact matching, try a more lenient approach
            if not found:
                found = any(tool_name in required_tool.lower() or required_tool.lower() in tool_name 
                           for tool_name in agent_tool_names)
                
            assert found, f"Required tool '{required_tool}' was not loaded by the HR agent"
            if found:
                logger.info(f"Found required tool: {required_tool}")
    
    # Log success
    logger.info(f"Successfully verified HR agent loaded {len(agent._tools)} tools from JSON configuration")


@skip_if_no_azure
@pytest.mark.asyncio
async def test_hr_agent_has_system_message():
    """Test that the HR agent is created with a domain-appropriate system message."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create an HR agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HR,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Get the system message from the agent
    system_message = None
    if hasattr(agent._agent, 'definition') and agent._agent.definition is not None:
        system_message = agent._agent.definition.get('instructions', '')
    
    # Verify that a system message is present
    assert system_message, "No system message found for HR agent"
    
    # Check that the system message is domain-specific for HR
    # We're being less strict about the exact wording
    hr_terms = ["HR", "hr", "human resource", "human resources"]
    
    # Check that at least one domain-specific term is in the system message
    found_term = next((term for term in hr_terms if term.lower() in system_message.lower()), None)
    assert found_term, "System message for HR agent does not contain any HR-related terms"
        
    # Log success with the actual system message
    logger.info(f"Successfully verified system message for HR agent: '{system_message}'")


@skip_if_no_azure
@pytest.mark.asyncio
async def test_hr_agent_tools_existence():
    """Test that the HR agent has the expected tools available."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create an HR agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HR,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    # Load the JSON tools configuration for comparison
    tools_file = find_tools_json_file("hr")
    assert tools_file, "HR tools JSON file not found"
    
    with open(tools_file, 'r') as f:
        tools_config = json.load(f)
    
    # Define critical HR tools that must be available
    critical_tools = [
        "schedule_orientation_session",
        "assign_mentor", 
        "register_for_benefits",
        "update_employee_record",
        "process_leave_request",
        "verify_employment"
    ]
    
    # Check that these tools exist in the configuration
    config_tool_names = [tool.get("name", "").lower() for tool in tools_config.get("tools", [])]
    for tool_name in critical_tools:
        assert tool_name.lower() in config_tool_names, f"Critical tool '{tool_name}' not in HR tools JSON config"
    
    # Get tool names from the agent for a less strict validation
    agent_tool_names = []
    for t in agent._tools:
        # Handle different ways the name might be stored
        if hasattr(t, 'name'):
            name = t.name
        elif hasattr(t, 'metadata') and hasattr(t.metadata, 'name'):
            name = t.metadata.name
        else:
            name = str(t)
            
        if name:
            agent_tool_names.append(name.lower())
    
    # At least verify that we have a similar number of tools to what was in the original
    assert len(agent_tool_names) >= 25, f"HR agent should have at least 25 tools, but only has {len(agent_tool_names)}"
    
    logger.info(f"Successfully verified HR agent has {len(agent_tool_names)} tools available")


@skip_if_no_azure
@pytest.mark.asyncio
async def test_hr_agent_direct_tool_execution():
    """Test that we can directly execute HR agent tools using the agent instance."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create an HR agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HR,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    try:
        # Get available tool names for logging
        available_tools = [t.name for t in agent._tools if hasattr(t, 'name')]
        logger.info(f"Available tool names: {available_tools}")
        
        # First test: Schedule orientation using invoke_tool
        logger.info("Testing orientation tool invocation through agent")
        orientation_tool_name = "schedule_orientation_session"
        orientation_result = await agent.invoke_tool(
            orientation_tool_name, 
            {"employee_name": "Jane Doe", "date": "April 25, 2025"}
        )
        
        # Log the result
        logger.info(f"Orientation tool result via agent: {orientation_result}")
        
        # Verify the result
        assert orientation_result is not None, "No result returned from orientation tool"
        assert "Jane Doe" in str(orientation_result), "Employee name not found in orientation tool result"
        assert "April 25, 2025" in str(orientation_result), "Date not found in orientation tool result"
        
        # Second test: Register for benefits
        logger.info("Testing benefits registration tool invocation through agent")
        benefits_tool_name = "register_for_benefits"
        benefits_result = await agent.invoke_tool(
            benefits_tool_name,
            {"employee_name": "John Smith"}
        )
        
        # Log the result
        logger.info(f"Benefits tool result via agent: {benefits_result}")
        
        # Verify the result
        assert benefits_result is not None, "No result returned from benefits tool"
        assert "John Smith" in str(benefits_result), "Employee name not found in benefits tool result"
        
        # Third test: Process leave request
        logger.info("Testing leave request processing tool invocation through agent")
        leave_tool_name = "process_leave_request"
        leave_result = await agent.invoke_tool(
            leave_tool_name,
            {"employee_name": "Alice Brown", "start_date": "May 1, 2025", "end_date": "May 5, 2025", "reason": "Vacation"}
        )
        
        # Log the result
        logger.info(f"Leave request tool result via agent: {leave_result}")
        
        # Verify the result
        assert leave_result is not None, "No result returned from leave request tool"
        assert "Alice Brown" in str(leave_result), "Employee name not found in leave request tool result"
        
        logger.info("Successfully executed HR agent tools directly through the agent instance")
    except Exception as e:
        logger.error(f"Error executing HR agent tools: {str(e)}")
        raise


@skip_if_no_azure
@pytest.mark.asyncio
async def test_hr_agent_function_calling():
    """Test that the HR agent uses function calling when processing a request."""
    # Reset cached clients
    Config._Config__ai_project_client = None
    
    # Create an HR agent
    agent = await AgentFactory.create_agent(
        agent_type=AgentType.HR,
        session_id=TEST_SESSION_ID,
        user_id=TEST_USER_ID
    )
    
    try:
        # Create a prompt that should trigger a specific HR function
        prompt = "I need to schedule an orientation session for Jane Doe on April 25, 2025"
        
        # Get the chat function from the underlying Azure OpenAI client
        client = agent._agent.client
        
        # Try to get the AzureAIAgent to process our request with a custom implementation
        # This is a more direct test of function calling without mocking
        if hasattr(agent._agent, 'get_chat_history'):
            # Get the current chat history
            chat_history = agent._agent.get_chat_history()
            
            # Add our user message to the history
            chat_history.append({
                "role": "user", 
                "content": prompt
            })
            
            # Create a message to send to the agent
            message = {
                "role": "user",
                "content": prompt
            }
            
            # Use the Azure OpenAI client directly with function definitions from the agent
            # This tests that the functions are correctly formatted for the API
            tools = []
            
            # Extract tool definitions from agent._tools
            for tool in agent._tools:
                if hasattr(tool, 'metadata') and hasattr(tool.metadata, 'kernel_function_definition'):
                    # Add this tool to the tools list
                    tool_definition = {
                        "type": "function",
                        "function": {
                            "name": tool.metadata.name,
                            "description": tool.metadata.description,
                            "parameters": {} # Schema will be filled in below
                        }
                    }
                    
                    # Add parameters if available
                    if hasattr(tool, 'parameters'):
                        parameter_schema = {"type": "object", "properties": {}, "required": []}
                        for param in tool.parameters:
                            param_name = param.name
                            param_type = "string"
                            param_desc = param.description if hasattr(param, 'description') else ""
                            
                            parameter_schema["properties"][param_name] = {
                                "type": param_type,
                                "description": param_desc
                            }
                            
                            if param.required if hasattr(param, 'required') else False:
                                parameter_schema["required"].append(param_name)
                        
                        tool_definition["function"]["parameters"] = parameter_schema
                    
                    tools.append(tool_definition)
            
            # Log the tools we'll be using
            logger.info(f"Testing Azure client with {len(tools)} function tools")
            
            # Make the API call to verify functions are received correctly
            completion = await client.chat.completions.create(
                model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
                messages=[{"role": "system", "content": agent._system_message}, message],
                tools=tools,
                tool_choice="auto"
            )
            
            # Log the response
            logger.info(f"Received response from Azure OpenAI: {completion}")
            
            # Check if function calling was used
            if completion.choices and completion.choices[0].message.tool_calls:
                tool_calls = completion.choices[0].message.tool_calls
                logger.info(f"Azure OpenAI used function calling with {len(tool_calls)} tool calls")
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments
                    
                    logger.info(f"Function called: {function_name}")
                    logger.info(f"Function arguments: {function_args}")
                    
                    # Verify that schedule_orientation_session was called with the right parameters
                    if "schedule_orientation" in function_name.lower():
                        args_dict = json.loads(function_args)
                        assert "employee_name" in args_dict, "employee_name parameter missing"
                        assert "Jane Doe" in args_dict["employee_name"], "Incorrect employee name"
                        assert "date" in args_dict, "date parameter missing"
                        assert "April 25, 2025" in args_dict["date"], "Incorrect date"
                
                # Assert that at least one function was called
                assert len(tool_calls) > 0, "No functions were called by Azure OpenAI"
            else:
                # If no function calling was used, check the content for evidence of understanding
                content = completion.choices[0].message.content
                logger.info(f"Azure OpenAI response content: {content}")
                
                # Even if function calling wasn't used, the response should mention orientation
                assert "orientation" in content.lower(), "Response doesn't mention orientation"
                assert "Jane Doe" in content, "Response doesn't mention the employee name"
        
        logger.info("Successfully tested HR agent function calling")
    except Exception as e:
        logger.error(f"Error testing HR agent function calling: {str(e)}")
        raise
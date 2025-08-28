"""Integration tests for the agent system.

This test file verifies that the agent system correctly loads environment 
variables and can use functions from the JSON tool files.
"""
import os, sys, unittest, asyncio, uuid
from dotenv import load_dotenv

# Make src/backend importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- begin: test-only stub to satisfy config_kernel import ---
import types
sys.modules.pop("app_config", None)
app_config_stub = types.ModuleType("app_config")
app_config_stub.config = types.SimpleNamespace(
    AZURE_TENANT_ID="test-tenant",
    AZURE_CLIENT_ID="test-client",
    AZURE_CLIENT_SECRET="test-secret",
    COSMOSDB_ENDPOINT="https://mock-cosmos.documents.azure.com",
    COSMOSDB_DATABASE="mock-db",
    COSMOSDB_CONTAINER="mock-container",
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o",
    AZURE_OPENAI_API_VERSION="2024-11-20",
    AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
    AZURE_OPENAI_SCOPES=["https://cognitiveservices.azure.com/.default"],
    AZURE_AI_SUBSCRIPTION_ID="sub-id",
    AZURE_AI_RESOURCE_GROUP="rg",
    AZURE_AI_PROJECT_NAME="proj",
    AZURE_AI_AGENT_ENDPOINT="https://agents.example.com/",
    FRONTEND_SITE_NAME="http://127.0.0.1:3000",
    get_user_local_browser_language=lambda: os.environ.get("USER_LOCAL_BROWSER_LANGUAGE","en-US"),
)
sys.modules["app_config"] = app_config_stub
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-11-20")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
# --- end: test-only stub ---

# --------- CRUCIAL: evict any prior stub of models.messages_kernel BEFORE imports ---------
import importlib
sys.modules.pop("models.messages_kernel", None)
sys.modules.pop("models", None)
importlib.invalidate_caches()
from models.messages_kernel import AgentType  # load the real module now
# -----------------------------------------------------------------------------------------

from config_kernel import Config
from kernel_agents.agent_factory import AgentFactory
from utils_kernel import get_agents
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Load environment variables from .env file
load_dotenv()


class AgentIntegrationTest(unittest.TestCase):
    """Integration tests for the agent system."""

    def __init__(self, methodName='runTest'):
        """Initialize the test case with required attributes."""
        super().__init__(methodName)
        # Initialize these here to avoid the AttributeError
        self.session_id = str(uuid.uuid4())
        self.user_id = "test-user"
        self.required_env_vars = [
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "AZURE_OPENAI_API_VERSION", 
            "AZURE_OPENAI_ENDPOINT"
        ]

    def setUp(self):
        """Set up the test environment."""
        # Ensure we have the required environment variables
        for var in self.required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set")
                
        # Print test configuration
        print(f"\nRunning tests with:")
        print(f"  - Session ID: {self.session_id}")
        print(f"  - OpenAI Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
        print(f"  - OpenAI Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")

    def tearDown(self):
        """Clean up after tests."""
        # Clear the agent cache to ensure each test starts fresh
        AgentFactory.clear_cache()

    def test_environment_variables(self):
        """Test that environment variables are loaded correctly."""
        self.assertIsNotNone(Config.AZURE_OPENAI_DEPLOYMENT_NAME)
        self.assertIsNotNone(Config.AZURE_OPENAI_API_VERSION)
        self.assertIsNotNone(Config.AZURE_OPENAI_ENDPOINT)
        
    async def _test_create_kernel(self):
        """Test creating a semantic kernel."""
        kernel = Config.CreateKernel()
        self.assertIsNotNone(kernel)
        return kernel
        
    async def _test_create_agent_factory(self):
        """Test creating an agent using the agent factory."""
        # Create a generic agent
        generic_agent = await AgentFactory.create_agent(
            agent_type=AgentType.GENERIC,
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        self.assertIsNotNone(generic_agent)
        self.assertEqual(generic_agent._agent_name, "generic")
        
        # Test that the agent has tools loaded from the generic_tools.json file
        self.assertTrue(hasattr(generic_agent, "_tools"))
        
        # Return the agent for further testing
        return generic_agent
        
    async def _test_create_all_agents(self):
        """Test creating all agents."""
        agents_raw = await AgentFactory.create_all_agents(
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Check that all expected agent types are created
        expected_types = [
            AgentType.HR, AgentType.MARKETING, AgentType.PRODUCT,
            AgentType.PROCUREMENT, AgentType.TECH_SUPPORT,
            AgentType.GENERIC, AgentType.HUMAN, AgentType.PLANNER,
            AgentType.GROUP_CHAT_MANAGER
        ]
        
        for agent_type in expected_types:
            self.assertIn(agent_type, agents_raw)
            self.assertIsNotNone(agents_raw[agent_type])
            
        # Return the agents for further testing
        return agents_raw
        
    async def _test_get_agents(self):
        """Test the get_agents utility function."""
        agents = await get_agents(self.session_id, self.user_id)
        
        # Check that all expected agents are present
        expected_agent_names = [
            "HrAgent", "ProductAgent", "MarketingAgent",
            "ProcurementAgent", "TechSupportAgent", "GenericAgent",
            "HumanAgent", "PlannerAgent", "GroupChatManager"
        ]
        
        for agent_name in expected_agent_names:
            self.assertIn(agent_name, agents)
            self.assertIsNotNone(agents[agent_name])
            
        # Return the agents for further testing
        return agents

    async def _test_create_azure_ai_agent(self):
        """Test creating an AzureAIAgent directly."""
        agent = await get_azure_ai_agent(
            session_id=self.session_id,
            agent_name="test-agent",
            system_prompt="You are a test agent."
        )
        
        self.assertIsNotNone(agent)
        return agent
        
    async def _test_agent_tool_invocation(self):
        """Test that an agent can invoke tools from JSON configuration."""
        # Get a generic agent that should have the dummy_function loaded
        agents = await get_agents(self.session_id, self.user_id)
        generic_agent = agents["GenericAgent"]
        
        # Check that the agent has tools
        self.assertTrue(hasattr(generic_agent, "_tools"))
        
        # Try to invoke a dummy function if it exists
        try:
            # Use the agent to invoke the dummy function
            result = await generic_agent._agent.invoke_async("This is a test query that should use dummy_function")
            
            # If we got here, the function invocation worked
            self.assertIsNotNone(result)
            print(f"Tool invocation result: {result}")
        except Exception as e:
            self.fail(f"Tool invocation failed: {e}")
            
        return result
        
    async def run_all_tests(self):
        """Run all tests in sequence."""
        # Call setUp explicitly to ensure environment is properly initialized
        self.setUp()
        
        try:
            print("Testing environment variables...")
            self.test_environment_variables()
            
            print("Testing kernel creation...")
            kernel = await self._test_create_kernel()
            
            print("Testing agent factory...")
            generic_agent = await self._test_create_agent_factory()
            
            print("Testing creating all agents...")
            all_agents_raw = await self._test_create_all_agents()
            
            print("Testing get_agents utility...")
            agents = await self._test_get_agents()
            
            print("Testing Azure AI agent creation...")
            azure_agent = await self._test_create_azure_ai_agent()
            
            print("Testing agent tool invocation...")
            tool_result = await self._test_agent_tool_invocation()
            
            print("\nAll tests completed successfully!")
            
        except Exception as e:
            print(f"Tests failed: {e}")
            raise
        finally:
            # Call tearDown explicitly to ensure proper cleanup
            self.tearDown()
        
def run_tests():
    """Run the tests."""
    test = AgentIntegrationTest()
    
    # Create and run the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(test.run_all_tests())
    finally:
        loop.close()
    
if __name__ == '__main__':
    run_tests()
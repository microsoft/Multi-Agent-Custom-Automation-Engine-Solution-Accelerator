"""Integration tests for the GroupChatManager.

This test file verifies that the GroupChatManager correctly manages agent interactions,
coordinates plan execution, and properly integrates with Cosmos DB memory context.
These are real integration tests using real Cosmos DB connections and Azure OpenAI,
then cleaning up the test data afterward.
"""
import os
import sys
import unittest
import asyncio
import uuid
import json
from typing import Dict, List, Optional, Any, Set
from dotenv import load_dotenv
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- Force a test stub for app_config BEFORE importing Config ----
import types
import os, sys

# Evict any previously loaded app_config to avoid stale stubs
sys.modules.pop("app_config", None)

app_config_stub = types.ModuleType("app_config")
app_config_stub.config = types.SimpleNamespace(
    # Cosmos settings (non-emulator so setUp() passes)
    COSMOSDB_ENDPOINT="https://mock-cosmos.documents.azure.com",
    COSMOSDB_DATABASE="mock-database",
    COSMOSDB_CONTAINER="mock-container",

    # Azure OpenAI settings (dummies so imports don't crash)
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o",
    AZURE_OPENAI_API_VERSION="2024-11-20",
    AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
    AZURE_OPENAI_SCOPES=["https://cognitiveservices.azure.com/.default"],

    # Azure AI Project (dummies)
    AZURE_AI_SUBSCRIPTION_ID="00000000-0000-0000-0000-000000000000",
    AZURE_AI_RESOURCE_GROUP="rg-ci",
    AZURE_AI_PROJECT_NAME="proj-ci",
    AZURE_AI_AGENT_ENDPOINT="https://agents.example.azure.com/",

    # Misc used by some tools
    FRONTEND_SITE_NAME="http://127.0.0.1:3000",

    # Some modules expect this method on config
    get_user_local_browser_language=lambda: os.environ.get("USER_LOCAL_BROWSER_LANGUAGE", "en-US"),
)
sys.modules["app_config"] = app_config_stub
# ------------------------------------------------------------------

from config_kernel import Config

# ---- Ensure Config has a non-emulator Cosmos endpoint for these tests ----
Config.COSMOSDB_ENDPOINT  = app_config_stub.config.COSMOSDB_ENDPOINT
Config.COSMOSDB_DATABASE  = app_config_stub.config.COSMOSDB_DATABASE
Config.COSMOSDB_CONTAINER = app_config_stub.config.COSMOSDB_CONTAINER

# Also set env vars in case any code checks os.environ directly
os.environ.setdefault("COSMOSDB_ENDPOINT",  app_config_stub.config.COSMOSDB_ENDPOINT)
os.environ.setdefault("COSMOSDB_DATABASE",  app_config_stub.config.COSMOSDB_DATABASE)
os.environ.setdefault("COSMOSDB_CONTAINER", app_config_stub.config.COSMOSDB_CONTAINER)
# --------------------------------------------------------------------------

from kernel_agents.group_chat_manager import GroupChatManager
from kernel_agents.planner_agent import PlannerAgent
from kernel_agents.human_agent import HumanAgent
from kernel_agents.generic_agent import GenericAgent
from context.cosmos_memory_kernel import CosmosMemoryContext
from models.messages_kernel import (
    InputTask, 
    Plan, 
    Step, 
    AgentMessage,
    PlanStatus,
    StepStatus,
    HumanFeedbackStatus,
    ActionRequest,
    ActionResponse
)
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Load environment variables from .env file
load_dotenv()

class TestCleanupCosmosContext(CosmosMemoryContext):
    """Extended CosmosMemoryContext that tracks created items for test cleanup."""

    def __init__(self, cosmos_endpoint=None, cosmos_key=None, cosmos_database=None, 
                cosmos_container=None, session_id=None, user_id=None):
        """Initialize the cleanup-enabled context."""
        super().__init__(
            cosmos_endpoint=cosmos_endpoint,
            cosmos_key=cosmos_key,
            cosmos_database=cosmos_database,
            cosmos_container=cosmos_container,
            session_id=session_id,
            user_id=user_id
        )
        # Track items created during tests for cleanup
        self.created_items: Set[str] = set()
        self.created_plans: Set[str] = set()
        self.created_steps: Set[str] = set()
        
    async def add_item(self, item: Any) -> None:
        """Add an item and track it for cleanup."""
        await super().add_item(item)
        if hasattr(item, "id"):
            self.created_items.add(item.id)

    async def add_plan(self, plan: Plan) -> None:
        """Add a plan and track it for cleanup."""
        await super().add_plan(plan)
        self.created_plans.add(plan.id)

    async def add_step(self, step: Step) -> None:
        """Add a step and track it for cleanup."""
        await super().add_step(step)
        self.created_steps.add(step.id)
        
    async def cleanup_test_data(self) -> None:
        """Clean up all data created during testing."""
        print(f"\nCleaning up test data...")
        print(f"  - {len(self.created_items)} messages")
        print(f"  - {len(self.created_plans)} plans")
        print(f"  - {len(self.created_steps)} steps")
        
        # Delete steps
        for step_id in self.created_steps:
            try:
                await self._delete_item_by_id(step_id)
            except Exception as e:
                print(f"Error deleting step {step_id}: {e}")
                
        # Delete plans
        for plan_id in self.created_plans:
            try:
                await self._delete_item_by_id(plan_id)
            except Exception as e:
                print(f"Error deleting plan {plan_id}: {e}")
                
        # Delete messages
        for item_id in self.created_items:
            try:
                await self._delete_item_by_id(item_id)
            except Exception as e:
                print(f"Error deleting message {item_id}: {e}")
                
        print("Cleanup completed")
    
    async def _delete_item_by_id(self, item_id: str) -> None:
        """Delete a single item by ID from Cosmos DB."""
        if not self._container:
            await self._initialize_cosmos_client()
            
        try:
            # First try to read the item to get its partition key
            # This approach handles cases where we don't know the partition key for an item
            query = f"SELECT * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": item_id}]
            items = self._container.query_items(query=query, parameters=params, enable_cross_partition_query=True)
            
            found_items = list(items)
            if found_items:
                item = found_items[0]
                # If session_id exists in the item, use it as partition key
                partition_key = item.get("session_id")
                if partition_key:
                    await self._container.delete_item(item=item_id, partition_key=partition_key)
            else:
                # If we can't find it with a query, try deletion with cross-partition
                # This is less efficient but should work for cleanup
                print(f"Item {item_id} not found for cleanup")
        except Exception as e:
            print(f"Error during item deletion: {e}")


class GroupChatManagerIntegrationTest(unittest.TestCase):
    """Integration tests for the GroupChatManager."""

    def __init__(self, methodName='runTest'):
        """Initialize the test case with required attributes."""
        super().__init__(methodName)
        # Initialize these here to avoid the AttributeError
        self.session_id = str(uuid.uuid4())
        self.user_id = "test-user"
        self.required_env_vars = [
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OPENAI_ENDPOINT",
        ]
        self.group_chat_manager = None
        self.planner_agent = None
        self.memory_store = None
        self.test_task = "Create a marketing plan for a new product launch including social media strategy"

    def setUp(self):
        """Set up the test environment."""
        # Ensure we have the required environment variables for Azure OpenAI
        for var in self.required_env_vars:
            if not os.getenv(var):
                self.fail(f"Required environment variable {var} not set")
                
        # Ensure CosmosDB settings are available (using Config class instead of env vars directly)
        if not Config.COSMOSDB_ENDPOINT or Config.COSMOSDB_ENDPOINT == "https://localhost:8081":
            self.fail("COSMOSDB_ENDPOINT not set or is using default local value")
        
        # Print test configuration
        print(f"\nRunning tests with:")
        print(f"  - Session ID: {self.session_id}")
        print(f"  - OpenAI Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
        print(f"  - OpenAI Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
        print(f"  - Cosmos DB: {Config.COSMOSDB_DATABASE} at {Config.COSMOSDB_ENDPOINT}")

    async def tearDown_async(self):
        """Clean up after tests asynchronously."""
        if hasattr(self, 'memory_store') and self.memory_store:
            await self.memory_store.cleanup_test_data()

    def tearDown(self):
        """Clean up after tests."""
        # Run the async cleanup in a new event loop
        if asyncio.get_event_loop().is_running():
            # If we're in an already running event loop, we need to create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.tearDown_async())
            finally:
                loop.close()
        else:
            # Use the existing event loop
            asyncio.get_event_loop().run_until_complete(self.tearDown_async())

    async def initialize_group_chat_manager(self):
        """Initialize the group chat manager and agents for testing."""
        # Create Kernel
        kernel = Config.CreateKernel()
        
        # Create memory store with cleanup capabilities
        memory_store = TestCleanupCosmosContext(
            cosmos_endpoint=Config.COSMOSDB_ENDPOINT,
            cosmos_database=Config.COSMOSDB_DATABASE,
            cosmos_container=Config.COSMOSDB_CONTAINER,
            # The CosmosMemoryContext will use DefaultAzureCredential instead of a key
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Sample tool list for testing
        tool_list = [
            "create_social_media_post(platform: str, content: str, schedule_time: str)",
            "analyze_market_trends(industry: str, timeframe: str)",
            "setup_email_campaign(subject: str, content: str, target_audience: str)",
            "create_office365_account(name: str, email: str, access_level: str)",
            "generate_product_description(product_name: str, features: list, target_audience: str)",
            "schedule_meeting(participants: list, time: str, agenda: str)",
            "book_venue(location: str, date: str, attendees: int, purpose: str)"
        ]
        
        # Create real agent instances
        planner_agent = await self._create_planner_agent(kernel, memory_store, tool_list)
        human_agent = await self._create_human_agent(kernel, memory_store)
        generic_agent = await self._create_generic_agent(kernel, memory_store)
        
        # Create agent dictionary for the group chat manager
        available_agents = {
            "planner_agent": planner_agent,
            "human_agent": human_agent,
            "generic_agent": generic_agent
        }
        
        # Create the group chat manager
        group_chat_manager = GroupChatManager(
            kernel=kernel,
            session_id=self.session_id,
            user_id=self.user_id,
            memory_store=memory_store,
            available_agents=available_agents
        )
        
        self.planner_agent = planner_agent
        self.group_chat_manager = group_chat_manager
        self.memory_store = memory_store
        return group_chat_manager, planner_agent, memory_store

    async def _create_planner_agent(self, kernel, memory_store, tool_list):
        """Create a real PlannerAgent instance."""
        planner_agent = PlannerAgent(
            kernel=kernel,
            session_id=self.session_id,
            user_id=self.user_id,
            memory_store=memory_store,
            available_agents=["HumanAgent", "GenericAgent", "MarketingAgent"],
            agent_tools_list=tool_list
        )
        return planner_agent
        
    async def _create_human_agent(self, kernel, memory_store):
        """Create a real HumanAgent instance."""
        # Initialize a HumanAgent with async initialization
        human_agent = HumanAgent(
            kernel=kernel,
            session_id=self.session_id,
            user_id=self.user_id,
            memory_store=memory_store
        )
        await human_agent.async_init()
        return human_agent
        
    async def _create_generic_agent(self, kernel, memory_store):
        """Create a real GenericAgent instance."""
        # Initialize a GenericAgent with async initialization
        generic_agent = GenericAgent(
            kernel=kernel,
            session_id=self.session_id,
            user_id=self.user_id,
            memory_store=memory_store
        )
        await generic_agent.async_init()
        return generic_agent

    async def test_handle_input_task(self):
        """Test that the group chat manager correctly processes an input task."""
        # Initialize components
        await self.initialize_group_chat_manager()
        
        # Create input task
        input_task = InputTask(
            session_id=self.session_id,
            user_id=self.user_id,
            description=self.test_task
        )
        
        # Call handle_input_task on the group chat manager
        result = await self.group_chat_manager.handle_input_task(input_task.json())
        
        # Check that result contains a success message
        self.assertIn("Plan creation initiated", result)
        
        # Verify plan was created in memory store
        plan = await self.memory_store.get_plan_by_session(self.session_id)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.session_id, self.session_id)
        self.assertEqual(plan.overall_status, PlanStatus.in_progress)
        
        # Verify steps were created
        steps = await self.memory_store.get_steps_for_plan(plan.id, self.session_id)
        self.assertGreater(len(steps), 0)
        
        # Log plan details
        print(f"\nCreated plan with ID: {plan.id}")
        print(f"Goal: {plan.initial_goal}")
        print(f"Summary: {plan.summary}")
        
        print("\nSteps:")
        for i, step in enumerate(steps):
            print(f"  {i+1}. Agent: {step.agent}, Action: {step.action}")
        
        return plan, steps

    async def test_human_feedback(self):
        """Test providing human feedback on a plan step."""
        # First create a plan with steps
        plan, steps = await self.test_handle_input_task()
        
        # Choose the first step for approval
        first_step = steps[0]
        
        # Create feedback data
        feedback_data = {
            "session_id": self.session_id,
            "plan_id": plan.id,
            "step_id": first_step.id,
            "approved": True,
            "human_feedback": "This looks good. Proceed with this step."
        }
        
        # Call handle_human_feedback
        result = await self.group_chat_manager.handle_human_feedback(json.dumps(feedback_data))
        
        # Verify the result indicates success
        self.assertIn("execution started", result)
        
        # Get the updated step
        updated_step = await self.memory_store.get_step(first_step.id, self.session_id)
        
        # Verify step status was changed
        self.assertNotEqual(updated_step.status, StepStatus.planned)
        self.assertEqual(updated_step.human_approval_status, HumanFeedbackStatus.accepted)
        self.assertEqual(updated_step.human_feedback, feedback_data["human_feedback"] + " Today's date is " + datetime.now().date().isoformat() + ". No human feedback provided on the overall plan.")
        
        # Get messages to verify agent messages were created
        messages = await self.memory_store.get_messages_by_plan(plan.id)
        self.assertGreater(len(messages), 0)
        
        # Verify there is a message about the step execution
        self.assertTrue(any("perform action" in msg.content.lower() for msg in messages))
        
        print(f"\nApproved step: {first_step.id}")
        print(f"Updated step status: {updated_step.status}")
        print(f"Messages:")
        for msg in messages[-3:]:  # Show the last few messages
            print(f"  - {msg.source}: {msg.content[:50]}...")
        
        return updated_step

    async def test_execute_next_step(self):
        """Test executing the next step in a plan."""
        # First create a plan with steps
        plan, steps = await self.test_handle_input_task()
        
        # Call execute_next_step
        result = await self.group_chat_manager.execute_next_step(self.session_id, plan.id)
        
        # Verify the result indicates a step execution request
        self.assertIn("execution started", result)
        
        # Get all steps again to check status changes
        updated_steps = await self.memory_store.get_steps_for_plan(plan.id, self.session_id)
        
        # Verify at least one step has changed status
        action_requested_steps = [step for step in updated_steps if step.status == StepStatus.action_requested]
        self.assertGreaterEqual(len(action_requested_steps), 1)
        
        print(f"\nExecuted next step for plan: {plan.id}")
        print(f"Steps with action_requested status: {len(action_requested_steps)}")
        
        return updated_steps

    async def test_run_group_chat(self):
        """Test running the group chat with a direct user input."""
        # Initialize components
        await self.initialize_group_chat_manager()
        
        # First ensure the group chat is initialized
        await self.group_chat_manager.initialize_group_chat()
        
        # Run a test conversation
        user_input = "What's the best way to create a social media campaign for our new product?"
        result = await self.group_chat_manager.run_group_chat(user_input)
        
        # Verify we got a reasonable response
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 50)  # Should have a substantial response
        
        # Get messages to verify agent messages were created
        messages = await self.memory_store.get_messages_by_session(self.session_id)
        self.assertGreater(len(messages), 0)
        
        print(f"\nGroup chat response to: '{user_input}'")
        print(f"Response (partial): {result[:100]}...")
        print(f"Total messages: {len(messages)}")
        
        return result, messages

    async def test_conversation_history_generation(self):
        """Test the conversation history generation function."""
        # First create a plan with steps
        plan, steps = await self.test_handle_input_task()
        
        # Approve and execute a step to create some history
        first_step = steps[0]
        
        # Create feedback data
        feedback_data = {
            "session_id": self.session_id,
            "plan_id": plan.id,
            "step_id": first_step.id,
            "approved": True,
            "human_feedback": "This looks good. Please proceed."
        }
        
        # Apply feedback and execute the step
        await self.group_chat_manager.handle_human_feedback(json.dumps(feedback_data))
        
        # Generate conversation history for the next step
        if len(steps) > 1:
            second_step = steps[1]
            conversation_history = await self.group_chat_manager._generate_conversation_history(steps, second_step.id, plan)
            
            # Verify the conversation history contains expected elements
            self.assertIn("conversation_history", conversation_history)
            self.assertIn(plan.summary, conversation_history)
            
            print(f"\nGenerated conversation history:")
            print(f"{conversation_history[:200]}...")
            
            return conversation_history

    async def run_all_tests(self):
        """Run all tests in sequence."""
        # Call setUp explicitly to ensure environment is properly initialized
        self.setUp()
        
        try:
            # Test 1: Handle input task (creates a plan)
            print("\n===== Testing handle_input_task =====")
            plan, steps = await self.test_handle_input_task()
            
            # Test 2: Test providing human feedback
            print("\n===== Testing human_feedback =====")
            updated_step = await self.test_human_feedback()
            
            # Test 3: Test execute_next_step
            print("\n===== Testing execute_next_step =====")
            await self.test_execute_next_step()
            
            # Test 4: Test run_group_chat
            print("\n===== Testing run_group_chat =====")
            await self.test_run_group_chat()
            
            # Test 5: Test conversation history generation
            print("\n===== Testing conversation_history_generation =====")
            await self.test_conversation_history_generation()
            
            print("\nAll tests completed successfully!")
            
        except Exception as e:
            print(f"Tests failed: {e}")
            raise
        finally:
            # Call tearDown explicitly to ensure proper cleanup
            await self.tearDown_async()

def run_tests():
    """Run the tests."""
    test = GroupChatManagerIntegrationTest()
    
    # Create and run the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(test.run_all_tests())
    finally:
        loop.close()
    
if __name__ == '__main__':
    run_tests()
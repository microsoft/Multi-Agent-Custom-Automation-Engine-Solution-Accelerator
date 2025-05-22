"""Integration tests for the PlannerAgent.

This test file verifies that the PlannerAgent correctly plans tasks, breaks them down into steps,
and properly integrates with Cosmos DB memory context. These are real integration tests
using real Cosmos DB connections and then cleaning up the test data afterward.
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

from config_kernel import Config
from kernel_agents.planner_agent import PlannerAgent
from context.cosmos_memory_kernel import CosmosMemoryContext
from models.messages_kernel import (
    InputTask, 
    Plan, 
    Step, 
    AgentMessage,
    PlanStatus,
    StepStatus,
    HumanFeedbackStatus
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

class PlannerAgentIntegrationTest(unittest.TestCase):
    """Integration tests for the PlannerAgent."""

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

    async def initialize_planner_agent(self):
        """Initialize the planner agent and memory store for testing."""
        # Create Kernel
        kernel = Config.CreateKernel()
        
        # Create memory store with cleanup capabilities
        # Using Config settings instead of direct env vars
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
        
        # Create planner agent
        planner_agent = PlannerAgent(
            kernel=kernel,
            session_id=self.session_id,
            user_id=self.user_id,
            memory_store=memory_store,
            available_agents=["HumanAgent", "HrAgent", "MarketingAgent", "ProductAgent", 
                             "ProcurementAgent", "TechSupportAgent", "GenericAgent"],
            agent_tools_list=tool_list
        )
        
        self.planner_agent = planner_agent
        self.memory_store = memory_store
        return planner_agent, memory_store

    async def test_handle_input_task(self):
        """Test that the planner agent correctly processes an input task."""
        # Initialize components
        await self.initialize_planner_agent()
        
        # Create input task
        input_task = InputTask(
            session_id=self.session_id,
            user_id=self.user_id,
            description=self.test_task
        )
        
        # Call handle_input_task
        args = KernelArguments(input_task_json=input_task.json())
        result = await self.planner_agent.handle_input_task(args)
        
        # Check that result contains a success message
        self.assertIn("created successfully", result)
        
        # Verify plan was created in memory store
        plan = await self.memory_store.get_plan_by_session(self.session_id)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.session_id, self.session_id)
        self.assertEqual(plan.user_id, self.user_id)
        self.assertEqual(plan.overall_status, PlanStatus.in_progress)
        
        # Verify steps were created
        steps = await self.memory_store.get_steps_for_plan(plan.id, self.session_id)
        self.assertGreater(len(steps), 0)
        
        # Log plan details
        print(f"\nCreated plan with ID: {plan.id}")
        print(f"Goal: {plan.initial_goal}")
        print(f"Summary: {plan.summary}")
        if hasattr(plan, 'human_clarification_request') and plan.human_clarification_request:
            print(f"Human clarification request: {plan.human_clarification_request}")
        
        print("\nSteps:")
        for i, step in enumerate(steps):
            print(f"  {i+1}. Agent: {step.agent}, Action: {step.action}")
        
        return plan, steps

    async def test_plan_generation_content(self):
        """Test that the generated plan content is accurate and appropriate."""
        # Get the plan and steps
        plan, steps = await self.test_handle_input_task()
        
        # Check that the plan has appropriate content related to marketing
        marketing_terms = ["marketing", "product", "launch", "campaign", "strategy", "promotion"]
        self.assertTrue(any(term in plan.initial_goal.lower() for term in marketing_terms))
        
        # Check that the plan contains appropriate steps
        self.assertTrue(any(step.agent == "MarketingAgent" for step in steps))
        
        # Verify step structure
        for step in steps:
            self.assertIsNotNone(step.action)
            self.assertIsNotNone(step.agent)
            self.assertEqual(step.status, StepStatus.planned)

    async def test_handle_plan_clarification(self):
        """Test that the planner agent correctly handles human clarification."""
        # Get the plan
        plan, _ = await self.test_handle_input_task()
        
        # Test adding clarification to the plan
        clarification = "This is a luxury product targeting high-income professionals. Budget is $50,000. Launch date is June 15, 2025."
        
        # Create clarification request
        args = KernelArguments(
            session_id=self.session_id,
            human_clarification=clarification
        )
        
        # Handle clarification
        result = await self.planner_agent.handle_plan_clarification(args)
        
        # Check that result indicates success
        self.assertIn("updated with human clarification", result)
        
        # Verify plan was updated in memory store
        updated_plan = await self.memory_store.get_plan_by_session(self.session_id)
        self.assertEqual(updated_plan.human_clarification_response, clarification)
        
        # Check that messages were added
        messages = await self.memory_store.get_messages_by_session(self.session_id)
        self.assertTrue(any(msg.content == clarification for msg in messages))
        self.assertTrue(any("plan has been updated" in msg.content for msg in messages))
        
        print(f"\nAdded clarification: {clarification}")
        print(f"Updated plan: {updated_plan.id}")

    async def test_create_structured_plan(self):
        """Test the _create_structured_plan method directly."""
        # Initialize components
        await self.initialize_planner_agent()
        
        # Create input task
        input_task = InputTask(
            session_id=self.session_id,
            user_id=self.user_id,
            description="Arrange a technical webinar for introducing our new software development kit"
        )
        
        # Call _create_structured_plan directly
        plan, steps = await self.planner_agent._create_structured_plan(input_task)
        
        # Verify plan and steps were created
        self.assertIsNotNone(plan)
        self.assertIsNotNone(steps)
        self.assertGreater(len(steps), 0)
        
        # Check plan content
        self.assertIn("webinar", plan.initial_goal.lower())
        self.assertEqual(plan.session_id, self.session_id)
        
        # Check step assignments
        tech_terms = ["webinar", "technical", "software", "development", "sdk"]
        relevant_agents = ["TechSupportAgent", "ProductAgent"]
        
        # At least one step should be assigned to a relevant agent
        self.assertTrue(any(step.agent in relevant_agents for step in steps))
        
        print(f"\nCreated technical webinar plan with {len(steps)} steps")
        print(f"Steps assigned to: {', '.join(set(step.agent for step in steps))}")

    async def test_hr_agent_selection(self):
        """Test that the planner correctly assigns employee onboarding tasks to the HR agent."""
        # Initialize components
        await self.initialize_planner_agent()
        
        # Create an onboarding task
        input_task = InputTask(
            session_id=self.session_id,
            user_id=self.user_id,
            description="Onboard a new employee, Jessica Smith."
        )
        
        print("\n\n==== TESTING HR AGENT SELECTION FOR ONBOARDING ====")
        print(f"Task: '{input_task.description}'")
        
        # Call handle_input_task
        args = KernelArguments(input_task_json=input_task.json())
        result = await self.planner_agent.handle_input_task(args)
        
        # Check that result contains a success message
        self.assertIn("created successfully", result)
        
        # Verify plan was created in memory store
        plan = await self.memory_store.get_plan_by_session(self.session_id)
        self.assertIsNotNone(plan)
        
        # Verify steps were created
        steps = await self.memory_store.get_steps_for_plan(plan.id, self.session_id)
        self.assertGreater(len(steps), 0)
        
        # Log plan details
        print(f"\n📋 Created onboarding plan with ID: {plan.id}")
        print(f"🎯 Goal: {plan.initial_goal}")
        print(f"📝 Summary: {plan.summary}")
        
        print("\n📝 Steps:")
        for i, step in enumerate(steps):
            print(f"  {i+1}. 👤 Agent: {step.agent}, 🔧 Action: {step.action}")
        
        # Count agents used in the plan
        agent_counts = {}
        for step in steps:
            agent_counts[step.agent] = agent_counts.get(step.agent, 0) + 1
            
        print("\n📊 Agent Distribution:")
        for agent, count in agent_counts.items():
            print(f"  {agent}: {count} step(s)")
        
        # The critical test: verify that at least one step is assigned to HrAgent
        hr_steps = [step for step in steps if step.agent == "HrAgent"]
        has_hr_steps = len(hr_steps) > 0
        self.assertTrue(has_hr_steps, "No steps assigned to HrAgent for an onboarding task")
        
        if has_hr_steps:
            print("\n✅ TEST PASSED: HrAgent is used for onboarding task")
        else:
            print("\n❌ TEST FAILED: HrAgent is not used for onboarding task")
        
        # Verify that no steps are incorrectly assigned to MarketingAgent
        marketing_steps = [step for step in steps if step.agent == "MarketingAgent"]
        no_marketing_steps = len(marketing_steps) == 0
        self.assertEqual(len(marketing_steps), 0, 
                         f"Found {len(marketing_steps)} steps incorrectly assigned to MarketingAgent for an onboarding task")
        
        if no_marketing_steps:
            print("✅ TEST PASSED: No MarketingAgent steps for onboarding task")
        else:
            print(f"❌ TEST FAILED: Found {len(marketing_steps)} steps incorrectly assigned to MarketingAgent")
            
        # Verify that the first step or a step containing "onboard" is assigned to HrAgent
        first_agent = steps[0].agent if steps else None
        onboarding_steps = [step for step in steps if "onboard" in step.action.lower()]
        
        if onboarding_steps:
            onboard_correct = onboarding_steps[0].agent == "HrAgent"
            self.assertEqual(onboarding_steps[0].agent, "HrAgent", 
                            "The step containing 'onboard' was not assigned to HrAgent")
            if onboard_correct:
                print("✅ TEST PASSED: Steps containing 'onboard' are assigned to HrAgent")
            else:
                print(f"❌ TEST FAILED: Step containing 'onboard' assigned to {onboarding_steps[0].agent}, not HrAgent")
            
        # If no specific "onboard" step but we have steps, the first should likely be HrAgent
        elif steps and "hr" not in first_agent.lower():
            first_step_correct = first_agent == "HrAgent"
            self.assertEqual(first_agent, "HrAgent", 
                            f"The first step was assigned to {first_agent}, not HrAgent")
            if first_step_correct:
                print("✅ TEST PASSED: First step is assigned to HrAgent")
            else:
                print(f"❌ TEST FAILED: First step assigned to {first_agent}, not HrAgent")
                
        print("\n==== END HR AGENT SELECTION TEST ====\n")
            
        return plan, steps

    async def run_all_tests(self):
        """Run all tests in sequence."""
        # Call setUp explicitly to ensure environment is properly initialized
        self.setUp()
        
        try:
            # Test 1: Handle input task (creates a plan)
            print("\n===== Testing handle_input_task =====")
            await self.test_handle_input_task()
            
            # Test 2: Verify the content of the generated plan
            print("\n===== Testing plan generation content =====")
            await self.test_plan_generation_content()
            
            # Test 3: Handle plan clarification
            print("\n===== Testing handle_plan_clarification =====")
            await self.test_handle_plan_clarification()
            
            # Test 4: Test the structured plan creation directly (with a different task)
            print("\n===== Testing _create_structured_plan directly =====")
            await self.test_create_structured_plan()
            
            # Test 5: Verify HR agent selection for onboarding tasks
            print("\n===== Testing HR agent selection =====")
            await self.test_hr_agent_selection()
            
            print("\nAll tests completed successfully!")
            
        except Exception as e:
            print(f"Tests failed: {e}")
            raise
        finally:
            # Call tearDown explicitly to ensure proper cleanup
            await self.tearDown_async()

def run_tests():
    """Run the tests."""
    test = PlannerAgentIntegrationTest()
    
    # Create and run the event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(test.run_all_tests())
    finally:
        loop.close()
    
if __name__ == '__main__':
    run_tests()
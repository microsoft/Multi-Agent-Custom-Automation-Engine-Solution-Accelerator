"""
Magentic orchestration manager for employee onboarding agent coordination.
Handles agent orchestration, runtime management, and task execution.
"""
from callbacks.global_debug import DebugGlobalAccess
from callbacks.response_handlers import (enhanced_agent_response_callback,
                                         streaming_agent_response_callback)
from config.settings import azure_config
from magentic_agents.team_factory import create_employee_onboarding_agents
from semantic_kernel.agents.orchestration.magentic import (
    MagenticOrchestration, StandardMagenticManager)
from semantic_kernel.agents.runtime import InProcessRuntime

from .human_approval_manager import (HumanApprovalMagenticManager,
                                     InteractiveStepMagenticManager)


class OnboardingOrchestrationManager:
    """Manages the Magentic orchestration for employee onboarding scenarios."""
    
    def __init__(self, enable_human_approval=True, step_by_step=False, structured_output=True):
        self.orchestration = None
        self.runtime = None
        self.enable_human_approval = enable_human_approval
        self.step_by_step = step_by_step
        self.structured_output = structured_output
    
    async def initialize(self):
        """Initialize the orchestration with specialized agents."""
        print("🔧 Initializing Employee Onboarding Orchestration...")
        
        # Create execution settings
        execution_settings = azure_config.create_execution_settings()
        
        # Create chat completion service for manager
        manager_chat_service = azure_config.create_chat_completion_service(use_reasoning_model=True)
        
        # Create agents
        agents = await create_employee_onboarding_agents()

        # Choose manager type based on configuration
        if self.step_by_step:
            print("🎯 Using Interactive Step-by-Step Approval Manager")
            manager = InteractiveStepMagenticManager(
                chat_completion_service=manager_chat_service,
                execution_settings=execution_settings
            )
            manager.enable_step_by_step_approval(True)
        elif self.enable_human_approval:
            print("🎯 Using Human Approval Manager")
            manager = HumanApprovalMagenticManager(
                chat_completion_service=manager_chat_service,
                execution_settings=execution_settings
            )
        else:
            print("🎯 Using Standard Manager (no approval required)")
            manager = StandardMagenticManager(
                chat_completion_service=manager_chat_service,
                execution_settings=execution_settings
            )       
        
        # Create Magentic orchestration
        self.orchestration = MagenticOrchestration(
            members=agents,
            manager=manager,
            agent_response_callback=enhanced_agent_response_callback,
            streaming_agent_response_callback=streaming_agent_response_callback,
        )

        DebugGlobalAccess.add_manager(manager)
        
        # Create and start runtime
        self.runtime = InProcessRuntime()
        self.runtime.start()
        
        print("✅ Employee Onboarding Orchestration initialized successfully!")
        return self.orchestration, self.runtime
    
    async def execute_task(self, task: str):
        """Execute a task using the orchestration."""
        if not self.orchestration or not self.runtime:
            raise RuntimeError("Orchestration not initialized. Call initialize() first.")
        
        print(f"\n🎯 Processing employee onboarding task: {task}")
        print("-" * 60)
        
        # Invoke the orchestration (approval will happen inside the manager's plan method if enabled)
        orchestration_result = await self.orchestration.invoke(
            task=task,
            runtime=self.runtime,
        )
        
        # Wait for results
        try:
            print("\n📋 Agent responses:")
            value = await orchestration_result.get()
            print(f"\n✅ Task completed successfully:")
            print("=" * 60)
            print(value)
            print("=" * 60)
            return value
        except Exception as e:
            print(f"❌ Task execution error: {e}")
            print(f"Error type: {type(e).__name__}")
            raise e
    
    async def cleanup(self):
        """Clean up resources."""
        if self.runtime:
            await self.runtime.stop_when_idle()
            print("🧹 Runtime stopped and resources cleaned up")
    
    async def _create_plan_and_get_approval(self, task: str) -> bool:
        """Create a plan preview and get user approval before execution."""
        print("\n🤖 Human-in-the-Loop Plan Creation:")
        print("=" * 60)
        print(f"Task: {task}")
        print("=" * 60)
        
        # Analyze the task and create a realistic plan preview
        plan_preview = self._analyze_task_and_create_plan_preview(task)
        
        # Show the plan preview
        print("\n📋 Predicted Execution Plan:")
        for i, step in enumerate(plan_preview["steps"], 1):
            print(f"  Step {i}: {step}")
        
        print(f"\n👥 Agents to be involved:")
        for agent_name, role in plan_preview["agents"].items():
            print(f"  • {agent_name}: {role}")
        
        print(f"\n⏱️  Estimated complexity: {plan_preview['complexity']}")
        print(f"🎯 Expected outcome: {plan_preview['outcome']}")
        
        print("\n⚠️  Note: This is a preview based on task analysis.")
        print("The actual execution may vary based on agent decisions.")
        
        while True:
            approval = input("\n❓ Approve this execution plan? [y/n/details]: ").strip().lower()
            
            if approval in ['y', 'yes']:
                print("✅ Plan approved by user - proceeding with execution...")
                return True
            elif approval in ['n', 'no']:
                print("❌ Plan rejected by user")
                return False
            elif approval in ['d', 'details']:
                self._show_detailed_task_analysis(task, plan_preview)
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'details' for more info")
    
    def _analyze_task_and_create_plan_preview(self, task: str) -> dict:
        """Analyze the task and create a realistic plan preview."""
        task_lower = task.lower()
        
        # Determine primary task type
        task_types = []
        if any(word in task_lower for word in ['research', 'find', 'search', 'current', 'latest', 'information']):
            task_types.append('research')
        if any(word in task_lower for word in ['analyze', 'calculate', 'data', 'metrics', 'chart', 'visualization']):
            task_types.append('analysis')
        if any(word in task_lower for word in ['design', 'plan', 'strategy', 'recommend', 'create', 'develop']):
            task_types.append('planning')
        if any(word in task_lower for word in ['code', 'program', 'script', 'function', 'api']):
            task_types.append('coding')
        
        # If no specific type detected, default to general planning
        if not task_types:
            task_types = ['planning']
        
        # Create plan based on detected task types
        steps = []
        agents = {}
        complexity = "Medium"
        
        if 'research' in task_types:
            steps.append("Research Agent will search for current information using Bing")
            steps.append("Research Agent will gather relevant data and best practices")
            agents["Research Agent"] = "Web search and information gathering"
            complexity = "Medium-High"
        
        if 'analysis' in task_types:
            steps.append("Coder Agent will analyze data and perform calculations")
            steps.append("Coder Agent will create visualizations and metrics")
            agents["Coder Agent"] = "Data analysis and visualization"
            if complexity == "Medium":
                complexity = "Medium-High"
        
        if 'planning' in task_types or 'coding' in task_types:
            steps.append("Reasoning Agent will provide strategic analysis")
            steps.append("Reasoning Agent will synthesize findings and create recommendations")
            agents["Reasoning Agent"] = "Strategic thinking and synthesis"
        
        # Add coordination steps
        if len(agents) > 1:
            steps.insert(0, "Manager will analyze task and create detailed execution plan")
            steps.append("Manager will coordinate agent collaboration")
            steps.append("Manager will synthesize final results from all agents")
            complexity = "High"
        
        # Determine expected outcome
        if 'research' in task_types and 'analysis' in task_types:
            outcome = "Comprehensive report with data analysis and recommendations"
        elif 'research' in task_types:
            outcome = "Detailed research summary with current information"
        elif 'analysis' in task_types:
            outcome = "Data analysis with charts and calculated metrics"
        elif 'planning' in task_types:
            outcome = "Strategic plan with actionable recommendations"
        else:
            outcome = "Structured response addressing the task requirements"
        
        return {
            "steps": steps,
            "agents": agents,
            "complexity": complexity,
            "outcome": outcome,
            "task_types": task_types
        }
    
    def _show_detailed_task_analysis(self, task: str, plan_preview: dict):
        """Show detailed analysis of the task and execution plan."""
        print("\n📖 Detailed Task Analysis:")
        print("-" * 40)
        
        print(f"🎯 Original Task: {task}")
        print(f"\n🔍 Detected Task Types: {', '.join(plan_preview['task_types'])}")
        
        print(f"\n📋 Execution Steps ({len(plan_preview['steps'])} total):")
        for i, step in enumerate(plan_preview["steps"], 1):
            print(f"  {i}. {step}")
        
        print(f"\n🤖 Agent Responsibilities:")
        for agent_name, role in plan_preview["agents"].items():
            print(f"  • {agent_name}: {role}")
        
        print(f"\n⏱️  Complexity Assessment: {plan_preview['complexity']}")
        print(f"🎯 Expected Final Outcome: {plan_preview['outcome']}")
        
        print("\n🔄 Execution Flow:")
        print("  1. Task analysis and plan creation")
        print("  2. Agent assignment based on capabilities")
        print("  3. Parallel/sequential agent execution")
        print("  4. Result coordination and synthesis")
        print("  5. Final response compilation")
        
        print("\n💡 This preview helps you understand what will happen")
        print("before committing to the full execution.")
    
    def _show_task_details(self, task: str):
        """Show detailed information about what the task execution will involve."""
        print("\n📖 Task Execution Details:")
        print("-" * 40)
        
        # Analyze task type and show expected flow
        task_lower = task.lower()
        
        print("🔍 Task Analysis:")
        if any(word in task_lower for word in ['research', 'find', 'search', 'current', 'latest']):
            print("  → Research-Heavy Task Detected")
            print("  → Research Agent will search for current information")
            print("  → May use Bing search tools and MCP capabilities")
            
        if any(word in task_lower for word in ['analyze', 'calculate', 'data', 'metrics', 'chart']):
            print("  → Analysis Task Detected")
            print("  → Coder Agent will process and analyze data")
            print("  → May create visualizations and calculations")
            
        if any(word in task_lower for word in ['design', 'plan', 'strategy', 'recommend']):
            print("  → Strategic Planning Task Detected")
            print("  → Reasoning Agent will lead strategic analysis")
            print("  → Research Agent will gather best practices")
        
        print(f"\n🎯 Available Agents:")
        print("  • Research Agent: Searches for current information and best practices")
        print("  • Coder Agent: Analyzes data, creates code, and generates visualizations")  
        print("  • Reasoning Agent: Provides strategic analysis and recommendations")
        
        print(f"\n📝 Task: {task}")
        print("\n🔄 Execution Flow:")
        print("  1. Magentic Manager creates execution plan")
        print("  2. Agents collaborate based on task requirements")
        print("  3. Real-time progress shown through callbacks")
        print("  4. Final results synthesized and presented")

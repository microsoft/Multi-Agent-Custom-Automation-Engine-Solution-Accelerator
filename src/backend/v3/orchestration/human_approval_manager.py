"""
Human-in-the-loop Magentic Manager for employee onboarding orchestration.
Extends StandardMagenticManager to add approval gates before plan execution.
"""

import re
from typing import Any, List, Optional

from semantic_kernel.agents import Agent
from semantic_kernel.agents.orchestration.magentic import \
    StandardMagenticManager
from semantic_kernel.contents import ChatMessageContent
from v3.models.orchestration_models import (AgentDefinition,
                                            PlannerResponsePlan,
                                            PlannerResponseStep)


class HumanApprovalMagenticManager(StandardMagenticManager):
    """
    Extended Magentic manager that requires human approval before executing plan steps.
    Provides interactive approval for each step in the orchestration plan.
    """
    
    # Define Pydantic fields to avoid validation errors
    approval_enabled: bool = True
    
    def __init__(self, *args, **kwargs):
        # Remove any custom kwargs before passing to parent
        approval_enabled = kwargs.pop('approval_enabled', True)
        # Remove structured_output since we're not using it anymore
        kwargs.pop('structured_output', False)
        super().__init__(*args, **kwargs)
        
        # Use a private dictionary to store our settings to avoid Pydantic validation issues
        self._approval_settings = {
            'enabled': approval_enabled,
            'auto_approve_keywords': ["hello", "test", "greet"],
            'plan_approved': False  # Track if plan was approved
        }
    
    def enable_human_approval(self, enabled: bool = True):
        """Enable or disable human approval requirement."""
        self._approval_settings['enabled'] = enabled
        print(f"🎯 Human approval {'enabled' if enabled else 'disabled'}")

    async def plan(self, magentic_context) -> Any:
        """
        Override the plan method to create the plan first, then ask for approval before execution.
        """
        # Extract task text from the context
        task_text = magentic_context.task
        if hasattr(task_text, 'content'):
            task_text = task_text.content
        elif not isinstance(task_text, str):
            task_text = str(task_text)
        
        print(f"\n🎯 Human-in-the-Loop Magentic Manager Creating Plan:")
        print(f"   Task: {task_text}")
        print("-" * 60)
        
        # First, let the parent create the actual plan
        print("📋 Creating execution plan...")
        plan = await super().plan(magentic_context)

        planner_response_plan = self._plan_to_objects(magentic_context.participant_descriptions)
        
        # If planning failed or returned early, just return the result
        if isinstance(plan, ChatMessageContent):
            # Now show the actual plan and ask for approval
            if self._approval_settings['enabled']:
                plan_approved = await self._get_plan_approval_with_details(
                    task_text, 
                    magentic_context.participant_descriptions, 
                    plan
                )
                if not plan_approved:
                    print("❌ Plan execution cancelled by user")
                    return ChatMessageContent(
                        role="assistant",
                        content="Plan execution was cancelled by the user."
                    )
            
            # If we get here, plan is approved - return the plan for execution
            print("✅ Plan approved - proceeding with execution...")
            return plan
        
        # If plan is not a ChatMessageContent, still show it and ask for approval
        if self._approval_settings['enabled']:
            plan_approved = await self._get_plan_approval_with_details(
                task_text, 
                magentic_context.participant_descriptions, 
                plan
            )
            if not plan_approved:
                print("❌ Plan execution cancelled by user")
                return ChatMessageContent(
                    role="assistant",
                    content="Plan execution was cancelled by the user."
                )
        
        # If we get here, plan is approved - return the plan for execution
        print("✅ Plan approved - proceeding with execution...")
        return plan
    
    def _should_auto_approve(self, task) -> bool:
        """Check if task should be auto-approved based on keywords."""
        # Handle both string and ChatMessageContent objects
        if hasattr(task, 'content'):
            task_text = task.content
        elif isinstance(task, str):
            task_text = task
        else:
            task_text = str(task)
        
        task_lower = task_text.lower()
        return any(keyword in task_lower for keyword in self._approval_settings['auto_approve_keywords'])
    
    async def _get_plan_approval_with_details(self, task: str, participant_descriptions: dict, plan: Any) -> bool:
        """Get human approval for the actual created plan before execution."""
        print("\n🤖 Magentic Manager Created This Execution Plan:")
        print("=" * 80)
        print(f"Task: {task}")
        print(f"Available Agents: {list(participant_descriptions.keys())}")
        print("=" * 80)
        
        # Try to extract and display plan details
        print("\n📋 Actual Execution Plan Details:")
        try:
            if hasattr(plan, 'content') and plan.content:
                # Parse the plan into JSON format for display
                parsed_plan = self._parse_plan_to_json(plan.content, participant_descriptions)
                
                print("  📊 Structured Plan:")
                print(f"    Task Summary: {parsed_plan['plan_description']['task_summary']}")
                print(f"    Complexity: {parsed_plan['plan_description']['complexity_assessment']}")
                print(f"    Steps to Execute:")
                
                for step in parsed_plan['steps']:
                    print(f"      {step['step_number']}. [{step['step_agent']}] {step['step_prompt']}")
                
                print("\n  📄 Original Plan Content:")
                lines = plan.content.split('\n')
                for line in lines:
                    if line.strip():
                        print(f"    {line}")
            else:
                print("  ❌ ERROR: No plan content available")
                print(f"  Plan Type: {type(plan).__name__}")
        except Exception as e:
            print(f"  ❌ ERROR: Could not parse plan details: {e}")
            print(f"  Plan Type: {type(plan).__name__}")
            # Fallback to show raw content if available
            if hasattr(plan, 'content') and plan.content:
                print(f"  Raw Content: {plan.content}")
        
        print(f"\n👥 Available Agents:")
        for agent_name, description in participant_descriptions.items():
            print(f"  • {agent_name}: {description}")
        
        print("\n⚠️  This is the ACTUAL execution plan that will be run.")
        print("You can see exactly what the Magentic Manager has planned.")
        
        while True:
            approval = input("\n❓ Approve this execution plan? [y/n/details]: ").strip().lower()
            
            if approval in ['y', 'yes']:
                print("✅ Plan approved by user")
                return True
            elif approval in ['n', 'no']:
                print("❌ Plan rejected by user")
                return False
            elif approval in ['d', 'details']:
                self._show_detailed_plan_info(task, participant_descriptions, plan)
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'details' for more info")

    async def _get_plan_approval(self, task: str, agents: List[Agent]) -> bool:
        """Get human approval for the plan before execution."""
        print("\n🤖 Magentic Manager Plan Preview:")
        print("=" * 60)
        print(f"Task: {task}")
        print(f"Available Agents: {[agent.name for agent in agents]}")
        print("=" * 60)
        
        print("\n📋 The system will:")
        print("  1. Analyze the task and create an execution plan")
        print("  2. Assign tasks to appropriate agents (Research, Coder, Reasoning)")
        print("  3. Coordinate agent collaboration")
        print("  4. Synthesize final results")
        
        print("\n⚠️  Note: Once approved, the plan will execute automatically.")
        print("You can monitor progress through agent response callbacks.")
        
        while True:
            approval = input("\n❓ Approve plan execution? [y/n/details]: ").strip().lower()
            
            if approval in ['y', 'yes']:
                print("✅ Plan approved by user")
                return True
            elif approval in ['n', 'no']:
                print("❌ Plan rejected by user")
                return False
            elif approval in ['d', 'details']:
                self._show_detailed_plan_info(task, agents)
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'details' for more info")
    
    def _show_detailed_plan_info(self, task: str, participant_descriptions: dict, plan: Any = None):
        """Show detailed information about the planned execution."""
        print("\n📖 Detailed Plan Information:")
        print("-" * 80)
        
        # Show the actual plan details if provided
        if plan:
            print("🔍 Plan Content Analysis:")
            try:
                if hasattr(plan, 'content') and plan.content:
                    # Parse the plan into structured JSON format
                    parsed_plan = self._parse_plan_to_json(plan.content, participant_descriptions)
                    
                    print("  📊 Structured Analysis:")
                    print(f"    Task Summary: {parsed_plan['plan_description']['task_summary']}")
                    print(f"    Complexity: {parsed_plan['plan_description']['complexity_assessment']}")
                    print(f"    Total Steps: {len(parsed_plan['steps'])}")
                    
                    print("  📋 Step-by-Step Breakdown:")
                    for step in parsed_plan['steps']:
                        print(f"    {step['step_number']}. [{step['step_agent']}]")
                        print(f"       Action: {step['step_prompt']}")
                    
                    print("  📄 Raw Plan Content:")
                    content_lines = plan.content.split('\n')
                    for line in content_lines:
                        if line.strip():
                            print(f"    → {line.strip()}")
                            
                elif hasattr(plan, '__dict__'):
                    print("  Plan object attributes:")
                    for key, value in plan.__dict__.items():
                        print(f"    {key}: {str(value)[:100]}...")
            except Exception as e:
                print(f"  Error analyzing plan: {e}")
        
        # Analyze task type and show expected flow
        task_lower = task.lower()
        
        if any(word in task_lower for word in ['research', 'find', 'search', 'current', 'latest']):
            print("\n🔍 Research-Heavy Task Detected:")
            print("  → Research Agent will search for current information")
            print("  → May use Bing search tools and MCP capabilities")
            print("  → Results will be analyzed by Reasoning Agent")
            
        if any(word in task_lower for word in ['analyze', 'calculate', 'data', 'metrics', 'chart']):
            print("\n🔢 Analysis Task Detected:")
            print("  → Coder Agent will process and analyze data")
            print("  → May create visualizations and calculations")
            print("  → Research Agent may gather supporting data")
            
        if any(word in task_lower for word in ['design', 'plan', 'strategy', 'recommend']):
            print("\n🧠 Strategic Planning Task Detected:")
            print("  → Reasoning Agent will lead strategic analysis")
            print("  → Research Agent will gather best practices")
            print("  → Comprehensive recommendations will be provided")
        
        print(f"\n👥 Available Agents:")
        for agent_name, description in participant_descriptions.items():
            print(f"  • {agent_name}: {description}")
        
        print(f"\n📝 Task: {task}")
        print("\nThe Magentic Manager will automatically coordinate these agents")
        print("based on the task requirements and agent capabilities.")

    def _plan_to_objects(self, team: dict[str,str]) -> PlannerResponsePlan:
        """
        Parse a task description string with bullet points and agent assignments into a structured plan.
        
        Args:
            team (dict[str,str]): Dictionary of agent names and their descriptions.
            ledger (str): The task description containing bullet points.
            
        Returns:
            PlannerResponsePlan: Structured plan with steps and agent assignments.
        """

        # Initialize the plan structure
        planner_response_plan = PlannerResponsePlan()

        # Populate the plan description
        planner_response_plan.request = self.task_ledger.task_text

        # Populate the facts
        planner_response_plan.facts = self.task_ledger.facts or "No specific facts provided."

        # Populate the team
        planner_response_plan.team = [AgentDefinition(**d) for d in team]

        # Populate the plan
        planner_response_plan.steps = []

        
        # Split the description into lines and clean them
        lines = [line.strip() for line in self.task_ledger.plan.content.strip().split('\n') if line.strip()]
        
        init_step = True
        
        for line in lines:
            # match lines that look like bullet points
            if re.match(r'^[-•*]\s+', line):
                if not init_step:
                    planner_response_plan.steps.append(step)
                # Remove the bullet point marker
                clean_line = re.sub(r'^[-•*]\s+', '', line).strip()
            
                # Look for agent names in the line
                found_agent = None
                for agent in planner_response_plan.team:
                    # Check if agent name appears in the line (case insensitive)
                    if agent.name.lower() in clean_line.lower():
                        found_agent = agent
                        break
                
                # If no specific agent found, use MagenticPlanner
                if not found_agent:
                    found_agent = AgentDefinition("MagenticPlanner", "The Magentic Planner agent that coordinates the plan execution.")
            
                # Create the step object
                step = PlannerResponseStep()
                {
                    "agent_name": found_agent,
                    "step_description": clean_line
                }
            else:
                step.action = step.action + f" {line.strip()}"
        # Insert the last found bulleted step:
        planner_response_plan.steps.append(step)

        return planner_response_plan


class InteractiveStepMagenticManager(HumanApprovalMagenticManager):
    """
    Extended manager that allows step-by-step approval during execution.
    More granular control than the basic approval manager.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._approval_settings['step_by_step'] = False
    
    def enable_step_by_step_approval(self, enabled: bool = True):
        """Enable step-by-step approval for each agent action."""
        self._approval_settings['step_by_step'] = enabled
        print(f"🎯 Step-by-step approval {'enabled' if enabled else 'disabled'}")
    
    # Note: For step-by-step approval, we would need to hook into the agent
    # execution pipeline, which would require more extensive modifications
    # to the agent response callbacks or the orchestration flow itself.
    
    async def _intercept_agent_execution(self, agent: Agent, task: str) -> bool:
        """Intercept individual agent execution for approval (placeholder)."""
        if not self._approval_settings.get('step_by_step', False):
            return True
            
        print(f"\n🤖 Agent Execution Request:")
        print(f"   Agent: {agent.name}")
        print(f"   Task: {task[:100]}...")
        
        approval = input("❓ Allow this agent to proceed? [y/n]: ").strip().lower()
        return approval in ['y', 'yes']

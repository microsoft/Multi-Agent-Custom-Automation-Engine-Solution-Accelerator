"""
Human-in-the-loop Magentic Manager for employee onboarding orchestration.
Extends StandardMagenticManager to add approval gates before plan execution.
"""

import re
from typing import Any, List, Optional

from semantic_kernel.agents import Agent
from semantic_kernel.agents.orchestration.magentic import (
    MagenticContext, StandardMagenticManager)
from semantic_kernel.contents import ChatMessageContent
from v3.models.models import MPlan, MStep


class HumanApprovalMagenticManager(StandardMagenticManager):
    """
    Extended Magentic manager that requires human approval before executing plan steps.
    Provides interactive approval for each step in the orchestration plan.
    """
    
    # Define Pydantic fields to avoid validation errors
    approval_enabled: bool = True
    magentic_plan: Optional[MPlan] = None
    def __init__(self, *args, **kwargs):
        # Remove any custom kwargs before passing to parent
        super().__init__(*args, **kwargs)
        

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

        self.magentic_plan = self.plan_to_obj( magentic_context, self.task_ledger)
        
        # If planning failed or returned early, just return the result
        if isinstance(plan, ChatMessageContent):
            # Now show the actual plan and ask for approval
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
    
    async def prepare_final_answer(self, magentic_context: MagenticContext) -> ChatMessageContent:
        """
        Override to ensure final answer is prepared after all steps are executed.
        """
        print("\n📝 Magentic Manager - Preparing final answer...")

        return await super().prepare_final_answer(magentic_context)
    
    async def _get_plan_approval_with_details(self, task: str, participant_descriptions: dict, plan: Any) -> bool:
        while True:
            approval = input("\n❓ Approve this execution plan? [y/n/details]: ").strip().lower()
            
            if approval in ['y', 'yes']:
                print("✅ Plan approved by user")
                return True
            elif approval in ['n', 'no']:
                print("❌ Plan rejected by user")
                return False
            # elif approval in ['d', 'details']:
            #     self._show_detailed_plan_info(task, participant_descriptions, plan)
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'details' for more info")
    

    def plan_to_obj(self, magentic_context, ledger) -> MPlan:
        """
        """
        
        return_plan: MPlan = MPlan()

        # get the request text from the ledger
        if hasattr(magentic_context, 'task'):
            return_plan.user_request = magentic_context.task

        return_plan.team = list(magentic_context.participant_descriptions.keys())
        
        # Get the facts content from the ledger
        if hasattr(ledger, 'facts') and ledger.facts.content:
            return_plan.facts = ledger.facts.content

        # Get the plan / steps content from the ledger
        # Split the description into lines and clean them
        lines = [line.strip() for line in ledger.plan.content.strip().split('\n') if line.strip()]
        
        found_agent = None
        prefix = None
        
        for line in lines:
            # match lines that look like bullet points
            if re.match(r'^[-•*]\s+', line):
                # Remove the bullet point marker
                line = re.sub(r'^[-•*]\s+', '', line).strip()
            
            # Look for agent names in the line
            
            for agent_name in return_plan.team:
                # Check if agent name appears in the line (case insensitive)
                if agent_name.lower() in line.lower():
                    found_agent = agent_name
                    line = line.split(agent_name, 1)
                    line = line[1].strip() if len(line) > 1 else ""
                    line = line.replace('*', '').strip()
                    break
            
            # If line indicates a following list of actions (e.g. "Assign **EnhancedResearchAgent** 
            # to gather authoritative data on:") save and prefix to the steps
            if line.endswith(':'):
                line = line.replace(':', '').strip()
                prefix = line + " "

            # Don't create a step if action is blank 
            if line.strip() != "":
                if prefix:
                    line = prefix + line
                # Create the step object
                step = MStep(agent=found_agent, action=line)

                # add the step to the plan
                return_plan.steps.append(step) # pylint: disable=E1101

        return return_plan



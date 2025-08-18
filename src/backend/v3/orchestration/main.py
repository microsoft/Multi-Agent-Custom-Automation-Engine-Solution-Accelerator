from orchestration.manager import OnboardingOrchestrationManager
from scenarios.onboarding_cases import MagenticScenarios


class EmployeeOnboardingChat:
    """Interactive chat interface for the employee onboarding system."""
    
    def __init__(self, approval_mode="human"):
        """ Initialize the chat with the specified approval mode. """

        self.manager = OnboardingOrchestrationManager(enable_human_approval=True, step_by_step=False)
    
    async def start(self, user_input: str = "") -> None:
        """Start the interactive chat session."""
          
        # Initialize orchestration
        try:
            await self.manager.initialize()
            await self.manager.execute_task(user_input)
            await self.manager.cleanup()
        except Exception as e:
            print(f"❌ Failed to initialize system: {e}")
            return


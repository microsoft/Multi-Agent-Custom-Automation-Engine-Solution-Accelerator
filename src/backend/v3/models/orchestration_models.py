from typing import List, Optional

from semantic_kernel.kernel_pydantic import KernelBaseModel

# Add other agents as needed


# Define agents drawing on the magentic team output
class AgentDefinition:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"Agent(name={self.name!r}, description={self.description!r})"


# Define the expected structure of the LLM response
class PlannerResponseStep(KernelBaseModel):
    agent: AgentDefinition
    action: str


class PlannerResponsePlan(KernelBaseModel):
    request: str
    team: List[AgentDefinition]
    facts: str
    steps: List[PlannerResponseStep]
    summary_plan_and_steps: str
    human_clarification_request: Optional[str] = None

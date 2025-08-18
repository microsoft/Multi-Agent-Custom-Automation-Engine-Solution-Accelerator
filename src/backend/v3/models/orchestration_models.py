from enum import Enum
from typing import List, Optional, TypedDict

from semantic_kernel.kernel_pydantic import Field, KernelBaseModel


# This will be a dynamic dictionary and will depend on the loaded team definition
class AgentType(str, Enum):
    """Enumeration of agent types."""

    HUMAN = "Human_Agent"
    HR = "Hr_Agent"
    MARKETING = "Marketing_Agent"
    PROCUREMENT = "Procurement_Agent"
    PRODUCT = "Product_Agent"
    GENERIC = "Generic_Agent"
    TECH_SUPPORT = "Tech_Support_Agent"
    GROUP_CHAT_MANAGER = "Group_Chat_Manager"
    PLANNER = "Planner_Agent"

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
"""
Agent Framework version of orchestration models.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Core lightweight value object
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AgentDefinition:
    """Simple agent descriptor used in planning output."""
    name: str
    description: str

    def __repr__(self) -> str:  # Keep original style
        return f"Agent(name={self.name!r}, description={self.description!r})"


# ---------------------------------------------------------------------------
# Planner response models
# ---------------------------------------------------------------------------

class PlannerResponseStep(BaseModel):
    """One planned step referencing an agent and an action to perform."""
    agent: AgentDefinition
    action: str


class PlannerResponsePlan(BaseModel):
    """
    Full planner output including:
    - original request
    - selected team (list of AgentDefinition)
    - extracted facts
    - ordered steps
    - summarization
    - optional human clarification request
    """
    request: str
    team: List[AgentDefinition]
    facts: str
    steps: List[PlannerResponseStep]
    summary_plan_and_steps: str
    human_clarification_request: Optional[str] = None


import uuid
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MStep(BaseModel):
    """model of a step in a plan"""

    agent: str = ""
    action: str = ""


class MPlan(BaseModel):
    """model of a plan"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    team_id: str = ""
    plan_id: str = ""
    overall_status: PlanStatus = PlanStatus.CREATED
    user_request: str = ""
    team: List[str] = []
    facts: str = ""
    steps: List[MStep] = []

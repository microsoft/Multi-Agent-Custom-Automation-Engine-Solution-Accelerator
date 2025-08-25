import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

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
    _agent: str = ""
    action: str = ""

    @property
    def agent(self):
        return self._agent

    @agent.setter
    def agent(self, value):
        self._agent = value if value is not None else ""

class MPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    team_id: Optional[str] = None
    user_id: Optional[str] = None
    overall_status: PlanStatus = PlanStatus.CREATED
    progress: int = 0  # 0-100 percentage
    current_step: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(datetime.now(timezone.utc))
    updated_at: datetime = Field(datetime.now(timezone.utc))
    estimated_completion: Optional[datetime] = None
    user_request: Optional[str] = None
    team: List[str] = []
    facts: Optional[str] = None
    steps: List[MStep] = Field(list)

# class MPlan(BaseModel):
#     """model of a plan"""
#     session_id: str = ""
#     user_id: str = ""
#     team_id: str = ""
#     plan_id: str = ""
#     user_request: str = ""
#     team: List[str] = []
#     facts: str = ""
#     steps: List[MStep] = []


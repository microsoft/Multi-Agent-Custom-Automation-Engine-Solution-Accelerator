
"""Database base class for managing database operations."""

# pylint: disable=unnecessary-pass

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

import v3.models.messages as messages

from ..models.messages_kernel import (
    AgentMessageData,
    BaseDataModel,
    Plan,
    Step,
    TeamConfiguration,
    UserCurrentTeam,
)


class DatabaseBase(ABC):
    """Abstract base class for database operations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the database client and create containers if needed."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""
        pass

    # Core CRUD Operations
    @abstractmethod
    async def add_item(self, item: BaseDataModel) -> None:
        """Add an item to the database."""
        pass

    @abstractmethod
    async def update_item(self, item: BaseDataModel) -> None:
        """Update an item in the database."""
        pass

    @abstractmethod
    async def get_item_by_id(
        self, item_id: str, partition_key: str, model_class: Type[BaseDataModel]
    ) -> Optional[BaseDataModel]:
        """Retrieve an item by its ID and partition key."""
        pass

    @abstractmethod
    async def query_items(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
        model_class: Type[BaseDataModel],
    ) -> List[BaseDataModel]:
        """Query items from the database and return a list of model instances."""
        pass

    @abstractmethod
    async def delete_item(self, item_id: str, partition_key: str) -> None:
        """Delete an item from the database."""
        pass

    # Plan Operations
    @abstractmethod
    async def add_plan(self, plan: Plan) -> None:
        """Add a plan to the database."""
        pass

    @abstractmethod
    async def update_plan(self, plan: Plan) -> None:
        """Update a plan in the database."""
        pass

    @abstractmethod
    async def get_plan_by_plan_id(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by plan_id."""
        pass

    @abstractmethod
    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by plan_id."""
        pass

    @abstractmethod
    async def get_all_plans(self) -> List[Plan]:
        """Retrieve all plans for the user."""
        pass

    @abstractmethod
    async def get_all_plans_by_team_id(self, team_id: str) -> List[Plan]:
        """Retrieve all plans for a specific team."""
        pass

    @abstractmethod
    async def get_all_plans_by_team_id_status(
        self, user_id: str, team_id: str, status: str
    ) -> List[Plan]:
        """Retrieve all plans for a specific team."""
        pass

    # Step Operations
    @abstractmethod
    async def add_step(self, step: Step) -> None:
        """Add a step to the database."""
        pass

    @abstractmethod
    async def update_step(self, step: Step) -> None:
        """Update a step in the database."""
        pass

    @abstractmethod
    async def get_steps_by_plan(self, plan_id: str) -> List[Step]:
        """Retrieve all steps for a plan."""
        pass

    @abstractmethod
    async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
        """Retrieve a step by step_id and session_id."""
        pass

    # Team Operations
    @abstractmethod
    async def add_team(self, team: TeamConfiguration) -> None:
        """Add a team configuration to the database."""
        pass

    @abstractmethod
    async def update_team(self, team: TeamConfiguration) -> None:
        """Update a team configuration in the database."""
        pass

    @abstractmethod
    async def get_team(self, team_id: str) -> Optional[TeamConfiguration]:
        """Retrieve a team configuration by team_id."""
        pass

    @abstractmethod
    async def get_team_by_id(self, team_id: str) -> Optional[TeamConfiguration]:
        """Retrieve a team configuration by internal id."""
        pass

    @abstractmethod
    async def get_all_teams(self) -> List[TeamConfiguration]:
        """Retrieve all team configurations for the given user."""
        pass

    @abstractmethod
    async def delete_team(self, team_id: str) -> bool:
        """Delete a team configuration by team_id and return True if deleted."""
        pass

    # Data Management Operations
    @abstractmethod
    async def get_data_by_type(self, data_type: str) -> List[BaseDataModel]:
        """Retrieve all data of a specific type."""
        pass

    @abstractmethod
    async def get_all_items(self) -> List[Dict[str, Any]]:
        """Retrieve all items as dictionaries."""
        pass

    # Context Manager Support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Async context manager exit."""
        await self.close()

    @abstractmethod
    async def get_steps_for_plan(self, plan_id: str) -> List[Step]:
        """Convenience method aliasing get_steps_by_plan for compatibility."""
        pass

    @abstractmethod
    async def get_current_team(self, user_id: str) -> Optional[UserCurrentTeam]:
        """Retrieve the current team for a user."""
        pass

    @abstractmethod
    async def delete_current_team(self, user_id: str) -> Optional[UserCurrentTeam]:
        """Retrieve the current team for a user."""
        pass

    @abstractmethod
    async def set_current_team(self, current_team: UserCurrentTeam) -> None:
        pass

    @abstractmethod
    async def update_current_team(self, current_team: UserCurrentTeam) -> None:
        """Update the current team for a user."""
        pass

    @abstractmethod
    async def delete_plan_by_plan_id(self, plan_id: str) -> bool:
        """Retrieve the current team for a user."""
        pass

    @abstractmethod
    async def add_mplan(self, mplan: messages.MPlan) -> None:
        """Add a team configuration to the database."""
        pass

    @abstractmethod
    async def update_mplan(self, mplan: messages.MPlan) -> None:
        """Update a team configuration in the database."""
        pass

    @abstractmethod
    async def get_mplan(self, plan_id: str) -> Optional[messages.MPlan]:
        """Retrieve a mplan configuration by plan_id."""
        pass

    @abstractmethod
    async def add_agent_message(self, message: AgentMessageData) -> None:
        pass

    @abstractmethod
    async def update_agent_message(self, message: AgentMessageData) -> None:
        """Update an agent message in the database."""
        pass

    @abstractmethod
    async def get_agent_messages(self, plan_id: str) -> Optional[AgentMessageData]:
        """Retrieve an agent message by message_id."""
        pass

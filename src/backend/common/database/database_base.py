"""Database base class for managing database operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from ..models.messages_kernel import (
    BaseDataModel,
    Session,
    Plan,
    Step,
    TeamConfiguration,
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

    # Session Operations
    @abstractmethod
    async def add_session(self, session: Session) -> None:
        """Add a session to the database."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by session_id."""
        pass

    @abstractmethod
    async def get_all_sessions(self) -> List[Session]:
        """Retrieve all sessions for the user."""
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
    async def get_plan_by_session(self, session_id: str) -> Optional[Plan]:
        """Retrieve a plan by session_id."""
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
    async def get_team_by_id(self, id: str) -> Optional[TeamConfiguration]:
        """Retrieve a team configuration by internal id."""
        pass

    @abstractmethod
    async def get_all_teams_by_user(self, user_id: str) -> List[TeamConfiguration]:
        """Retrieve all team configurations for the given user."""
        pass

    @abstractmethod
    async def delete_team(self, team_id: str) -> bool:
        """Delete a team configuration by team_id and return True if deleted."""
        pass

    @abstractmethod
    async def delete_team_by_id(self, id: str) -> bool:
        """Delete a team configuration by internal id and return True if deleted."""
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

    # Convenience aliases
    async def get_steps_for_plan(self, plan_id: str) -> List[Step]:
        """Convenience method aliasing get_steps_by_plan for compatibility."""
        pass

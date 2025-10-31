"""CosmosDB implementation of the database interface."""

import datetime
import logging
from typing import Any, Dict, List, Optional, Type

import v3.models.messages as messages
from azure.cosmos.aio import CosmosClient
from azure.cosmos.aio._database import DatabaseProxy

from ..models.messages_kernel import (
    AgentMessage,
    AgentMessageData,
    BaseDataModel,
    DataType,
    Plan,
    Step,
    TeamConfiguration,
    UserCurrentTeam,
)
from .database_base import DatabaseBase


class CosmosDBClient(DatabaseBase):
    """CosmosDB implementation of the database interface."""

    MODEL_CLASS_MAPPING = {
        DataType.plan: Plan,
        DataType.step: Step,
        DataType.agent_message: AgentMessage,
        DataType.team_config: TeamConfiguration,
        DataType.user_current_team: UserCurrentTeam,
    }

    def __init__(
        self,
        endpoint: str,
        credential: any,
        database_name: str,
        container_name: str,
        session_id: str = "",
        user_id: str = "",
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.database_name = database_name
        self.container_name = container_name
        self.session_id = session_id
        self.user_id = user_id

        self.logger = logging.getLogger(__name__)
        self.client = None
        self.database = None
        self.container = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the CosmosDB client and create container if needed."""
        try:
            if not self._initialized:
                self.client = CosmosClient(
                    url=self.endpoint, credential=self.credential
                )
                self.database = self.client.get_database_client(self.database_name)

                self.container = await self._get_container(
                    self.database, self.container_name
                )
                self._initialized = True

        except Exception as e:
            self.logger.error("Failed to initialize CosmosDB: %s", str(e))
            raise

    # Helper Methods
    async def _ensure_initialized(self) -> None:
        """Ensure the database is initialized."""
        if not self._initialized:
            await self.initialize()

    async def _get_container(self, database: DatabaseProxy, container_name):
        try:
            return database.get_container_client(container_name)

        except Exception as e:
            self.logger.error("Failed to Get cosmosdb container", error=str(e))
            raise

    async def close(self) -> None:
        """Close the CosmosDB connection."""
        if self.client:
            await self.client.close()
            self.logger.info("Closed CosmosDB connection")

    # Core CRUD Operations
    async def add_item(self, item: BaseDataModel) -> None:
        """Add an item to CosmosDB."""
        await self._ensure_initialized()

        try:
            # Convert to dictionary and handle datetime serialization
            document = item.model_dump()

            for key, value in list(document.items()):
                if isinstance(value, datetime.datetime):
                    document[key] = value.isoformat()

            await self.container.create_item(body=document)
        except Exception as e:
            self.logger.error("Failed to add item to CosmosDB: %s", str(e))
            raise

    async def update_item(self, item: BaseDataModel) -> None:
        """Update an item in CosmosDB."""
        await self._ensure_initialized()

        try:
            # Convert to dictionary and handle datetime serialization
            document = item.model_dump()
            for key, value in list(document.items()):
                if isinstance(value, datetime.datetime):
                    document[key] = value.isoformat()
            await self.container.upsert_item(body=document)
        except Exception as e:
            self.logger.error("Failed to update item in CosmosDB: %s", str(e))
            raise

    async def get_item_by_id(
        self, item_id: str, partition_key: str, model_class: Type[BaseDataModel]
    ) -> Optional[BaseDataModel]:
        """Retrieve an item by its ID and partition key."""
        await self._ensure_initialized()

        try:
            item = await self.container.read_item(
                item=item_id, partition_key=partition_key
            )
            return model_class.model_validate(item)
        except Exception as e:
            self.logger.error("Failed to retrieve item from CosmosDB: %s", str(e))
            return None

    async def query_items(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
        model_class: Type[BaseDataModel],
    ) -> List[BaseDataModel]:
        """Query items from CosmosDB and return a list of model instances."""
        await self._ensure_initialized()

        try:
            items = self.container.query_items(query=query, parameters=parameters)
            result_list = []
            async for item in items:
                # item["ts"] = item["_ts"]
                try:
                    result_list.append(model_class.model_validate(item))
                except Exception as validation_error:
                    self.logger.warning(
                        "Failed to validate item: %s", str(validation_error)
                    )
                    continue
            return result_list
        except Exception as e:
            self.logger.error("Failed to query items from CosmosDB: %s", str(e))
            return []

    async def delete_item(self, item_id: str, partition_key: str) -> None:
        """Delete an item from CosmosDB."""
        await self._ensure_initialized()

        try:
            await self.container.delete_item(item=item_id, partition_key=partition_key)
        except Exception as e:
            self.logger.error("Failed to delete item from CosmosDB: %s", str(e))
            raise

    # Plan Operations
    async def add_plan(self, plan: Plan) -> None:
        """Add a plan to CosmosDB."""
        await self.add_item(plan)

    async def update_plan(self, plan: Plan) -> None:
        """Update a plan in CosmosDB."""
        await self.update_item(plan)

    async def get_plan_by_plan_id(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by plan_id."""
        query = "SELECT * FROM c WHERE c.id=@plan_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@plan_id", "value": plan_id},
            {"name": "@data_type", "value": DataType.plan},
            {"name": "@user_id", "value": self.user_id},
        ]
        results = await self.query_items(query, parameters, Plan)
        return results[0] if results else None

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by plan_id."""
        return await self.get_plan_by_plan_id(plan_id)

    async def get_all_plans(self) -> List[Plan]:
        """Retrieve all plans for the user."""
        query = "SELECT * FROM c WHERE c.user_id=@user_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@user_id", "value": self.user_id},
            {"name": "@data_type", "value": DataType.plan},
        ]
        return await self.query_items(query, parameters, Plan)

    async def get_all_plans_by_team_id(self, team_id: str) -> List[Plan]:
        """Retrieve all plans for a specific team."""
        query = "SELECT * FROM c WHERE c.team_id=@team_id AND c.data_type=@data_type and c.user_id=@user_id"
        parameters = [
            {"name": "@user_id", "value": self.user_id},
            {"name": "@team_id", "value": team_id},
            {"name": "@data_type", "value": DataType.plan},
        ]
        return await self.query_items(query, parameters, Plan)

    async def get_all_plans_by_team_id_status(
        self, user_id: str, team_id: str, status: str
    ) -> List[Plan]:
        """Retrieve all plans for a specific team."""
        query = "SELECT * FROM c WHERE c.team_id=@team_id AND c.data_type=@data_type and c.user_id=@user_id and c.overall_status=@status ORDER BY c._ts DESC"
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@team_id", "value": team_id},
            {"name": "@data_type", "value": DataType.plan},
            {"name": "@status", "value": status},
        ]
        return await self.query_items(query, parameters, Plan)

    # Step Operations
    async def add_step(self, step: Step) -> None:
        """Add a step to CosmosDB."""
        await self.add_item(step)

    async def update_step(self, step: Step) -> None:
        """Update a step in CosmosDB."""
        await self.update_item(step)

    async def get_steps_by_plan(self, plan_id: str) -> List[Step]:
        """Retrieve all steps for a plan."""
        query = "SELECT * FROM c WHERE c.plan_id=@plan_id AND c.data_type=@data_type ORDER BY c.timestamp"
        parameters = [
            {"name": "@plan_id", "value": plan_id},
            {"name": "@data_type", "value": DataType.step},
        ]
        return await self.query_items(query, parameters, Step)

    async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
        """Retrieve a step by step_id and session_id."""
        query = "SELECT * FROM c WHERE c.id=@step_id AND c.session_id=@session_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@step_id", "value": step_id},
            {"name": "@session_id", "value": session_id},
            {"name": "@data_type", "value": DataType.step},
        ]
        results = await self.query_items(query, parameters, Step)
        return results[0] if results else None

    # Removed duplicate update_team method definition

    async def get_team(self, team_id: str) -> Optional[TeamConfiguration]:
        """Retrieve a specific team configuration by team_id.

        Args:
            team_id: The team_id of the team configuration to retrieve

        Returns:
            TeamConfiguration object or None if not found
        """
        query = "SELECT * FROM c WHERE c.team_id=@team_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@team_id", "value": team_id},
            {"name": "@data_type", "value": DataType.team_config},
        ]
        teams = await self.query_items(query, parameters, TeamConfiguration)
        return teams[0] if teams else None

    async def get_team_by_id(self, team_id: str) -> Optional[TeamConfiguration]:
        """Retrieve a specific team configuration by its document id.

        Args:
            id: The document id of the team configuration to retrieve

        Returns:
            TeamConfiguration object or None if not found
        """
        query = "SELECT * FROM c WHERE c.team_id=@team_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@team_id", "value": team_id},
            {"name": "@data_type", "value": DataType.team_config},
        ]
        teams = await self.query_items(query, parameters, TeamConfiguration)
        return teams[0] if teams else None

    async def get_all_teams(self) -> List[TeamConfiguration]:
        """Retrieve all team configurations for a specific user.

        Args:
            user_id: The user_id to get team configurations for

        Returns:
            List of TeamConfiguration objects
        """
        query = "SELECT * FROM c WHERE c.data_type=@data_type ORDER BY c.created DESC"
        parameters = [
            {"name": "@data_type", "value": DataType.team_config},
        ]
        teams = await self.query_items(query, parameters, TeamConfiguration)
        return teams

    async def delete_team(self, team_id: str) -> bool:
        """Delete a team configuration by team_id.

        Args:
            team_id: The team_id of the team configuration to delete

        Returns:
            True if team was found and deleted, False otherwise
        """
        await self._ensure_initialized()

        try:
            # First find the team to get its document id and partition key
            team = await self.get_team(team_id)
            print(team)
            if team:
                await self.delete_item(item_id=team.id, partition_key=team.session_id)
            return True
        except Exception as e:
            logging.exception(f"Failed to delete team from Cosmos DB: {e}")
            return False

    # Data Management Operations
    async def get_data_by_type(self, data_type: str) -> List[BaseDataModel]:
        """Retrieve all data of a specific type."""
        query = "SELECT * FROM c WHERE c.data_type=@data_type AND c.user_id=@user_id"
        parameters = [
            {"name": "@data_type", "value": data_type},
            {"name": "@user_id", "value": self.user_id},
        ]

        # Get the appropriate model class
        model_class = self.MODEL_CLASS_MAPPING.get(data_type, BaseDataModel)
        return await self.query_items(query, parameters, model_class)

    async def get_all_items(self) -> List[Dict[str, Any]]:
        """Retrieve all items as dictionaries."""
        query = "SELECT * FROM c WHERE c.user_id=@user_id"
        parameters = [
            {"name": "@user_id", "value": self.user_id},
        ]

        await self._ensure_initialized()
        items = self.container.query_items(query=query, parameters=parameters)
        results = []
        async for item in items:
            results.append(item)
        return results

    # Collection Management (for compatibility)

    # Additional compatibility methods
    async def get_steps_for_plan(self, plan_id: str) -> List[Step]:
        """Alias for get_steps_by_plan for compatibility."""
        return await self.get_steps_by_plan(plan_id)

    async def add_team(self, team: TeamConfiguration) -> None:
        """Add a team configuration to Cosmos DB.

        Args:
            team: The TeamConfiguration to add
        """
        await self.add_item(team)

    async def update_team(self, team: TeamConfiguration) -> None:
        """Update an existing team configuration in Cosmos DB.

        Args:
            team: The TeamConfiguration to update
        """
        await self.update_item(team)

    async def get_current_team(self, user_id: str) -> Optional[UserCurrentTeam]:
        """Retrieve the current team for a user."""
        await self._ensure_initialized()
        if self.container is None:
            return None

        query = "SELECT * FROM c WHERE c.data_type=@data_type AND c.user_id=@user_id"
        parameters = [
            {"name": "@data_type", "value": DataType.user_current_team},
            {"name": "@user_id", "value": user_id},
        ]

        # Get the appropriate model class
        teams = await self.query_items(query, parameters, UserCurrentTeam)
        return teams[0] if teams else None

    async def delete_current_team(self, user_id: str) -> bool:
        """Delete the current team for a user."""
        query = "SELECT c.id, c.session_id FROM c WHERE c.user_id=@user_id AND c.data_type=@data_type"

        params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@data_type", "value": DataType.user_current_team},
        ]
        items = self.container.query_items(query=query, parameters=params)
        print("Items to delete:", items)
        if items:
            async for doc in items:
                try:
                    await self.container.delete_item(
                        doc["id"], partition_key=doc["session_id"]
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed deleting current team doc %s: %s", doc.get("id"), e
                    )

        return True

    async def set_current_team(self, current_team: UserCurrentTeam) -> None:
        """Set the current team for a user."""
        await self._ensure_initialized()
        await self.add_item(current_team)

    async def update_current_team(self, current_team: UserCurrentTeam) -> None:
        """Update the current team for a user."""
        await self._ensure_initialized()
        await self.update_item(current_team)

    async def delete_plan_by_plan_id(self, plan_id: str) -> bool:
        """Delete a plan by its ID."""
        query = "SELECT c.id, c.session_id FROM c WHERE c.id=@plan_id "

        params = [
            {"name": "@plan_id", "value": plan_id},
        ]
        items = self.container.query_items(query=query, parameters=params)
        print("Items to delete planid:", items)
        if items:
            async for doc in items:
                try:
                    await self.container.delete_item(
                        doc["id"], partition_key=doc["session_id"]
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed deleting current team doc %s: %s", doc.get("id"), e
                    )

        return True

    async def add_mplan(self, mplan: messages.MPlan) -> None:
        """Add a team configuration to the database."""
        await self.add_item(mplan)

    async def update_mplan(self, mplan: messages.MPlan) -> None:
        """Update a team configuration in the database."""
        await self.update_item(mplan)

    async def get_mplan(self, plan_id: str) -> Optional[messages.MPlan]:
        """Retrieve a mplan configuration by mplan_id."""
        query = "SELECT * FROM c WHERE c.plan_id=@plan_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@plan_id", "value": plan_id},
            {"name": "@data_type", "value": DataType.m_plan},
        ]
        results = await self.query_items(query, parameters, messages.MPlan)
        return results[0] if results else None

    async def add_agent_message(self, message: AgentMessageData) -> None:
        """Add an agent message to the database."""
        await self.add_item(message)

    async def update_agent_message(self, message: AgentMessageData) -> None:
        """Update an agent message in the database."""
        await self.update_item(message)

    async def get_agent_messages(self, plan_id: str) -> List[AgentMessageData]:
        """Retrieve an agent message by message_id."""
        query = "SELECT * FROM c WHERE c.plan_id=@plan_id AND c.data_type=@data_type ORDER BY c._ts ASC"
        parameters = [
            {"name": "@plan_id", "value": plan_id},
            {"name": "@data_type", "value": DataType.m_plan_message},
        ]

        return await self.query_items(query, parameters, AgentMessageData)

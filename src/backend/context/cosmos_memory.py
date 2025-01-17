# cosmos_memory.py

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Type

from autogen_core.components.model_context import BufferedChatCompletionContext
from autogen_core.components.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from azure.cosmos.partition_key import PartitionKey

from config import Config
from models.messages import BaseDataModel, Plan, Session, Step, AgentMessage


class CosmosBufferedChatCompletionContext(BufferedChatCompletionContext):
    """A buffered chat completion context that also saves messages and data models to Cosmos DB."""

    MODEL_CLASS_MAPPING = {
        "session": Session,
        "plan": Plan,
        "step": Step,
        "agent_message": AgentMessage,
        # Messages are handled separately
    }

    def __init__(
        self,
        session_id: str,
        user_id: str,
        buffer_size: int = 100,
        initial_messages: Optional[List[LLMMessage]] = None,
    ) -> None:
        super().__init__(buffer_size, initial_messages)
        self._cosmos_container = Config.COSMOSDB_CONTAINER
        self._database = Config.GetCosmosDatabaseClient()
        self._container = None
        self.session_id = session_id
        self.user_id = user_id
        self._initialized = asyncio.Event()
        # Auto-initialize the container
        asyncio.create_task(self.initialize())

    async def initialize(self):
        # Create container if it does not exist
        self._container = await self._database.create_container_if_not_exists(
            id=self._cosmos_container,
            partition_key=PartitionKey(path="/session_id"),
        )
        self._initialized.set()

    async def add_item(self, item: BaseDataModel) -> None:
        """Add a data model item to Cosmos DB."""
        await self._initialized.wait()
        try:
            document = item.model_dump()
            await self._container.create_item(body=document)
            logging.info(f"Item added to Cosmos DB - {document['id']}")
        except Exception as e:
            logging.exception(f"Failed to add item to Cosmos DB: {e}")
            # print(f"Failed to add item to Cosmos DB: {e}")

    async def update_item(self, item: BaseDataModel) -> None:
        """Update an existing item in Cosmos DB."""
        await self._initialized.wait()
        try:
            document = item.model_dump()
            await self._container.upsert_item(body=document)
            # logging.info(f"Item updated in Cosmos DB: {document}")
        except Exception as e:
            logging.exception(f"Failed to update item in Cosmos DB: {e}")

    async def get_item_by_id(
        self, item_id: str, partition_key: str, model_class: Type[BaseDataModel]
    ) -> Optional[BaseDataModel]:
        """Retrieve an item by its ID and partition key."""
        await self._initialized.wait()
        try:
            item = await self._container.read_item(
                item=item_id, partition_key=partition_key
            )
            return model_class.model_validate(item)
        except Exception as e:
            logging.exception(f"Failed to retrieve item from Cosmos DB: {e}")
            return None

    async def query_items(
        self,
        query: str,
        parameters: List[Dict[str, Any]],
        model_class: Type[BaseDataModel],
    ) -> List[BaseDataModel]:
        """Query items from Cosmos DB and return a list of model instances."""
        await self._initialized.wait()
        try:
            items = self._container.query_items(query=query, parameters=parameters)
            result_list = []
            async for item in items:
                item["ts"] = item["_ts"]
                result_list.append(model_class.model_validate(item))
            return result_list
        except Exception as e:
            logging.exception(f"Failed to query items from Cosmos DB: {e}")
            return []

    # Methods to add and retrieve Sessions, Plans, and Steps

    async def add_session(self, session: Session) -> None:
        """Add a session to Cosmos DB."""
        await self.add_item(session)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by session_id."""
        query = "SELECT * FROM c WHERE c.id=@id AND c.data_type=@data_type"
        parameters = [
            {"name": "@id", "value": session_id},
            {"name": "@data_type", "value": "session"},
        ]
        sessions = await self.query_items(query, parameters, Session)
        return sessions[0] if sessions else None

    async def get_all_sessions(self) -> List[Session]:
        """Retrieve all sessions."""
        query = "SELECT * FROM c WHERE c.data_type=@data_type"
        parameters = [
            {"name": "@data_type", "value": "session"},
        ]
        sessions = await self.query_items(query, parameters, Session)
        return sessions

    async def add_plan(self, plan: Plan) -> None:
        """Add a plan to Cosmos DB."""
        await self.add_item(plan)

    async def update_plan(self, plan: Plan) -> None:
        """Update an existing plan in Cosmos DB."""
        await self.update_item(plan)

    async def get_plan_by_session(self, session_id: str) -> Optional[Plan]:
        """Retrieve a plan associated with a session."""
        query = "SELECT * FROM c WHERE c.session_id=@session_id AND c.user_id=@user_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@session_id", "value": session_id},
            {"name": "@data_type", "value": "plan"},
            {"name": "@user_id", "value": self.user_id},
        ]
        plans = await self.query_items(query, parameters, Plan)
        return plans[0] if plans else None

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by its ID."""
        return await self.get_item_by_id(
            plan_id, partition_key=plan_id, model_class=Plan
        )

    async def get_all_plans(self) -> List[Plan]:
        """Retrieve all plans."""
        query = "SELECT * FROM c WHERE c.user_id=@user_id AND c.data_type=@data_type ORDER BY c._ts DESC OFFSET 0 LIMIT 5"
        parameters = [
            {"name": "@data_type", "value": "plan"},
            {"name": "@user_id", "value": self.user_id},
        ]
        plans = await self.query_items(query, parameters, Plan)
        return plans

    async def add_step(self, step: Step) -> None:
        """Add a step to Cosmos DB."""
        await self.add_item(step)

    async def update_step(self, step: Step) -> None:
        """Update an existing step in Cosmos DB."""
        await self.update_item(step)

    async def get_steps_by_plan(self, plan_id: str) -> List[Step]:
        """Retrieve all steps associated with a plan."""
        query = "SELECT * FROM c WHERE c.plan_id=@plan_id AND c.user_id=@user_id AND c.data_type=@data_type"
        parameters = [
            {"name": "@plan_id", "value": plan_id},
            {"name": "@data_type", "value": "step"},
            {"name": "@user_id", "value": self.user_id},
        ]
        steps = await self.query_items(query, parameters, Step)
        return steps

    async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
        """Retrieve a step by its ID."""
        return await self.get_item_by_id(
            step_id, partition_key=session_id, model_class=Step
        )

    # Methods for messages

    async def add_message(self, message: LLMMessage) -> None:
        """Add a message to the memory and save to Cosmos DB."""
        await self._initialized.wait()
        if self._container is None:
            # logging.error("Cosmos DB container is not initialized.")
            return

        try:
            await super().add_message(message)
            message_dict = {
                "id": str(uuid.uuid4()),
                "session_id": self.session_id,
                "data_type": "message",
                "content": message.dict(),
                "source": getattr(message, "source", ""),
            }
            await self._container.create_item(body=message_dict)
            # logging.info(f"Message added to Cosmos DB: {message_dict}")
        except Exception as e:
            logging.exception(f"Failed to add message to Cosmos DB: {e}")

    async def get_messages(self) -> List[LLMMessage]:
        """Get recent messages for the session."""
        await self._initialized.wait()
        if self._container is None:
            # logging.error("Cosmos DB container is not initialized.")
            return []

        try:
            query = """
                SELECT * FROM c
                WHERE c.session_id=@session_id AND c.data_type=@data_type
                ORDER BY c._ts ASC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@session_id", "value": self.session_id},
                {"name": "@data_type", "value": "message"},
                {"name": "@limit", "value": self._buffer_size},
            ]
            items = self._container.query_items(
                query=query,
                parameters=parameters,
            )
            messages = []
            async for item in items:
                content = item.get("content", {})
                message_type = content.get("type")
                if message_type == "SystemMessage":
                    message = SystemMessage.model_validate(content)
                elif message_type == "UserMessage":
                    message = UserMessage.model_validate(content)
                elif message_type == "AssistantMessage":
                    message = AssistantMessage.model_validate(content)
                elif message_type == "FunctionExecutionResultMessage":
                    message = FunctionExecutionResultMessage.model_validate(content)
                else:
                    continue
                messages.append(message)
            return messages
        except Exception as e:
            logging.exception(f"Failed to load messages from Cosmos DB: {e}")
            return []

    # Generic method to get data by type

    async def get_data_by_type(self, data_type: str) -> List[BaseDataModel]:
        """Query the Cosmos DB for documents with the matching data_type, session_id and user_id."""
        await self._initialized.wait()
        if self._container is None:
            # logging.error("Cosmos DB container is not initialized.")
            return []

        model_class = self.MODEL_CLASS_MAPPING.get(data_type, BaseDataModel)
        try:
            query = "SELECT * FROM c WHERE c.session_id=@session_id AND c.user_id=@user_id AND c.data_type=@data_type  ORDER BY c._ts ASC"
            parameters = [
                {"name": "@session_id", "value": self.session_id},
                {"name": "@data_type", "value": data_type},
                {"name": "@user_id", "value": self.user_id},
            ]
            return await self.query_items(query, parameters, model_class)
        except Exception as e:
            logging.exception(f"Failed to query data by type from Cosmos DB: {e}")
            return []

    # Additional utility methods

    async def delete_item(self, item_id: str, partition_key: str) -> None:
        """Delete an item from Cosmos DB."""
        await self._initialized.wait()
        try:
            await self._container.delete_item(item=item_id, partition_key=partition_key)
            # logging.info(f"Item {item_id} deleted from Cosmos DB")
        except Exception as e:
            logging.exception(f"Failed to delete item from Cosmos DB: {e}")

    async def delete_items_by_query(
        self, query: str, parameters: List[Dict[str, Any]]
    ) -> None:
        """Delete items matching the query."""
        await self._initialized.wait()
        try:
            items = self._container.query_items(query=query, parameters=parameters)
            async for item in items:
                item_id = item["id"]
                partition_key = item.get("session_id", None)
                await self._container.delete_item(
                    item=item_id, partition_key=partition_key
                )
                # logging.info(f"Item {item_id} deleted from Cosmos DB")
        except Exception as e:
            logging.exception(f"Failed to delete items from Cosmos DB: {e}")

    async def delete_all_messages(self, data_type) -> None:
        """Delete all messages from Cosmos DB."""
        query = "SELECT c.id, c.session_id FROM c WHERE c.data_type=@data_type AND c.user_id=@user_id"
        parameters = [
            {"name": "@data_type", "value": data_type},
            {"name": "@user_id", "value": self.user_id},
        ]
        await self.delete_items_by_query(query, parameters)

    async def get_all_messages(self) -> List[Dict[str, Any]]:
        """Retrieve all messages from Cosmos DB."""
        await self._initialized.wait()
        if self._container is None:
            # logging.error("Cosmos DB container is not initialized.")
            return []

        try:
            messages_list = []
            query = "SELECT * FROM c OFFSET 0 LIMIT @limit"
            parameters = [{"name": "@limit", "value": 100}]
            items = self._container.query_items(query=query, parameters=parameters)
            async for item in items:
                messages_list.append(item)
            return messages_list
        except Exception as e:
            logging.exception(f"Failed to get messages from Cosmos DB: {e}")
            return []

    async def close(self) -> None:
        """Close the Cosmos DB client."""
        # await self.aad_credentials.close()
        # await self._cosmos_client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def __del__(self):
        asyncio.create_task(self.close())

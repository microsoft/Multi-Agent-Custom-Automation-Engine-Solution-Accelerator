"""Database factory for creating database instances."""

import logging
from typing import Optional

from common.config.app_config import config

from .cosmosdb import CosmosDBClient
from .database_base import DatabaseBase


class DatabaseFactory:
    """Factory class for creating database instances.

    Caches the expensive CosmosDB connection infrastructure (client, database,
    container) while creating per-request CosmosDBClient instances scoped to
    the calling user_id.  This ensures ownership filters in queries always
    reference the correct user without race conditions across concurrent
    asyncio tasks.
    """

    _shared_instance: Optional[CosmosDBClient] = None
    _logger = logging.getLogger(__name__)

    @staticmethod
    async def get_database(
        user_id: str = "",
        force_new: bool = False,
    ) -> DatabaseBase:
        """
        Get a database instance scoped to the given user_id.

        The underlying CosmosDB connection (client, database, container) is
        shared across all requests.  Each call returns a lightweight wrapper
        bound to *user_id* so that query-level ownership predicates are
        always correct — even under concurrent async execution.

        Args:
            user_id: User ID for data isolation (required for ownership checks)
            force_new: Force re-creation of the shared connection

        Returns:
            DatabaseBase: Database instance scoped to user_id
        """

        # Ensure the shared connection infrastructure is initialized
        if force_new or DatabaseFactory._shared_instance is None:
            shared = CosmosDBClient(
                endpoint=config.COSMOSDB_ENDPOINT,
                credential=config.get_azure_credentials(),
                database_name=config.COSMOSDB_DATABASE,
                container_name=config.COSMOSDB_CONTAINER,
                session_id="",
                user_id=user_id,
            )
            await shared.initialize()
            DatabaseFactory._shared_instance = shared

        # Create a per-request instance that shares the connection but is
        # bound to the caller's user_id
        instance = CosmosDBClient(
            endpoint=config.COSMOSDB_ENDPOINT,
            credential=config.get_azure_credentials(),
            database_name=config.COSMOSDB_DATABASE,
            container_name=config.COSMOSDB_CONTAINER,
            session_id="",
            user_id=user_id,
        )
        # Share the already-initialized connection objects
        instance.client = DatabaseFactory._shared_instance.client
        instance.database = DatabaseFactory._shared_instance.database
        instance.container = DatabaseFactory._shared_instance.container
        instance._initialized = True

        return instance

    @staticmethod
    async def close_all():
        """Close all database connections."""
        if DatabaseFactory._shared_instance:
            await DatabaseFactory._shared_instance.close()
            DatabaseFactory._shared_instance = None

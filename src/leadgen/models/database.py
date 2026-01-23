"""Database connection and session management with asyncpg.

This module provides async database connection management using SQLAlchemy
with asyncpg for PostgreSQL. It includes engine creation, session factories,
and dependency injection utilities for FastAPI.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from . import Base


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages async database connections and sessions.

    This class provides a singleton-like pattern for database engine
    management with proper connection pooling for asyncpg.

    Attributes:
        _engine: The async SQLAlchemy engine instance.
        _session_factory: Factory for creating async sessions.
    """

    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @classmethod
    def get_database_url(cls) -> str:
        """Get the database URL from environment variables.

        Returns:
            PostgreSQL connection URL with asyncpg driver.

        Raises:
            ValueError: If DATABASE_URL is not set.
        """
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Expected format: postgresql://user:password@host:port/dbname"
            )

        # Convert postgresql:// to postgresql+asyncpg:// if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif not database_url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql://' or 'postgresql+asyncpg://'"
            )

        return database_url

    @classmethod
    async def get_engine(cls) -> AsyncEngine:
        """Get or create the async database engine.

        Creates a new engine if one doesn't exist, using asyncpg
        with connection pooling optimized for async operations.

        Returns:
            AsyncEngine: The SQLAlchemy async engine.
        """
        if cls._engine is None:
            database_url = cls.get_database_url()

            cls._engine = create_async_engine(
                database_url,
                # Connection pool settings optimized for asyncpg
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=os.getenv("DATABASE_ECHO", "").lower() == "true",
            )

            logger.info("Database engine created successfully")

        return cls._engine

    @classmethod
    async def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """Get or create the async session factory.

        Returns:
            async_sessionmaker: Factory for creating AsyncSession instances.
        """
        if cls._session_factory is None:
            engine = await cls.get_engine()
            cls._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

        return cls._session_factory

    @classmethod
    async def create_tables(cls) -> None:
        """Create all database tables defined in the models.

        This should be called once at application startup to ensure
        all tables exist.
        """
        engine = await cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    @classmethod
    async def drop_tables(cls) -> None:
        """Drop all database tables.

        WARNING: This will delete all data. Use only for testing.
        """
        engine = await cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("Database tables dropped")

    @classmethod
    async def close(cls) -> None:
        """Close the database engine and release all connections.

        Should be called when shutting down the application.
        """
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Database engine closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session as a context manager.

    This is the primary way to get a database session for executing
    queries. The session is automatically committed on success and
    rolled back on exception.

    Yields:
        AsyncSession: An async database session.

    Example:
        async with get_db_session() as session:
            lead = await session.get(Lead, lead_id)
            lead.status = LeadStatus.RESEARCHING
            await session.commit()
    """
    session_factory = await DatabaseManager.get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Use this with FastAPI's Depends() for automatic session management
    in route handlers.

    Yields:
        AsyncSession: An async database session.

    Example:
        @app.get("/leads/{lead_id}")
        async def get_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
            return await db.get(Lead, lead_id)
    """
    async with get_db_session() as session:
        yield session


async def init_database() -> None:
    """Initialize the database connection and create tables.

    Call this once at application startup.
    """
    await DatabaseManager.create_tables()


async def close_database() -> None:
    """Close database connections.

    Call this when shutting down the application.
    """
    await DatabaseManager.close()


def create_test_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """Create an async engine for testing purposes.

    Uses NullPool to prevent connection issues in test fixtures.

    Args:
        database_url: Optional database URL. If not provided, uses
            DATABASE_URL environment variable.

    Returns:
        AsyncEngine: A test-configured async engine.
    """
    if database_url is None:
        database_url = DatabaseManager.get_database_url()

    return create_async_engine(
        database_url,
        poolclass=NullPool,
        echo=False,
    )

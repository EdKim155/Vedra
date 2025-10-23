"""
Database session configuration and utilities.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from cars_bot.database.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manager for database connections and sessions.

    Handles async engine creation and session lifecycle.
    """

    def __init__(self, database_url: str, echo: bool = False) -> None:
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL (asyncpg format)
            echo: Whether to log all SQL queries
        """
        self.database_url = database_url
        self.echo = echo
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def create_engine(self) -> AsyncEngine:
        """
        Create async SQLAlchemy engine.

        Returns:
            Configured async engine
        """
        logger.info("Creating database engine")

        self._engine = create_async_engine(
            self.database_url,
            echo=self.echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=20,  # Connection pool size
            max_overflow=10,  # Maximum overflow connections
            pool_recycle=3600,  # Recycle connections after 1 hour
            # Use NullPool for development to avoid connection issues
            poolclass=NullPool if "sqlite" in self.database_url else None,
        )

        return self._engine

    def create_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """
        Create async session maker.

        Returns:
            Configured session maker
        """
        if self._engine is None:
            self.create_engine()

        logger.info("Creating session maker")

        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flushing for better control
            autocommit=False,  # Explicit transactions
        )

        return self._sessionmaker

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.

        Yields:
            AsyncSession instance

        Example:
            async with db_manager.session() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
        """
        if self._sessionmaker is None:
            self.create_sessionmaker()

        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        """
        Create all database tables.

        WARNING: Only for development! Use Alembic migrations in production.
        """
        if self._engine is None:
            self.create_engine()

        logger.info("Creating database tables")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: This will delete all data! Use with caution.
        """
        if self._engine is None:
            self.create_engine()

        logger.warning("Dropping all database tables")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.info("Database tables dropped")

    async def dispose(self) -> None:
        """Dispose of the engine and close all connections."""
        if self._engine:
            logger.info("Disposing database engine")
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None


# Global database manager instance (will be initialized in app startup)
db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database manager is not initialized
    """
    if db_manager is None:
        raise RuntimeError(
            "Database manager not initialized. "
            "Call init_database() before accessing database."
        )
    return db_manager


def init_database(database_url: str, echo: bool = False) -> DatabaseManager:
    """
    Initialize global database manager.

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to log SQL queries

    Returns:
        Initialized DatabaseManager
    """
    global db_manager

    logger.info("Initializing database")
    db_manager = DatabaseManager(database_url=database_url, echo=echo)
    db_manager.create_engine()
    db_manager.create_sessionmaker()

    return db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.

    Yields:
        AsyncSession instance

    Example (FastAPI):
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    manager = get_db_manager()
    async with manager.session() as session:
        yield session

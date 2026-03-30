"""PostgreSQL database connection and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from loguru import logger
from typing import AsyncGenerator

from butterfly.config import settings
from butterfly.models.event import Base


# Create async engine
engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    poolclass=NullPool,  # Disable connection pooling for simplicity
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions. Raises 503 if Postgres is unavailable."""
    try:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database unavailable — start Postgres or use /api/v1/demo endpoints",
        )


async def create_all_tables() -> None:
    """Create all database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
async def drop_all_tables() -> None:
    """Drop all database tables (for testing)."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


async def close_db() -> None:
    """Close database connection."""
    await engine.dispose()
    logger.info("Database connection closed")

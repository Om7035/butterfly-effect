"""
PostgreSQL database layer.
Falls back to SQLite (via aiosqlite) when PostgreSQL is not running.
The app works fully in both modes — SQLite is used for development/demo.
"""
from __future__ import annotations

import os
from loguru import logger

from butterfly.config import settings

# ── Detect which backend to use ───────────────────────────────────────────────

_USE_SQLITE = False
_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "butterfly.db")

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import NullPool
    from sqlalchemy import text
    from butterfly.models.event import Base

    engine = create_async_engine(
        settings.postgres_url,
        echo=False,
        poolclass=NullPool,
        future=True,
        connect_args={"timeout": 3},
    )
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, future=True
    )
    logger.debug("Postgres engine created (will test on first use)")

except Exception as e:
    logger.warning(f"Postgres engine creation failed: {e} — will use SQLite fallback")
    engine = None  # type: ignore
    AsyncSessionLocal = None  # type: ignore


async def get_db():
    """FastAPI dependency for database sessions."""
    if AsyncSessionLocal is None or _USE_SQLITE:
        yield None
        return
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all database tables. Falls back to SQLite if Postgres unavailable."""
    global _USE_SQLITE

    # Try Postgres first
    if engine is not None:
        try:
            from butterfly.models.event import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("PostgreSQL: tables created")
            return
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable ({e}) — switching to SQLite")
            _USE_SQLITE = True

    # SQLite fallback
    await _sqlite_init()


async def _sqlite_init() -> None:
    """Initialize SQLite database as Postgres fallback."""
    import aiosqlite
    import os

    db_path = _SQLITE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT DEFAULT 'manual',
                source_url TEXT,
                occurred_at TEXT,
                raw_text TEXT,
                entities TEXT DEFAULT '[]',
                processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()
    logger.info(f"SQLite fallback initialised at {db_path}")


async def close_db() -> None:
    if engine is not None:
        try:
            await engine.dispose()
        except Exception:
            pass
    logger.info("DB connection closed")

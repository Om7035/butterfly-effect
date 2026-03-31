"""Redis connection and cache utilities.

Falls back to fakeredis (in-memory) automatically when Redis server is unavailable.
This means caching works out of the box with zero server setup.
"""

from typing import Any

import redis.asyncio as redis
from loguru import logger

from butterfly.config import settings

redis_client: redis.Redis | None = None
_using_fakeredis: bool = False


async def init_redis() -> redis.Redis | None:
    """Initialize Redis connection. Falls back to fakeredis if server unavailable."""
    global redis_client, _using_fakeredis

    # Try real Redis first
    try:
        client = await redis.from_url(settings.redis_url, decode_responses=True,
                                       socket_connect_timeout=2, socket_timeout=2)
        await client.ping()
        redis_client = client
        _using_fakeredis = False
        logger.info("Redis connection established (real server)")
        return redis_client
    except Exception as e:
        logger.warning(f"Real Redis unavailable ({e}) — using fakeredis (in-memory)")

    # Fall back to fakeredis
    try:
        import fakeredis.aioredis as fakeredis_async
        redis_client = fakeredis_async.FakeRedis(decode_responses=True)
        _using_fakeredis = True
        logger.info("fakeredis initialized (in-memory cache, resets on restart)")
        return redis_client
    except ImportError:
        logger.warning("fakeredis not installed — caching disabled. Run: pip install fakeredis")
        redis_client = None
        return None


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client and not _using_fakeredis:
        await redis_client.close()
        logger.info("Redis connection closed")


async def get_redis() -> redis.Redis | None:
    """Get Redis client, initializing if needed."""
    global redis_client
    if redis_client is None:
        await init_redis()
    return redis_client


async def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """Set a value in Redis cache."""
    try:
        client = await get_redis()
        if client is None:
            return
        await client.setex(key, ttl, str(value))
    except Exception as e:
        logger.warning(f"Failed to set cache for key {key}: {e}")


async def get_cache(key: str) -> str | None:
    """Get a value from Redis cache."""
    try:
        client = await get_redis()
        if client is None:
            return None
        return await client.get(key)
    except Exception as e:
        logger.warning(f"Failed to get cache for key {key}: {e}")
        return None


async def delete_cache(key: str) -> None:
    """Delete a value from Redis cache."""
    try:
        client = await get_redis()
        if client is None:
            return
        await client.delete(key)
    except Exception as e:
        logger.warning(f"Failed to delete cache for key {key}: {e}")

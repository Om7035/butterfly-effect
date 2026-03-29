"""Redis connection and cache utilities."""

import redis.asyncio as redis
from loguru import logger
from typing import Optional, Any

from butterfly.config import settings

redis_client: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection."""
    global redis_client
    try:
        redis_client = await redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = await init_redis()
    return redis_client


async def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """Set a value in Redis cache."""
    try:
        client = await get_redis()
        await client.setex(key, ttl, str(value))
    except Exception as e:
        logger.warning(f"Failed to set cache for key {key}: {e}")


async def get_cache(key: str) -> Optional[str]:
    """Get a value from Redis cache."""
    try:
        client = await get_redis()
        return await client.get(key)
    except Exception as e:
        logger.warning(f"Failed to get cache for key {key}: {e}")
        return None


async def delete_cache(key: str) -> None:
    """Delete a value from Redis cache."""
    try:
        client = await get_redis()
        await client.delete(key)
    except Exception as e:
        logger.warning(f"Failed to delete cache for key {key}: {e}")

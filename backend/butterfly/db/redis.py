"""
Redis cache layer.
Falls back to fakeredis (in-memory) when Redis server is not running.
All cache operations work identically in both modes.
"""
from __future__ import annotations

from typing import Any, Optional

from loguru import logger

_client = None
_using_fake = False


async def init_redis():
    """Connect to Redis. Falls back to fakeredis automatically."""
    global _client, _using_fake

    from butterfly.config import settings

    # Try real Redis first
    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        await client.ping()
        _client = client
        _using_fake = False
        logger.info("Redis: connected to real server")
        return _client
    except Exception as e:
        logger.warning(f"Redis server unavailable ({e}) — using fakeredis in-memory fallback")

    # fakeredis fallback
    try:
        import fakeredis.aioredis as fakeredis
        _client = fakeredis.FakeRedis(decode_responses=True)
        _using_fake = True
        logger.info("Redis: using fakeredis (in-memory, data lost on restart)")
        return _client
    except Exception as e2:
        logger.error(f"fakeredis also failed: {e2}")
        _client = None
        return None


async def close_redis() -> None:
    global _client
    if _client and not _using_fake:
        try:
            await _client.aclose()
        except Exception:
            pass
    _client = None
    logger.info("Redis connection closed")


async def _get_client():
    global _client
    if _client is None:
        await init_redis()
    return _client


async def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    try:
        client = await _get_client()
        if client:
            await client.setex(key, ttl, str(value))
    except Exception as e:
        logger.warning(f"Cache set failed for '{key}': {e}")


async def get_cache(key: str) -> Optional[str]:
    try:
        client = await _get_client()
        if client:
            return await client.get(key)
    except Exception as e:
        logger.warning(f"Cache get failed for '{key}': {e}")
    return None


async def delete_cache(key: str) -> None:
    try:
        client = await _get_client()
        if client:
            await client.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete failed for '{key}': {e}")


# Legacy aliases used by older code
redis_client = None  # populated after init_redis() is called

async def get_redis():
    return await _get_client()

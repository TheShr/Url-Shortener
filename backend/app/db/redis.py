from typing import Optional
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            max_connections=settings.redis_pool_size,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        logger.info("Redis connection pool initialized")
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection pool closed")


# ── Cache helpers ─────────────────────────────────────────────────────────────

async def cache_get(key: str) -> Optional[str]:
    try:
        redis = await get_redis()
        return await redis.get(key)
    except Exception as e:
        logger.warning("cache_get_failed", key=key, error=str(e))
        return None  # Graceful degradation — always fall through to DB


async def cache_set(key: str, value: str, ttl: int = settings.cache_ttl_seconds) -> None:
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, value)
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))


async def cache_delete(key: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(key)
    except Exception as e:
        logger.warning("cache_delete_failed", key=key, error=str(e))


async def cache_increment(key: str, ttl: int) -> int:
    """Atomic increment — used for rate limiting."""
    try:
        redis = await get_redis()
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        return results[0]
    except Exception as e:
        logger.warning("cache_increment_failed", key=key, error=str(e))
        return 0


async def enqueue_click_event(event: dict) -> None:
    """Push click analytics into a Redis list for batch processing."""
    try:
        import json
        redis = await get_redis()
        await redis.lpush("click_events", json.dumps(event))
    except Exception as e:
        logger.warning("enqueue_click_event_failed", error=str(e))

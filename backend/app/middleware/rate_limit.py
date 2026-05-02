"""
Sliding window rate limiter using Redis sorted sets.

Each key is a sorted set: { member: request_timestamp, score: request_timestamp }
On each request:
  1. Remove entries older than window_seconds
  2. Count remaining entries
  3. If count < limit: add current timestamp, return OK
  4. Else: return 429

This is more accurate than fixed window (no burst at window boundary).
"""

import time
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.redis import get_redis

settings = get_settings()
logger = get_logger(__name__)


def _parse_rate(rate_str: str) -> tuple[int, int]:
    """Parse '10/minute' → (10, 60)."""
    parts = rate_str.split("/")
    limit = int(parts[0])
    unit = parts[1].lower()
    windows = {"second": 1, "minute": 60, "hour": 3600}
    return limit, windows.get(unit, 60)


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting proxy headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


async def check_rate_limit(
    request: Request,
    rate_str: str,
    namespace: str = "rl",
) -> None:
    """
    Sliding window rate limit check.
    Raises HTTP 429 if the limit is exceeded.
    """
    limit, window = _parse_rate(rate_str)
    client_ip = get_client_ip(request)
    key = f"{namespace}:{client_ip}"
    now = time.time()
    window_start = now - window

    try:
        redis = await get_redis()
        pipe = redis.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count requests in window
        pipe.zcard(key)
        # Add current request (score = timestamp, member = unique value)
        pipe.zadd(key, {str(now): now})
        # Reset TTL
        pipe.expire(key, window + 1)
        results = await pipe.execute()
        count = results[1]

        if count >= limit:
            retry_after = int(window - (now - float(
                (await redis.zrange(key, 0, 0, withscores=True) or [(None, now - window)])[0][1]
            )))
            logger.warning("rate_limit_exceeded", ip=client_ip, count=count, limit=limit)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(max(retry_after, 1))},
            )
    except HTTPException:
        raise
    except Exception as e:
        # Redis unavailable — fail open (don't block requests)
        logger.error("rate_limiter_error", error=str(e))

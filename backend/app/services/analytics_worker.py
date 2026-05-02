"""
Background analytics worker.

Strategy: Click events are first queued in a Redis list (lpush/rpop).
This worker runs as an asyncio task on startup, draining the queue in
configurable batches. This decouples the hot redirect path (no DB write)
from analytics persistence, keeping p99 redirect latency low.

Batch insert pattern: collect N events → single INSERT ... VALUES (...) × N
Typically 50–100 events/batch at 2-second flush interval.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.core.logging import get_logger
from app.db.redis import get_redis
from app.db.session import get_db_context
from app.models.url import Click, URL
from sqlalchemy import select, update

logger = get_logger(__name__)

BATCH_SIZE = 100
FLUSH_INTERVAL_SECONDS = 2


async def _get_url_id_for_code(session, short_code: str) -> Optional[str]:
    result = await session.execute(
        select(URL.id).where(URL.short_code == short_code)
    )
    row = result.scalar_one_or_none()
    return str(row) if row else None


async def flush_click_events() -> None:
    """Drain up to BATCH_SIZE events from Redis and persist to PostgreSQL."""
    redis = await get_redis()
    pipeline = redis.pipeline()

    # Atomically pop up to BATCH_SIZE items from the list
    for _ in range(BATCH_SIZE):
        pipeline.rpop("click_events")
    raw_events = await pipeline.execute()

    events = [json.loads(e) for e in raw_events if e is not None]
    if not events:
        return

    logger.info("flushing_click_events", count=len(events))

    async with get_db_context() as session:
        # Resolve short_code → url_id (with a cache to avoid N+1)
        code_to_id: dict[str, Optional[str]] = {}
        click_records = []

        for event in events:
            code = event.get("short_code")
            if code not in code_to_id:
                code_to_id[code] = event.get("url_id") or await _get_url_id_for_code(session, code)

            url_id = code_to_id.get(code)
            if not url_id:
                continue

            click_records.append(
                Click(
                    url_id=url_id,
                    clicked_at=datetime.fromisoformat(event["clicked_at"]),
                    ip_address=event.get("ip_address"),
                    user_agent=event.get("user_agent"),
                    referer=event.get("referer"),
                )
            )

        if click_records:
            session.add_all(click_records)
            await session.flush()

            # Update denormalised click_count per URL
            from collections import Counter
            count_by_url = Counter(str(c.url_id) for c in click_records)
            for url_id, delta in count_by_url.items():
                await session.execute(
                    update(URL)
                    .where(URL.id == url_id)
                    .values(click_count=URL.click_count + delta)
                )

    logger.info("click_events_flushed", count=len(click_records))


async def run_analytics_worker() -> None:
    """Long-running task — runs for the lifetime of the process."""
    logger.info("analytics_worker_started")
    while True:
        try:
            await flush_click_events()
        except Exception as e:
            logger.error("analytics_worker_error", error=str(e))
        await asyncio.sleep(FLUSH_INTERVAL_SECONDS)


async def run_expiry_cleanup() -> None:
    """Soft-delete expired URLs. Runs every 10 minutes."""
    from datetime import datetime, timezone
    from sqlalchemy import update as sa_update
    logger.info("expiry_cleanup_worker_started")
    while True:
        try:
            async with get_db_context() as session:
                result = await session.execute(
                    sa_update(URL)
                    .where(URL.expires_at < datetime.now(timezone.utc), URL.is_active == True)
                    .values(is_active=False)
                    .returning(URL.short_code)
                )
                expired = result.fetchall()
                if expired:
                    logger.info("urls_expired", count=len(expired))
        except Exception as e:
            logger.error("expiry_cleanup_error", error=str(e))
        await asyncio.sleep(600)  # 10 minutes

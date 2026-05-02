from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import json

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.redis import cache_get, cache_set
from app.models.url import URL, Click
from app.schemas.url import ShortenRequest, ShortenResponse, AnalyticsDetail, AnalyticsSummary, ClickDataPoint
from app.utils.encoding import generate_short_code

settings = get_settings()
logger = get_logger(__name__)

# Cache key namespaces
_URL_CACHE_PREFIX = "url:"
_NOT_FOUND_SENTINEL = "__404__"   # Cache negative lookups to prevent DB hammering
_NOT_FOUND_TTL = 60               # Short TTL for negative cache


class URLService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Shorten ────────────────────────────────────────────────────────────────

    async def shorten(self, request: ShortenRequest) -> ShortenResponse:
        original_url = str(request.url)

        # Check custom alias availability
        if request.custom_alias:
            existing = await self._get_url_by_code(request.custom_alias)
            if existing:
                raise ValueError(f"Alias '{request.custom_alias}' is already taken")
            short_code = request.custom_alias
        else:
            short_code = await self._generate_unique_code()

        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=request.expiry_days)
            if request.expiry_days
            else datetime.now(timezone.utc) + timedelta(days=settings.default_expiry_days)
        )

        url_obj = URL(
            short_code=short_code,
            original_url=original_url,
            custom_alias=request.custom_alias,
            expires_at=expires_at,
        )
        self.db.add(url_obj)
        await self.db.flush()   # Flush to get DB-assigned values without full commit

        logger.info("url_shortened", short_code=short_code, original=original_url)

        # Warm cache immediately after creation
        await cache_set(f"{_URL_CACHE_PREFIX}{short_code}", original_url)

        return ShortenResponse(
            short_code=short_code,
            short_url=f"{settings.base_domain}/{short_code}",
            original_url=original_url,
            expires_at=expires_at,
            created_at=url_obj.created_at,
        )

    # ── Redirect ───────────────────────────────────────────────────────────────

    async def resolve(
        self,
        short_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> Optional[str]:
        cache_key = f"{_URL_CACHE_PREFIX}{short_code}"

        # 1. Cache hit (hot path — still requires the URL record for analytics)
        cached = await cache_get(cache_key)
        if cached:
            if cached == _NOT_FOUND_SENTINEL:
                return None
            url_obj = await self._get_url_by_code(short_code)
            if url_obj and url_obj.is_active and not url_obj.is_expired:
                await self._record_click(url_obj, ip_address, user_agent, referer)
            logger.debug("cache_hit", short_code=short_code)
            return cached

        # 2. DB lookup (cold path)
        url_obj = await self._get_url_by_code(short_code)

        if not url_obj or not url_obj.is_active or url_obj.is_expired:
            # Cache the miss to prevent repeated DB hits
            await cache_set(cache_key, _NOT_FOUND_SENTINEL, ttl=_NOT_FOUND_TTL)
            logger.info("url_not_found", short_code=short_code)
            return None

        # Warm cache for subsequent requests
        await cache_set(cache_key, url_obj.original_url)

        await self._record_click(url_obj, ip_address, user_agent, referer)
        logger.info("url_resolved", short_code=short_code, original=url_obj.original_url)
        return url_obj.original_url

    async def _record_click(
        self,
        url_obj: URL,
        ip_address: Optional[str],
        user_agent: Optional[str],
        referer: Optional[str],
    ) -> None:
        click = Click(
            url_id=url_obj.id,
            clicked_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
        )
        self.db.add(click)
        await self.db.flush()
        await self.db.execute(
            update(URL)
            .where(URL.id == url_obj.id)
            .values(click_count=URL.click_count + 1)
        )

    # ── Analytics ──────────────────────────────────────────────────────────────

    async def get_analytics(self, short_code: str) -> Optional[AnalyticsDetail]:
        url_obj = await self._get_url_by_code(short_code)
        if not url_obj:
            return None

        # Clicks by day (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        clicks_by_day_result = await self.db.execute(
            select(
                func.date(Click.clicked_at).label("date"),
                func.count(Click.id).label("count"),
            )
            .where(
                Click.url_id == url_obj.id,
                Click.clicked_at >= thirty_days_ago,
            )
            .group_by(func.date(Click.clicked_at))
            .order_by(func.date(Click.clicked_at))
        )
        clicks_by_day = [
            ClickDataPoint(date=str(row.date), clicks=row.count)
            for row in clicks_by_day_result.fetchall()
        ]

        # Top referers
        referer_result = await self.db.execute(
            select(Click.referer, func.count(Click.id).label("count"))
            .where(Click.url_id == url_obj.id, Click.referer.isnot(None))
            .group_by(Click.referer)
            .order_by(func.count(Click.id).desc())
            .limit(10)
        )
        top_referers = [{"referer": r.referer, "count": r.count} for r in referer_result]

        # Recent 10 clicks
        recent_result = await self.db.execute(
            select(Click)
            .where(Click.url_id == url_obj.id)
            .order_by(Click.clicked_at.desc())
            .limit(10)
        )
        recent_clicks = [
            {
                "clicked_at": c.clicked_at.isoformat(),
                "ip": c.ip_address,
                "referer": c.referer,
                "country": c.country,
            }
            for c in recent_result.scalars()
        ]

        return AnalyticsDetail(
            summary=AnalyticsSummary(
                short_code=url_obj.short_code,
                original_url=url_obj.original_url,
                total_clicks=url_obj.click_count,
                created_at=url_obj.created_at,
                expires_at=url_obj.expires_at,
                is_active=url_obj.is_active,
            ),
            clicks_by_day=clicks_by_day,
            top_referers=top_referers,
            recent_clicks=recent_clicks,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _get_url_by_code(self, short_code: str) -> Optional[URL]:
        result = await self.db.execute(
            select(URL).where(URL.short_code == short_code)
        )
        return result.scalar_one_or_none()

    async def _generate_unique_code(self, max_attempts: int = 5) -> str:
        """Generate a unique code with collision retry."""
        for attempt in range(max_attempts):
            code = generate_short_code(settings.short_code_length)
            existing = await self._get_url_by_code(code)
            if not existing:
                return code
            logger.warning("short_code_collision", code=code, attempt=attempt)
        raise RuntimeError("Failed to generate unique short code after max attempts")

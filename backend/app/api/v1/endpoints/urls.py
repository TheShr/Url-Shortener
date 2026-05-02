from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.middleware.rate_limit import check_rate_limit, get_client_ip
from app.schemas.url import AnalyticsDetail, ShortenRequest, ShortenResponse
from app.services.url_service import URLService

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Shorten a URL",
    description="Creates a short URL. Optionally accepts a custom alias and expiry.",
)
async def shorten_url(
    request: Request,
    body: ShortenRequest,
    db: AsyncSession = Depends(get_db),
) -> ShortenResponse:
    # Rate limit: 10 shortens per minute per IP
    await check_rate_limit(request, settings.rate_limit_shorten, namespace="rl:shorten")

    service = URLService(db)
    try:
        return await service.shorten(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error("shorten_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to shorten URL",
        )


@router.get(
    "/{short_code}",
    summary="Redirect to original URL",
    response_class=RedirectResponse,
    status_code=status.HTTP_301_MOVED_PERMANENTLY,
)
async def redirect_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    # Higher rate limit for redirects
    await check_rate_limit(request, settings.rate_limit_redirect, namespace="rl:redirect")

    service = URLService(db)
    original_url = await service.resolve(
        short_code=short_code,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        referer=request.headers.get("Referer"),
    )

    if not original_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL '{short_code}' not found or expired",
        )

    # 301 for SEO benefit; use 302 if analytics precision > SEO matters
    return RedirectResponse(url=original_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get(
    "/analytics/{short_code}",
    response_model=AnalyticsDetail,
    summary="Get click analytics for a short URL",
)
async def get_analytics(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsDetail:
    service = URLService(db)
    analytics = await service.get_analytics(short_code)

    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found",
        )
    return analytics

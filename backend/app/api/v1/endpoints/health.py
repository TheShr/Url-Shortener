from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.redis import get_redis
from app.schemas.url import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_status = "ok"
    cache_status = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:
        cache_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" and cache_status == "ok" else "degraded",
        db=db_status,
        cache=cache_status,
    )

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.redis import close_redis
from app.db.session import get_db
from app.services.analytics_worker import run_analytics_worker, run_expiry_cleanup
from app.services.url_service import URLService

setup_logging()
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    logger.info("app_starting", environment=settings.environment)

    # Start background workers
    analytics_task = asyncio.create_task(run_analytics_worker())
    cleanup_task = asyncio.create_task(run_expiry_cleanup())
    logger.info("background_workers_started")

    yield

    # Graceful shutdown
    analytics_task.cancel()
    cleanup_task.cancel()
    await close_redis()
    logger.info("app_shutdown")


app = FastAPI(
    title="URL Shortener API",
    description="Production-grade distributed URL shortener with analytics",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)


# ── Global exception handlers ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Request logging middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
    )
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")

@app.get("/{short_code}", include_in_schema=False)
async def root_redirect(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    service = URLService(db)
    forwarded_for = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")
    client_ip = forwarded_for or real_ip or (request.client[0] if request.client else "unknown")

    original_url = await service.resolve(
        short_code=short_code,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
        referer=request.headers.get("Referer"),
    )

    if not original_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL '{short_code}' not found or expired",
        )

    return RedirectResponse(url=original_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


# Convenience: redirect root to docs in dev
@app.get("/", include_in_schema=False)
async def root():
    if not settings.is_production:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/docs")
    return {"status": "ok"}

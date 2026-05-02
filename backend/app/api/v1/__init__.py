from fastapi import APIRouter
from app.api.v1.endpoints import urls, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="", tags=["ops"])
api_router.include_router(urls.router, prefix="", tags=["urls"])

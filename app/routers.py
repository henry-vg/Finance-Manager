from fastapi import APIRouter
from app.api.v1.endpoints import ping_pong
from app.core.settings import settings

api_router = APIRouter()

api_router.include_router(
    ping_pong.router, prefix=settings.app.api_prefix, tags=["Ping Pong"])

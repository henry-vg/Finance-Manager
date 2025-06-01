from fastapi import APIRouter
from app.api.v1.endpoints import hello_world
from app.core.settings import settings

api_router = APIRouter()

api_router.include_router(
    hello_world.router, prefix=settings.app.api_prefix, tags=["Test"])

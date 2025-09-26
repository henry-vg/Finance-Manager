from fastapi import APIRouter
from src.adapters.input.http.v1.routes import (
    health_route as health_route_v1,
)

api_router = APIRouter()

api_router_v1 = APIRouter(prefix="/v1")
api_router_v1.include_router(health_route_v1.router, tags=["Health"])

api_router.include_router(api_router_v1)

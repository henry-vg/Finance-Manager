from fastapi import APIRouter
from src.adapters.input.http.routers.v1 import (
    ping_pong as ping_pong_v1,
)

api_router = APIRouter()

api_router_v1 = APIRouter(prefix="/v1")
api_router_v1.include_router(ping_pong_v1.router, tags=["Ping Pong"])
api_router.include_router(api_router_v1)

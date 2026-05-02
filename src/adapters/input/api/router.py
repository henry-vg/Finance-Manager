from fastapi import APIRouter

from src.adapters.input.api.routes import (
    docs_route,
    healthz_route,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort


def create_api_router(
    docs_url: str,
    docs_title: str,
    docs_dark_mode: bool,
    openapi_url: str,
    healthz_input_port: HealthzInputPort,
) -> APIRouter:
    api_router = APIRouter()

    api_router.include_router(
        router=docs_route.create_router(
            docs_url=docs_url,
            openapi_url=openapi_url,
            docs_title=docs_title,
            docs_dark_mode=docs_dark_mode,
        ),
        include_in_schema=False,
    )

    api_router.include_router(
        router=healthz_route.create_router(
            healthz_input_port=healthz_input_port,
        )
    )

    return api_router

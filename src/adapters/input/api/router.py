from fastapi import APIRouter

from src.adapters.input.api.routes import (
    docs_route,
    healthz_route,
    tag_route,
    user_route,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.user_input_port import UserInputPort


def create_api_router(
    docs_url: str,
    docs_title: str,
    docs_dark_mode: bool,
    openapi_url: str,
    pagination_default_limit: int,
    pagination_max_limit: int,
    healthz_input_port: HealthzInputPort,
    tag_input_port: TagInputPort,
    user_input_port: UserInputPort,
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
        ),
    )

    api_router.include_router(
        router=tag_route.create_router(
            tag_input_port=tag_input_port,
            pagination_default_limit=pagination_default_limit,
            pagination_max_limit=pagination_max_limit,
        ),
    )

    api_router.include_router(
        router=user_route.create_router(
            user_input_port=user_input_port,
            pagination_default_limit=pagination_default_limit,
            pagination_max_limit=pagination_max_limit,
        ),
    )

    return api_router

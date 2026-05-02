import logging

from fastapi import FastAPI

from src.adapters.input.api.exception_handlers import add_exception_handlers
from src.adapters.input.api.middlewares import add_middlewares
from src.adapters.input.api.router import create_api_router
from src.infra.bootstrap import build_application_container
from src.infra.logging import setup_logging

from .tags import openapi_tags

logger = logging.getLogger(name=__name__)


def create_app() -> FastAPI:
    container = build_application_container()
    settings = container.settings

    setup_logging(settings=settings)

    logger.info(
        msg=f"Starting application under '{settings.environment}' environment..."
    )

    app = FastAPI(
        title=settings.fastapi.title,
        description=settings.fastapi.description,
        version=settings.fastapi.version,
        docs_url=None,
        redoc_url=settings.fastapi.redoc_url,
        openapi_url=settings.fastapi.openapi_url,
        openapi_tags=openapi_tags,
    )

    logger.debug(msg="Adding exception handlers...")
    add_exception_handlers(app=app)

    logger.debug(msg="Adding middlewares...")
    add_middlewares(app=app)

    logger.debug(msg="Including routers...")
    router = create_api_router(
        docs_url=settings.fastapi.docs_url,
        docs_title=settings.fastapi.docs_title,
        docs_dark_mode=settings.fastapi.docs_dark_mode,
        openapi_url=settings.fastapi.openapi_url,
        healthz_input_port=container.healthz_input_port,
    )

    app.include_router(router=router)

    return app

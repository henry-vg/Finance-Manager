import logging

from fastapi import FastAPI

from src.infra.settings import settings
from src.infra.logging import setup_logging

from src.adapters.input.http.router import api_router
from src.adapters.input.http.exception_handlers import register_exception_handlers


def create_app() -> FastAPI:
    setup_logging()
    
    logger = logging.getLogger("main")

    logger.info(f"Starting application under {settings.env.environment} environment...")

    app = FastAPI(
        title=settings.app.title,
        description=settings.app.description,
        version=settings.app.version,
        docs_url=settings.app.docs_url,
        redoc_url=settings.app.redoc_url,
        openapi_url=settings.app.openapi_url,
        license_info=settings.app.license_info,
    )

    app.include_router(api_router)
    register_exception_handlers(app)

    return app

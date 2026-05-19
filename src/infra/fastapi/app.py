import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.input.api.exception_handlers import add_exception_handlers
from src.adapters.input.api.middlewares import add_middlewares
from src.adapters.input.api.router import create_api_router
from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.infra.fastapi.tags import openapi_tags
from src.infra.logging import setup_logging
from src.infra.settings import Settings

logger = logging.getLogger(name=__name__)


@asynccontextmanager
async def _default_lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


def create_http_app(
    *,
    settings: Settings,
    healthz_input_port: HealthzInputPort,
    currency_input_port: CurrencyInputPort,
    ledger_account_input_port: LedgerAccountInputPort,
    tag_input_port: TagInputPort,
    user_input_port: UserInputPort,
    lifespan=_default_lifespan,
) -> FastAPI:
    setup_logging(settings=settings)

    logger.info(
        msg=f"Starting application under '{settings.environment}' environment...",
    )

    app = FastAPI(
        title=settings.fastapi.title,
        description=settings.fastapi.description,
        version=settings.fastapi.version,
        docs_url=None,
        lifespan=lifespan,
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
        pagination_default_limit=settings.fastapi.pagination_default_limit,
        pagination_max_limit=settings.fastapi.pagination_max_limit,
        healthz_input_port=healthz_input_port,
        currency_input_port=currency_input_port,
        ledger_account_input_port=ledger_account_input_port,
        tag_input_port=tag_input_port,
        user_input_port=user_input_port,
    )

    app.include_router(router=router)

    return app

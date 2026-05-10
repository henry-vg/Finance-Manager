from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.infra.bootstrap import build_application_container
from src.infra.fastapi.app import create_http_app
from src.infra.postgres import dispose_postgres_engine


def create_app() -> FastAPI:
    container = build_application_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await dispose_postgres_engine(container.postgres_engine)

    return create_http_app(
        settings=container.settings,
        healthz_input_port=container.healthz_input_port,
        tag_input_port=container.tag_input_port,
        user_input_port=container.user_input_port,
        lifespan=lifespan,
    )

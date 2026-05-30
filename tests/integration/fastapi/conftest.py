from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI

from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.infra.fastapi.app import create_http_app
from src.infra.settings import Settings, load_settings
from tests.integration.fastapi.helpers.stubs import (
    CurrencyInputPortStub,
    LedgerAccountInputPortStub,
    ReadyHealthzInputPortStub,
    TagInputPortStub,
    TransactionInputPortStub,
    UserInputPortStub,
)


@pytest.fixture
def fastapi_app_builder():
    def build_app(
        *,
        settings: Settings | None = None,
        healthz_input_port: HealthzInputPort | None = None,
        currency_input_port: CurrencyInputPort | None = None,
        ledger_account_input_port: LedgerAccountInputPort | None = None,
        tag_input_port: TagInputPort | None = None,
        transaction_input_port: TransactionInputPort | None = None,
        user_input_port: UserInputPort | None = None,
    ) -> FastAPI:
        return create_http_app(
            settings=settings or load_settings(),
            healthz_input_port=healthz_input_port or ReadyHealthzInputPortStub(),
            currency_input_port=currency_input_port or CurrencyInputPortStub(),
            ledger_account_input_port=(
                ledger_account_input_port or LedgerAccountInputPortStub()
            ),
            tag_input_port=tag_input_port or TagInputPortStub(),
            transaction_input_port=(
                transaction_input_port or TransactionInputPortStub()
            ),
            user_input_port=user_input_port or UserInputPortStub(),
        )

    return build_app


@pytest.fixture
def fastapi_app(
    fastapi_app_builder,
) -> FastAPI:
    return fastapi_app_builder()


@pytest.fixture
def fastapi_client_factory() -> object:
    @asynccontextmanager
    async def factory(
        app: FastAPI,
        *,
        raise_app_exceptions: bool = True,
    ) -> AsyncIterator[httpx.AsyncClient]:
        transport = httpx.ASGITransport(
            app=app,
            raise_app_exceptions=raise_app_exceptions,
        )

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client

    return factory


@pytest.fixture
def currency_input_port_stub() -> CurrencyInputPortStub:
    return CurrencyInputPortStub()


@pytest.fixture
def ledger_account_input_port_stub() -> LedgerAccountInputPortStub:
    return LedgerAccountInputPortStub()


@pytest.fixture
def tag_input_port_stub() -> TagInputPortStub:
    return TagInputPortStub()


@pytest.fixture
def transaction_input_port_stub() -> TransactionInputPortStub:
    return TransactionInputPortStub()


@pytest.fixture
def user_input_port_stub() -> UserInputPortStub:
    return UserInputPortStub()

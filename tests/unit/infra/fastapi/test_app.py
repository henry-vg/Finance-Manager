from typing import cast

import pytest
from fastapi import APIRouter

from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.infra.fastapi.app import create_http_app
from src.infra.fastapi.tags import openapi_tags
from src.infra.settings import load_settings


def test_create_http_app_configures_router_and_openapi_tags(monkeypatch) -> None:
    import src.infra.fastapi.app as app_module

    captured: dict[str, object] = {}
    router = APIRouter()

    @router.get("/probe")
    async def probe() -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(app_module, "setup_logging", lambda settings: None)
    monkeypatch.setattr(app_module, "add_exception_handlers", lambda app: None)
    monkeypatch.setattr(app_module, "add_middlewares", lambda app: None)

    def fake_create_api_router(**kwargs):
        captured.update(kwargs)
        return router

    monkeypatch.setattr(app_module, "create_api_router", fake_create_api_router)

    settings = load_settings()
    healthz_input_port = cast(HealthzInputPort, object())
    currency_input_port = cast(CurrencyInputPort, object())
    ledger_account_input_port = cast(LedgerAccountInputPort, object())
    tag_input_port = cast(TagInputPort, object())
    transaction_input_port = cast(TransactionInputPort, object())
    user_input_port = cast(UserInputPort, object())

    app = create_http_app(
        settings=settings,
        healthz_input_port=healthz_input_port,
        currency_input_port=currency_input_port,
        ledger_account_input_port=ledger_account_input_port,
        tag_input_port=tag_input_port,
        transaction_input_port=transaction_input_port,
        user_input_port=user_input_port,
    )

    assert app.title == settings.fastapi.title
    assert app.openapi_tags == openapi_tags
    assert captured["currency_input_port"] is currency_input_port
    assert captured["transaction_input_port"] is transaction_input_port
    assert (
        captured["pagination_default_limit"]
        == settings.fastapi.pagination_default_limit
    )
    assert captured["pagination_max_limit"] == settings.fastapi.pagination_max_limit
    assert any(getattr(route, "path", None) == "/probe" for route in app.routes)


@pytest.mark.anyio
async def test_create_http_app_uses_default_lifespan_context(monkeypatch) -> None:
    import src.infra.fastapi.app as app_module

    router = APIRouter()

    monkeypatch.setattr(app_module, "setup_logging", lambda settings: None)
    monkeypatch.setattr(app_module, "add_exception_handlers", lambda app: None)
    monkeypatch.setattr(app_module, "add_middlewares", lambda app: None)
    monkeypatch.setattr(app_module, "create_api_router", lambda **kwargs: router)

    settings = load_settings()
    app = create_http_app(
        settings=settings,
        healthz_input_port=cast(HealthzInputPort, object()),
        currency_input_port=cast(CurrencyInputPort, object()),
        ledger_account_input_port=cast(LedgerAccountInputPort, object()),
        tag_input_port=cast(TagInputPort, object()),
        transaction_input_port=cast(TransactionInputPort, object()),
        user_input_port=cast(UserInputPort, object()),
    )

    async with app.router.lifespan_context(app):
        assert app.docs_url is None

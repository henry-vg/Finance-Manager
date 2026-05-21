from fastapi import APIRouter

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
    healthz_input_port = object()
    currency_input_port = object()
    ledger_account_input_port = object()
    tag_input_port = object()
    user_input_port = object()

    app = create_http_app(
        settings=settings,
        healthz_input_port=healthz_input_port,
        currency_input_port=currency_input_port,
        ledger_account_input_port=ledger_account_input_port,
        tag_input_port=tag_input_port,
        user_input_port=user_input_port,
    )

    assert app.title == settings.fastapi.title
    assert app.openapi_tags == openapi_tags
    assert captured["currency_input_port"] is currency_input_port
    assert any(route.path == "/probe" for route in app.routes)

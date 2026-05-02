import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api import middlewares
from src.adapters.input.api.middlewares import add_middlewares


@pytest.mark.anyio
async def test_middlewares_add_trace_id_header_and_route_path_to_logs(monkeypatch):
    app = FastAPI()
    add_middlewares(app)
    logged_messages: list[tuple[str, dict[str, object] | None]] = []

    def fake_logger_info(
        message: str,
        *,
        extra: dict[str, object] | None = None,
    ) -> None:
        logged_messages.append((message, extra))

    monkeypatch.setattr(middlewares.logger, "info", fake_logger_info)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/ping", headers={"X-Trace-Id": "trace-123"})

    request_log = next(
        extra
        for message, extra in logged_messages
        if message == "Request received. Processing..."
    )
    response_log = next(
        extra for message, extra in logged_messages if message == "Response sent"
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-123"
    assert request_log is not None
    assert response_log is not None
    assert request_log["method"] == "GET"
    assert response_log["route_path"] == "/ping"
    assert response_log["status_code"] == 200

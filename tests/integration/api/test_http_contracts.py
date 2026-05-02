import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.infra.fastapi.app import create_http_app
from src.infra.settings import load_settings


class _Payload(BaseModel):
    value: int


class _ReadyHealthzInputPortStub(HealthzInputPort):
    async def get_healthz_liveness(self) -> HealthzLiveness:
        return HealthzLiveness(status=HealthzStatus.OK)

    async def get_healthz_readiness(self) -> HealthzReadiness:
        return HealthzReadiness(
            status=HealthzStatus.OK,
            dependencies=HealthzReadinessDependencies(
                api=HealthzStatus.OK,
                database=HealthzStatus.OK,
            ),
        )


def _create_test_app() -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=_ReadyHealthzInputPortStub(),
    )


@pytest.mark.anyio
async def test_docs_endpoint_is_customized_and_returns_html():
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text
    assert 'document.documentElement.classList.add("dark-mode")' in response.text


@pytest.mark.anyio
async def test_openapi_endpoint_exposes_expected_metadata():
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert app.docs_url is None
    assert response.status_code == 200
    assert response.json()["info"]["title"] == app.title
    assert response.json()["info"]["version"] == app.version
    assert any(tag["name"] == "HealthZ" for tag in response.json()["tags"])


@pytest.mark.anyio
async def test_middleware_passes_trace_id_through_response():
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/healthz/liveness",
            headers={"X-Trace-Id": "trace-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-123"


@pytest.mark.anyio
async def test_registered_validation_handler_returns_problem_details_for_body_errors():
    app = _create_test_app()

    @app.post("/validation/body")
    async def validate_body(payload: _Payload) -> dict[str, int]:
        return {"value": payload.value}

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/validation/body",
            json={"value": "bad"},
            headers={"X-Trace-Id": "trace-123"},
        )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Validation failed."
    assert response.json()["trace_id"] == "trace-123"


@pytest.mark.anyio
async def test_registered_validation_handler_returns_problem_details_for_query_errors():
    app = _create_test_app()

    @app.get("/validation/query")
    async def validate_query(value: int) -> dict[str, int]:
        return {"value": value}

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/validation/query", params={"value": "bad"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Invalid request."


@pytest.mark.anyio
async def test_registered_generic_exception_handler_returns_problem_details():
    app = _create_test_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom", headers={"X-Trace-Id": "trace-123"})

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "An unexpected error occurred."
    assert response.json()["trace_id"] == "trace-123"

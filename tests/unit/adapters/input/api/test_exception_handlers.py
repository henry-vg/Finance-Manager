from http import HTTPStatus

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.adapters.input.api.exception_handlers import add_exception_handlers


class _Payload(BaseModel):
    value: int


def _create_test_app() -> FastAPI:
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/http")
    async def raise_http_exception() -> None:
        raise HTTPException(status_code=404, detail="missing")

    @app.get("/boom")
    async def raise_runtime_error() -> None:
        raise RuntimeError("boom")

    @app.post("/body")
    async def validate_body(payload: _Payload) -> dict[str, int]:
        return {"value": payload.value}

    @app.get("/query")
    async def validate_query(value: int) -> dict[str, int]:
        return {"value": value}

    return app


def _assert_problem_details(
    response: httpx.Response,
    *,
    expected_status: int,
    expected_detail: str,
    expected_instance: str,
    expected_trace_id: str | None,
) -> None:
    payload = response.json()

    assert response.headers["content-type"].startswith("application/problem+json")
    assert payload["title"] == HTTPStatus(expected_status).phrase
    assert payload["status"] == expected_status
    assert payload["type"] == "about:blank"
    assert payload["detail"] == expected_detail
    assert payload["instance"] == expected_instance
    assert payload["trace_id"] == expected_trace_id
    assert payload["timestamp"].endswith("Z")


@pytest.mark.anyio
async def test_http_exception_is_rendered_as_problem_details():
    transport = httpx.ASGITransport(app=_create_test_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/http", headers={"X-Trace-Id": "trace-123"})

    assert response.status_code == 404
    _assert_problem_details(
        response,
        expected_status=404,
        expected_detail="missing",
        expected_instance="http://test/http",
        expected_trace_id="trace-123",
    )


@pytest.mark.anyio
async def test_body_validation_error_is_rendered_as_422_problem_details():
    transport = httpx.ASGITransport(app=_create_test_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/body", json={"value": "bad"})

    assert response.status_code == 422
    _assert_problem_details(
        response,
        expected_status=422,
        expected_detail="Validation failed.",
        expected_instance="http://test/body",
        expected_trace_id=None,
    )
    assert "errors" in response.json()


@pytest.mark.anyio
async def test_non_body_validation_error_is_rendered_as_400_problem_details():
    transport = httpx.ASGITransport(app=_create_test_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/query", params={"value": "bad"})

    assert response.status_code == 400
    _assert_problem_details(
        response,
        expected_status=400,
        expected_detail="Invalid request.",
        expected_instance="http://test/query?value=bad",
        expected_trace_id=None,
    )
    assert "errors" in response.json()


@pytest.mark.anyio
async def test_generic_exception_is_rendered_as_500_problem_details():
    transport = httpx.ASGITransport(app=_create_test_app(), raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    _assert_problem_details(
        response,
        expected_status=500,
        expected_detail="An unexpected error occurred.",
        expected_instance="http://test/boom",
        expected_trace_id=None,
    )

import pytest
from pydantic import BaseModel


class _Payload(BaseModel):
    value: int


@pytest.mark.anyio
async def test_middleware_passes_trace_id_through_response(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    async with fastapi_client_factory(fastapi_app) as client:
        response = await client.get(
            "/healthz/liveness",
            headers={"X-Trace-Id": "trace-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-123"


@pytest.mark.anyio
async def test_registered_validation_handler_returns_problem_details_for_body_errors(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    @fastapi_app.post("/validation/body")
    async def validate_body(payload: _Payload) -> dict[str, int]:
        return {"value": payload.value}

    async with fastapi_client_factory(fastapi_app) as client:
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
async def test_registered_validation_handler_returns_problem_details_for_query_errors(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    @fastapi_app.get("/validation/query")
    async def validate_query(value: int) -> dict[str, int]:
        return {"value": value}

    async with fastapi_client_factory(fastapi_app) as client:
        response = await client.get("/validation/query", params={"value": "bad"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Invalid request."


@pytest.mark.anyio
async def test_registered_generic_exception_handler_returns_problem_details(
    fastapi_app,
    fastapi_client_factory,
) -> None:
    @fastapi_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    async with fastapi_client_factory(
        fastapi_app,
        raise_app_exceptions=False,
    ) as client:
        response = await client.get("/boom", headers={"X-Trace-Id": "trace-123"})

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "An unexpected error occurred."
    assert response.json()["trace_id"] == "trace-123"

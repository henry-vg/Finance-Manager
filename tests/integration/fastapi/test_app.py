import httpx
import pytest
from pydantic import BaseModel

from tests.integration.fastapi.app_builder import create_default_test_app


class _Payload(BaseModel):
    value: int


@pytest.mark.anyio
async def test_openapi_endpoint_exposes_expected_metadata():
    app = create_default_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert app.docs_url is None
    assert response.status_code == 200
    openapi_schema = response.json()

    assert openapi_schema["info"]["title"] == app.title
    assert openapi_schema["info"]["version"] == app.version
    assert any(tag["name"] == "Currency" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "HealthZ" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "LedgerAccount" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "Tag" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "User" for tag in openapi_schema["tags"])

    currency_collection_path = openapi_schema["paths"]["/currency"]
    currency_list_path = openapi_schema["paths"]["/currency/list"]
    healthz_liveness_path = openapi_schema["paths"]["/healthz/liveness"]
    healthz_readiness_path = openapi_schema["paths"]["/healthz/readiness"]
    ledger_account_collection_path = openapi_schema["paths"]["/ledger-account"]
    ledger_account_list_path = openapi_schema["paths"]["/ledger-account/list"]
    tag_collection_path = openapi_schema["paths"]["/tag"]
    tag_list_path = openapi_schema["paths"]["/tag/list"]
    user_collection_path = openapi_schema["paths"]["/user"]
    user_list_path = openapi_schema["paths"]["/user/list"]
    healthz_status_schema = openapi_schema["components"]["schemas"][
        "HealthzStatusResponse"
    ]
    ledger_account_kind_schema = openapi_schema["components"]["schemas"][
        "LedgerAccountKindSchema"
    ]

    assert "get" in healthz_liveness_path
    assert "get" in healthz_readiness_path
    assert "200" in healthz_liveness_path["get"]["responses"]
    assert "200" in healthz_readiness_path["get"]["responses"]
    assert "503" in healthz_readiness_path["get"]["responses"]
    assert healthz_status_schema["enum"] == ["ok", "not_ok"]
    assert ledger_account_kind_schema["enum"] == [
        "bank_account",
        "credit_card",
        "wallet",
        "other",
    ]

    assert "post" in currency_collection_path
    assert "get" in currency_collection_path
    assert "put" in currency_collection_path
    assert "delete" in currency_collection_path
    assert "id" in {
        parameter["name"] for parameter in currency_collection_path["get"]["parameters"]
    }
    assert "id" in {
        parameter["name"] for parameter in currency_collection_path["put"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in currency_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"]
        for parameter in currency_collection_path["delete"]["parameters"]
    }
    assert "200" in currency_collection_path["get"]["responses"]
    assert "404" in currency_collection_path["get"]["responses"]
    assert "201" in currency_collection_path["post"]["responses"]
    assert "409" in currency_collection_path["post"]["responses"]
    assert "200" in currency_collection_path["put"]["responses"]
    assert "404" in currency_collection_path["put"]["responses"]
    assert "409" in currency_collection_path["put"]["responses"]
    assert "204" in currency_collection_path["delete"]["responses"]
    assert "404" in currency_collection_path["delete"]["responses"]
    assert "get" in currency_list_path
    assert {
        parameter["name"] for parameter in currency_list_path["get"]["parameters"]
    } == {
        "offset",
        "limit",
        "sort",
    }
    assert "200" in currency_list_path["get"]["responses"]

    assert "post" in ledger_account_collection_path
    assert "get" in ledger_account_collection_path
    assert "put" in ledger_account_collection_path
    assert "delete" in ledger_account_collection_path
    assert "id" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["get"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["put"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["delete"]["parameters"]
    }
    assert "200" in ledger_account_collection_path["get"]["responses"]
    assert "404" in ledger_account_collection_path["get"]["responses"]
    assert "201" in ledger_account_collection_path["post"]["responses"]
    assert "200" in ledger_account_collection_path["put"]["responses"]
    assert "404" in ledger_account_collection_path["put"]["responses"]
    assert "204" in ledger_account_collection_path["delete"]["responses"]
    assert "404" in ledger_account_collection_path["delete"]["responses"]
    assert "get" in ledger_account_list_path
    assert {
        parameter["name"] for parameter in ledger_account_list_path["get"]["parameters"]
    } == {"offset", "limit", "sort"}
    assert "200" in ledger_account_list_path["get"]["responses"]

    assert "post" in tag_collection_path
    assert "get" in tag_collection_path
    assert "put" in tag_collection_path
    assert "delete" in tag_collection_path
    assert "id" in {
        parameter["name"] for parameter in tag_collection_path["get"]["parameters"]
    }
    assert "id" in {
        parameter["name"] for parameter in tag_collection_path["put"]["parameters"]
    }
    assert "id" in {
        parameter["name"] for parameter in tag_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"] for parameter in tag_collection_path["delete"]["parameters"]
    }
    assert "200" in tag_collection_path["get"]["responses"]
    assert "404" in tag_collection_path["get"]["responses"]
    assert "201" in tag_collection_path["post"]["responses"]
    assert "200" in tag_collection_path["put"]["responses"]
    assert "404" in tag_collection_path["put"]["responses"]
    assert "204" in tag_collection_path["delete"]["responses"]
    assert "404" in tag_collection_path["delete"]["responses"]
    assert "get" in tag_list_path
    assert {parameter["name"] for parameter in tag_list_path["get"]["parameters"]} == {
        "offset",
        "limit",
        "sort",
    }
    assert "200" in tag_list_path["get"]["responses"]

    assert "post" in user_collection_path
    assert "get" in user_collection_path
    assert "put" in user_collection_path
    assert "delete" in user_collection_path
    assert "email" in {
        parameter["name"] for parameter in user_collection_path["get"]["parameters"]
    }
    assert "current_email" in {
        parameter["name"] for parameter in user_collection_path["put"]["parameters"]
    }
    assert "email" in {
        parameter["name"] for parameter in user_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"] for parameter in user_collection_path["delete"]["parameters"]
    }
    assert "200" in user_collection_path["get"]["responses"]
    assert "404" in user_collection_path["get"]["responses"]
    assert "201" in user_collection_path["post"]["responses"]
    assert "409" in user_collection_path["post"]["responses"]
    assert "200" in user_collection_path["put"]["responses"]
    assert "404" in user_collection_path["put"]["responses"]
    assert "409" in user_collection_path["put"]["responses"]
    assert "204" in user_collection_path["delete"]["responses"]
    assert "404" in user_collection_path["delete"]["responses"]
    assert "get" in user_list_path
    assert {parameter["name"] for parameter in user_list_path["get"]["parameters"]} == {
        "offset",
        "limit",
        "sort",
    }
    assert "200" in user_list_path["get"]["responses"]

    sort_parameter = next(
        parameter
        for parameter in user_list_path["get"]["parameters"]
        if parameter["name"] == "sort"
    )

    assert "+" in sort_parameter["description"]
    assert "-" in sort_parameter["description"]
    assert "created_at" in sort_parameter["description"]
    assert "id" in sort_parameter["description"]
    assert "Default sort: created_at." in sort_parameter["description"]


@pytest.mark.anyio
async def test_middleware_passes_trace_id_through_response():
    app = create_default_test_app()
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
    app = create_default_test_app()

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
    app = create_default_test_app()

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
    app = create_default_test_app()

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

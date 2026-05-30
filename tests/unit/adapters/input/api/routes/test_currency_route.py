import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.currency_route import create_router
from src.core.domain.currency import (
    Currency,
    CurrencyDataValidationError,
    CurrencyISOCodeConflictError,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from tests.integration.fastapi.helpers.builders import (
    build_currency_create_payload,
    build_currency_response,
    build_currency_update_payload,
    build_page_response,
)
from tests.integration.fastapi.helpers.stubs import (
    CurrencyInputPortStub as _CurrencyInputPortStub,
)
from tests.integration.fastapi.helpers.stubs import (
    build_timestamp as _build_timestamp,
)


def _create_test_app(currency_input_port: _CurrencyInputPortStub) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_router(
            currency_input_port=currency_input_port,
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )
    return app


@pytest.mark.anyio
async def test_get_currency_returns_currency_response() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.currencies_by_id[1] = Currency(
        id=1,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/currency", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == build_currency_response()


@pytest.mark.anyio
async def test_get_currency_returns_404_when_currency_does_not_exist() -> None:
    app = _create_test_app(_CurrencyInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/currency", params={"id": 1})

    assert response.status_code == 404
    assert response.json()["detail"] == "Currency not found."


@pytest.mark.anyio
async def test_list_currencies_returns_paginated_response() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.currencies_by_id[1] = Currency(
        id=1,
        iso_code="USD",
        iso_numeric="840",
        name="Dollar",
        symbol="$",
        decimal_places=2,
        created_at=_build_timestamp(2),
        updated_at=_build_timestamp(2),
    )
    currency_input_port_stub.currencies_by_id[2] = Currency(
        id=2,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/currency/list",
            params={"offset": 0, "limit": 10, "sort": "iso_code"},
        )

    assert response.status_code == 200
    assert response.json() == build_page_response(
        items=[
            build_currency_response(id=2),
            build_currency_response(
                id=1,
                created_at="2026-05-02T00:00:00.000Z",
                updated_at="2026-05-02T00:00:00.000Z",
                iso_code="USD",
                iso_numeric="840",
                name="Dollar",
                symbol="$",
            ),
        ],
        limit=10,
        total=2,
    )
    assert currency_input_port_stub.list_currency_queries == [
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="iso_code", direction=SortDirection.ASC),),
        ),
    ]


@pytest.mark.anyio
async def test_create_currency_returns_created_response() -> None:
    app = _create_test_app(_CurrencyInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/currency", json=build_currency_create_payload())

    assert response.status_code == 201
    assert response.json() == build_currency_response()


@pytest.mark.anyio
async def test_create_currency_returns_409_when_iso_code_already_exists() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.create_error = CurrencyISOCodeConflictError()
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/currency", json=build_currency_create_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == "Currency ISO code already exists."


@pytest.mark.anyio
async def test_update_currency_returns_422_for_invalid_domain_data() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.currencies_by_id[1] = Currency(
        id=1,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    currency_input_port_stub.update_error = CurrencyDataValidationError()
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/currency",
            params={"id": 1},
            json=build_currency_update_payload(
                iso_code="BRL",
                iso_numeric="986",
                name="   ",
                symbol="R$",
            ),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Currency data is invalid."


@pytest.mark.anyio
async def test_delete_currency_soft_deletes_by_default() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.currencies_by_id[1] = Currency(
        id=1,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/currency", params={"id": 1})

    assert response.status_code == 204
    assert currency_input_port_stub.delete_calls == [(1, False)]


@pytest.mark.anyio
async def test_delete_currency_forwards_hard_delete_query_param() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.currencies_by_id[1] = Currency(
        id=1,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/currency",
            params={"id": 1, "hard_delete": "true"},
        )

    assert response.status_code == 204
    assert currency_input_port_stub.delete_calls == [(1, True)]

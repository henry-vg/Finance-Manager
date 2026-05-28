from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.currency_route import create_router
from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    CurrencyDataValidationError,
    CurrencyISOCodeConflictError,
    CurrencyNotFoundError,
    UpdateCurrencyData,
)
from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class _CurrencyInputPortStub:
    def __init__(self) -> None:
        self.currencies_by_id: dict[int, Currency] = {}
        self.soft_deleted_currency_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_currency_queries: list[ListQuery] = []
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self._next_currency_id = 1

    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]:
        self.list_currency_queries.append(list_query)
        active_currencies = [
            currency
            for currency_id, currency in self.currencies_by_id.items()
            if currency_id not in self.soft_deleted_currency_ids
        ]
        active_currencies.sort(key=lambda currency: (currency.iso_code, currency.id))
        return Page[Currency](
            items=active_currencies[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_currencies),
        )

    async def get_currency(self, currency_id: int) -> Currency:
        if (
            currency_id in self.soft_deleted_currency_ids
            or currency_id not in self.currencies_by_id
        ):
            raise CurrencyNotFoundError()

        return self.currencies_by_id[currency_id]

    async def create_currency(
        self,
        data: CreateCurrencyData,
    ) -> Currency:
        if self.create_error is not None:
            raise self.create_error

        currency = Currency(
            id=self._next_currency_id,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.currencies_by_id[currency.id] = currency
        self._next_currency_id += 1
        return currency

    async def update_currency(
        self,
        currency_id: int,
        data: UpdateCurrencyData,
    ) -> Currency:
        if self.update_error is not None:
            raise self.update_error

        current = await self.get_currency(currency_id)
        updated = Currency(
            id=current.id,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.currencies_by_id[currency_id] = updated
        return updated

    async def delete_currency(
        self,
        currency_id: int,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((currency_id, hard_delete))
        if currency_id in self.soft_deleted_currency_ids:
            if hard_delete:
                self.soft_deleted_currency_ids.remove(currency_id)
                self.currencies_by_id.pop(currency_id, None)
                return
            raise CurrencyNotFoundError()
        if currency_id not in self.currencies_by_id:
            raise CurrencyNotFoundError()
        if hard_delete:
            self.currencies_by_id.pop(currency_id, None)
            return
        self.soft_deleted_currency_ids.add(currency_id)


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
    assert response.json() == {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "iso_code": "BRL",
        "iso_numeric": "986",
        "name": "Real",
        "symbol": "R$",
        "decimal_places": 2,
        "storage_decimal_places": 3,
    }


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
    assert response.json() == {
        "items": [
            {
                "id": 2,
                "created_at": "2026-05-01T00:00:00.000Z",
                "updated_at": "2026-05-01T00:00:00.000Z",
                "iso_code": "BRL",
                "iso_numeric": "986",
                "name": "Real",
                "symbol": "R$",
                "decimal_places": 2,
                "storage_decimal_places": 3,
            },
            {
                "id": 1,
                "created_at": "2026-05-02T00:00:00.000Z",
                "updated_at": "2026-05-02T00:00:00.000Z",
                "iso_code": "USD",
                "iso_numeric": "840",
                "name": "Dollar",
                "symbol": "$",
                "decimal_places": 2,
                "storage_decimal_places": 3,
            },
        ],
        "offset": 0,
        "limit": 10,
        "total": 2,
    }
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
        response = await client.post(
            "/currency",
            json={
                "iso_code": "BRL",
                "iso_numeric": "986",
                "name": "Real",
                "symbol": "R$",
                "decimal_places": 2,
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "iso_code": "BRL",
        "iso_numeric": "986",
        "name": "Real",
        "symbol": "R$",
        "decimal_places": 2,
        "storage_decimal_places": 3,
    }


@pytest.mark.anyio
async def test_create_currency_returns_409_when_iso_code_already_exists() -> None:
    currency_input_port_stub = _CurrencyInputPortStub()
    currency_input_port_stub.create_error = CurrencyISOCodeConflictError()
    app = _create_test_app(currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/currency",
            json={
                "iso_code": "BRL",
                "iso_numeric": "986",
                "name": "Real",
                "symbol": "R$",
                "decimal_places": 2,
            },
        )

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
            json={
                "iso_code": "BRL",
                "iso_numeric": "986",
                "name": "   ",
                "symbol": "R$",
                "decimal_places": 2,
            },
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

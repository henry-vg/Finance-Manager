from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.ledger_account_route import create_router
from src.core.domain.ledger_account import (
    LedgerAccount,
    LedgerAccountBalance,
    LedgerAccountInstrumentKind,
    LedgerAccountInstrumentKindNotAllowedError,
    LedgerAccountType,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from tests.integration.fastapi.helpers.builders import (
    build_ledger_account_create_payload,
    build_ledger_account_response,
    build_ledger_account_update_payload,
    build_page_response,
)
from tests.integration.fastapi.helpers.stubs import (
    LedgerAccountInputPortStub as _LedgerAccountInputPortStub,
)
from tests.integration.fastapi.helpers.stubs import (
    build_timestamp as _build_timestamp,
)


def _build_balance(
    *,
    currency_id: int,
    current_balance: str,
    future_balance: str,
) -> LedgerAccountBalance:
    return LedgerAccountBalance(
        currency_id=currency_id,
        current_balance=Decimal(current_balance),
        future_balance=Decimal(future_balance),
    )


def _create_test_app(
    ledger_account_input_port: _LedgerAccountInputPortStub,
) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_router(
            ledger_account_input_port=ledger_account_input_port,
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )
    return app


@pytest.mark.anyio
async def test_get_ledger_account_returns_ledger_account_response() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.ledger_accounts_by_id[1] = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        instrument_kind=LedgerAccountInstrumentKind.BANK_ACCOUNT,
        balances=(
            _build_balance(
                currency_id=1,
                current_balance="100.00",
                future_balance="150.00",
            ),
        ),
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ledger-account", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == build_ledger_account_response(
        balances=[
            {
                "currency_id": 1,
                "current_balance": "100.00",
                "future_balance": "150.00",
            },
        ],
    )


@pytest.mark.anyio
async def test_get_ledger_account_returns_null_instrument_kind_when_absent() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.ledger_accounts_by_id[1] = LedgerAccount(
        id=1,
        title="Salary",
        type=LedgerAccountType.INCOME,
        instrument_kind=None,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ledger-account", params={"id": 1})

    assert response.status_code == 200
    assert response.json()["instrument_kind"] is None
    assert response.json()["balances"] == []


@pytest.mark.anyio
async def test_get_ledger_account_returns_404_when_ledger_account_does_not_exist() -> (
    None
):
    app = _create_test_app(_LedgerAccountInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ledger-account", params={"id": 1})

    assert response.status_code == 404
    assert response.json()["detail"] == "Ledger account not found."


@pytest.mark.anyio
async def test_list_ledger_accounts_returns_paginated_response() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.ledger_accounts_by_id[1] = LedgerAccount(
        id=1,
        title="Credit Card",
        type=LedgerAccountType.LIABILITY,
        instrument_kind=LedgerAccountInstrumentKind.CREDIT_CARD,
        balances=(
            _build_balance(
                currency_id=2,
                current_balance="-2500.00",
                future_balance="-2750.00",
            ),
        ),
        created_at=_build_timestamp(2),
        updated_at=_build_timestamp(2),
    )
    ledger_account_input_port_stub.ledger_accounts_by_id[2] = LedgerAccount(
        id=2,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        instrument_kind=LedgerAccountInstrumentKind.BANK_ACCOUNT,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/ledger-account/list",
            params={"offset": 0, "limit": 10, "sort": "title"},
        )

    assert response.status_code == 200
    assert response.json() == build_page_response(
        items=[
            build_ledger_account_response(
                created_at="2026-05-02T00:00:00.000Z",
                updated_at="2026-05-02T00:00:00.000Z",
                title="Credit Card",
                type="liability",
                instrument_kind="credit_card",
                balances=[
                    {
                        "currency_id": 2,
                        "current_balance": "-2500.00",
                        "future_balance": "-2750.00",
                    },
                ],
            ),
            build_ledger_account_response(id=2, balances=[]),
        ],
        limit=10,
        total=2,
    )
    assert ledger_account_input_port_stub.list_ledger_account_queries == [
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="title", direction=SortDirection.ASC),),
        ),
    ]


@pytest.mark.anyio
async def test_create_ledger_account_returns_created_response() -> None:
    app = _create_test_app(_LedgerAccountInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ledger-account",
            json=build_ledger_account_create_payload(),
        )

    assert response.status_code == 201
    assert response.json() == build_ledger_account_response()


@pytest.mark.anyio
async def test_create_ledger_account_allows_missing_instrument_kind() -> None:
    app = _create_test_app(_LedgerAccountInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ledger-account",
            json={
                "title": "Salary",
                "type": "income",
            },
        )

    assert response.status_code == 201
    assert response.json() == build_ledger_account_response(
        title="Salary",
        type="income",
        instrument_kind=None,
    )


@pytest.mark.anyio
async def test_create_ledger_account_returns_422_for_invalid_instrument_kind() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.create_error = (
        LedgerAccountInstrumentKindNotAllowedError()
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ledger-account",
            json=build_ledger_account_create_payload(
                title="Bad Expense",
                type="expense",
                instrument_kind="wallet",
            ),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Ledger account instrument kind is not allowed for the provided "
        "ledger account type."
    )


@pytest.mark.anyio
async def test_update_ledger_account_returns_404_for_missing_ledger_account() -> None:
    app = _create_test_app(_LedgerAccountInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/ledger-account",
            params={"id": 1},
            json=build_ledger_account_update_payload(),
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ledger account not found."


@pytest.mark.anyio
async def test_update_ledger_account_returns_422_for_invalid_instrument_kind() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.ledger_accounts_by_id[1] = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        instrument_kind=LedgerAccountInstrumentKind.BANK_ACCOUNT,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    ledger_account_input_port_stub.update_error = (
        LedgerAccountInstrumentKindNotAllowedError()
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/ledger-account",
            params={"id": 1},
            json=build_ledger_account_update_payload(
                title="Bad Expense",
                type="expense",
                instrument_kind="wallet",
            ),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Ledger account instrument kind is not allowed for the provided "
        "ledger account type."
    )


@pytest.mark.anyio
async def test_delete_ledger_account_soft_deletes_by_default() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.ledger_accounts_by_id[1] = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        instrument_kind=LedgerAccountInstrumentKind.BANK_ACCOUNT,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/ledger-account", params={"id": 1})

    assert response.status_code == 204
    assert ledger_account_input_port_stub.delete_calls == [(1, False)]


@pytest.mark.anyio
async def test_delete_ledger_account_forwards_hard_delete_query_param() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    ledger_account_input_port_stub.ledger_accounts_by_id[1] = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        instrument_kind=LedgerAccountInstrumentKind.BANK_ACCOUNT,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/ledger-account",
            params={"id": 1, "hard_delete": "true"},
        )

    assert response.status_code == 204
    assert ledger_account_input_port_stub.delete_calls == [(1, True)]

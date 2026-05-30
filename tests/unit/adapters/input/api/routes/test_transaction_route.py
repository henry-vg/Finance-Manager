from datetime import date
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.transaction_route import create_router
from src.core.domain.transaction import (
    CreateTransactionData,
    NewEntry,
    NewEntryTag,
    TransactionEntriesMustBalanceError,
    TransactionEntryCurrencyNotFoundError,
    TransactionStatus,
    UpdateTransactionData,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from tests.integration.fastapi.helpers.builders import (
    build_page_response,
    build_posted_transaction_response,
    build_transaction_create_payload,
    build_transaction_response,
    build_transaction_summary_response,
    build_transaction_update_payload,
    build_updated_transaction_response,
    build_voided_transaction_response,
)
from tests.integration.fastapi.helpers.stubs import (
    TransactionInputPortStub as _TransactionInputPortStub,
)
from tests.integration.fastapi.helpers.stubs import (
    build_timestamp as _build_timestamp,
)
from tests.integration.fastapi.helpers.stubs import (
    build_transaction_with_entries as _build_transaction_with_entries,
)


def _create_test_app(
    transaction_input_port: _TransactionInputPortStub,
) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_router(
            transaction_input_port=transaction_input_port,
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )
    return app


@pytest.mark.anyio
async def test_list_transactions_returns_paginated_response() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = _build_transaction_with_entries(
        transaction_id=1,
        title="Airline tickets",
    )
    transaction_input_port_stub.transactions_by_id[2] = _build_transaction_with_entries(
        transaction_id=2,
        title="Zoo tickets",
        status=TransactionStatus.POSTED,
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/transaction/list",
            params={"offset": 0, "limit": 10, "sort": "title"},
        )

    assert response.status_code == 200
    assert response.json() == build_page_response(
        items=[
            build_transaction_summary_response(),
            build_transaction_summary_response(
                id=2,
                title="Zoo tickets",
                status="posted",
            ),
        ],
        limit=10,
        total=2,
    )
    assert transaction_input_port_stub.list_transaction_queries == [
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="title", direction=SortDirection.ASC),),
        ),
    ]


@pytest.mark.anyio
async def test_get_transaction_returns_transaction_response() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = (
        _build_transaction_with_entries()
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/transaction", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == build_transaction_response()


@pytest.mark.anyio
async def test_get_transaction_returns_404_when_transaction_does_not_exist() -> None:
    app = _create_test_app(_TransactionInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/transaction", params={"id": 1})

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found."


@pytest.mark.anyio
async def test_create_transaction_returns_created_response_and_forwards_payload() -> (
    None
):
    transaction_input_port_stub = _TransactionInputPortStub()
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/transaction",
            json=build_transaction_create_payload(),
        )

    assert response.status_code == 201
    assert response.json() == build_transaction_response()
    assert len(transaction_input_port_stub.create_calls) == 1
    assert transaction_input_port_stub.create_calls[0] == CreateTransactionData(
        effective_at=_build_timestamp(11),
        title="Airline tickets",
        description="Family vacation purchase",
        status=TransactionStatus.PENDING,
        entries=(
            NewEntry(
                ledger_account_id=1,
                amount=Decimal("1200.00"),
                currency_id=1,
                statement_closing_date=None,
                statement_due_date=None,
                entry_tags=(NewEntryTag(tag_id=10), NewEntryTag(tag_id=11)),
            ),
            NewEntry(
                ledger_account_id=2,
                amount=Decimal("-1200.00"),
                currency_id=1,
                statement_closing_date=date(2026, 5, 31),
                statement_due_date=date(2026, 6, 10),
                entry_tags=(),
            ),
        ),
    )


@pytest.mark.anyio
async def test_create_transaction_returns_422_for_business_rule_violations() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.create_error = TransactionEntryCurrencyNotFoundError()
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/transaction",
            json=build_transaction_create_payload(),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Transaction entry currency was not found."


@pytest.mark.anyio
async def test_update_transaction_returns_updated_response() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = (
        _build_transaction_with_entries()
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/transaction",
            params={"id": 1},
            json=build_transaction_update_payload(),
        )

    assert response.status_code == 200
    assert response.json() == build_updated_transaction_response()
    assert transaction_input_port_stub.update_calls[0][0] == 1
    assert transaction_input_port_stub.update_calls[0][1] == UpdateTransactionData(
        effective_at=_build_timestamp(12),
        title="Updated airline tickets",
        description="Updated family vacation purchase",
        entries=(
            NewEntry(
                ledger_account_id=1,
                amount=Decimal("1300.00"),
                currency_id=1,
                statement_closing_date=None,
                statement_due_date=None,
                entry_tags=(NewEntryTag(tag_id=11),),
            ),
            NewEntry(
                ledger_account_id=2,
                amount=Decimal("-1300.00"),
                currency_id=1,
                statement_closing_date=date(2026, 5, 31),
                statement_due_date=date(2026, 6, 10),
                entry_tags=(),
            ),
        ),
    )


@pytest.mark.anyio
async def test_update_transaction_returns_409_when_transaction_is_not_pending() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = _build_transaction_with_entries(
        status=TransactionStatus.POSTED,
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/transaction",
            params={"id": 1},
            json=build_transaction_update_payload(),
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Transaction must be pending."


@pytest.mark.anyio
async def test_update_transaction_returns_422_for_business_rule_violations() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = (
        _build_transaction_with_entries()
    )
    transaction_input_port_stub.update_error = TransactionEntriesMustBalanceError()
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/transaction",
            params={"id": 1},
            json=build_transaction_update_payload(),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Transaction entries must balance to zero."


@pytest.mark.anyio
async def test_post_transaction_returns_posted_response() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = (
        _build_transaction_with_entries()
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/transaction/post", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == build_posted_transaction_response()
    assert transaction_input_port_stub.post_calls == [1]


@pytest.mark.anyio
async def test_post_transaction_returns_409_when_status_transition_is_not_allowed() -> (
    None
):
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = _build_transaction_with_entries(
        status=TransactionStatus.POSTED,
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/transaction/post", params={"id": 1})

    assert response.status_code == 409
    assert response.json()["detail"] == "Transaction status transition is not allowed."


@pytest.mark.anyio
async def test_void_transaction_returns_voided_response() -> None:
    transaction_input_port_stub = _TransactionInputPortStub()
    transaction_input_port_stub.transactions_by_id[1] = (
        _build_transaction_with_entries()
    )
    app = _create_test_app(transaction_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/transaction/void", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == build_voided_transaction_response()
    assert transaction_input_port_stub.void_calls == [1]


@pytest.mark.anyio
async def test_void_transaction_returns_404_when_transaction_does_not_exist() -> None:
    app = _create_test_app(_TransactionInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/transaction/void", params={"id": 1})

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found."

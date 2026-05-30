from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.ledger_account_route import create_router
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountBalance,
    LedgerAccountInstrumentKind,
    LedgerAccountInstrumentKindNotAllowedError,
    LedgerAccountNotFoundError,
    LedgerAccountType,
    UpdateLedgerAccountData,
)
from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


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


class _LedgerAccountInputPortStub:
    def __init__(self) -> None:
        self.ledger_accounts_by_id: dict[int, LedgerAccount] = {}
        self.soft_deleted_ledger_account_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_ledger_account_queries: list[ListQuery] = []
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self._next_ledger_account_id = 1

    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]:
        self.list_ledger_account_queries.append(list_query)
        active_ledger_accounts = [
            ledger_account
            for ledger_account_id, ledger_account in self.ledger_accounts_by_id.items()
            if ledger_account_id not in self.soft_deleted_ledger_account_ids
        ]
        active_ledger_accounts.sort(
            key=lambda ledger_account: (ledger_account.title, ledger_account.id),
        )
        return Page[LedgerAccount](
            items=active_ledger_accounts[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_ledger_accounts),
        )

    async def get_ledger_account(self, ledger_account_id: int) -> LedgerAccount:
        if (
            ledger_account_id in self.soft_deleted_ledger_account_ids
            or ledger_account_id not in self.ledger_accounts_by_id
        ):
            raise LedgerAccountNotFoundError()

        return self.ledger_accounts_by_id[ledger_account_id]

    async def create_ledger_account(
        self,
        data: CreateLedgerAccountData,
    ) -> LedgerAccount:
        if self.create_error is not None:
            raise self.create_error

        ledger_account = LedgerAccount(
            id=self._next_ledger_account_id,
            title=data.title,
            type=data.type,
            instrument_kind=data.instrument_kind,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.ledger_accounts_by_id[ledger_account.id] = ledger_account
        self._next_ledger_account_id += 1
        return ledger_account

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount:
        if self.update_error is not None:
            raise self.update_error

        current = await self.get_ledger_account(ledger_account_id)
        updated = LedgerAccount(
            id=current.id,
            title=data.title,
            type=data.type,
            instrument_kind=data.instrument_kind,
            balances=current.balances,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.ledger_accounts_by_id[ledger_account_id] = updated
        return updated

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((ledger_account_id, hard_delete))
        if ledger_account_id in self.soft_deleted_ledger_account_ids:
            if hard_delete:
                self.soft_deleted_ledger_account_ids.remove(ledger_account_id)
                self.ledger_accounts_by_id.pop(ledger_account_id, None)
                return
            raise LedgerAccountNotFoundError()
        if ledger_account_id not in self.ledger_accounts_by_id:
            raise LedgerAccountNotFoundError()
        if hard_delete:
            self.ledger_accounts_by_id.pop(ledger_account_id, None)
            return
        self.soft_deleted_ledger_account_ids.add(ledger_account_id)


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
    assert response.json() == {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "title": "Main Account",
        "type": "asset",
        "instrument_kind": "bank_account",
        "balances": [
            {
                "currency_id": 1,
                "current_balance": "100.00",
                "future_balance": "150.00",
            },
        ],
    }


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
    assert response.json() == {
        "items": [
            {
                "id": 1,
                "created_at": "2026-05-02T00:00:00.000Z",
                "updated_at": "2026-05-02T00:00:00.000Z",
                "title": "Credit Card",
                "type": "liability",
                "instrument_kind": "credit_card",
                "balances": [
                    {
                        "currency_id": 2,
                        "current_balance": "-2500.00",
                        "future_balance": "-2750.00",
                    },
                ],
            },
            {
                "id": 2,
                "created_at": "2026-05-01T00:00:00.000Z",
                "updated_at": "2026-05-01T00:00:00.000Z",
                "title": "Main Account",
                "type": "asset",
                "instrument_kind": "bank_account",
                "balances": [],
            },
        ],
        "offset": 0,
        "limit": 10,
        "total": 2,
    }
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
            json={
                "title": "Main Account",
                "type": "asset",
                "instrument_kind": "bank_account",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "title": "Main Account",
        "type": "asset",
        "instrument_kind": "bank_account",
        "balances": [],
    }


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
    assert response.json()["instrument_kind"] is None


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
            json={
                "title": "Bad Expense",
                "type": "expense",
                "instrument_kind": "wallet",
            },
        )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Ledger account instrument kind is not allowed for the provided ledger account type."
    )


@pytest.mark.anyio
async def test_update_ledger_account_returns_404_for_missing_ledger_account() -> None:
    app = _create_test_app(_LedgerAccountInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/ledger-account",
            params={"id": 1},
            json={
                "title": "Credit Card",
                "type": "liability",
                "instrument_kind": "credit_card",
            },
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
            json={
                "title": "Bad Expense",
                "type": "expense",
                "instrument_kind": "wallet",
            },
        )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Ledger account instrument kind is not allowed for the provided ledger account type."
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

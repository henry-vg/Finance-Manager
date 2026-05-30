from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.transaction_route import create_router
from src.core.domain.transaction import (
    CreateTransactionData,
    Entry,
    EntryTag,
    EntryWithTags,
    NewEntry,
    NewEntryTag,
    Transaction,
    TransactionEntriesMustBalanceError,
    TransactionEntryCurrencyNotFoundError,
    TransactionMustBePendingError,
    TransactionNotFoundError,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
    TransactionWithEntries,
    UpdateTransactionData,
)


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def _build_create_payload() -> dict[str, object]:
    return {
        "effective_at": "2026-05-11T00:00:00.000Z",
        "title": "Airline tickets",
        "description": "Family vacation purchase",
        "status": "pending",
        "entries": [
            {
                "ledger_account_id": 1,
                "amount": "1200.00",
                "currency_id": 1,
                "statement_closing_date": None,
                "statement_due_date": None,
                "entry_tags": [{"tag_id": 10}, {"tag_id": 11}],
            },
            {
                "ledger_account_id": 2,
                "amount": "-1200.00",
                "currency_id": 1,
                "statement_closing_date": "2026-05-31",
                "statement_due_date": "2026-06-10",
                "entry_tags": [],
            },
        ],
    }


def _build_update_payload() -> dict[str, object]:
    return {
        "effective_at": "2026-05-12T00:00:00.000Z",
        "title": "Updated airline tickets",
        "description": "Updated family vacation purchase",
        "entries": [
            {
                "ledger_account_id": 1,
                "amount": "1300.00",
                "currency_id": 1,
                "statement_closing_date": None,
                "statement_due_date": None,
                "entry_tags": [{"tag_id": 11}],
            },
            {
                "ledger_account_id": 2,
                "amount": "-1300.00",
                "currency_id": 1,
                "statement_closing_date": "2026-05-31",
                "statement_due_date": "2026-06-10",
                "entry_tags": [],
            },
        ],
    }


def _build_transaction_response_payload(
    *,
    transaction_id: int = 1,
    title: str = "Airline tickets",
    description: str | None = "Family vacation purchase",
    status: str = "pending",
    effective_at: str = "2026-05-11T00:00:00.000Z",
    transaction_updated_at: str = "2026-05-01T00:00:00.000Z",
    entry_one_amount: str = "1200.00",
    entry_two_amount: str = "-1200.00",
    entry_tags: list[dict[str, int]] | None = None,
    entry_updated_at: str = "2026-05-01T00:00:00.000Z",
) -> dict[str, object]:
    if entry_tags is None:
        entry_tags = [
            {"entry_id": 100, "tag_id": 10},
            {"entry_id": 100, "tag_id": 11},
        ]

    return {
        "id": transaction_id,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": transaction_updated_at,
        "effective_at": effective_at,
        "title": title,
        "description": description,
        "status": status,
        "entries": [
            {
                "entry": {
                    "id": 100,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": entry_updated_at,
                    "transaction_id": transaction_id,
                    "ledger_account_id": 1,
                    "amount": entry_one_amount,
                    "currency_id": 1,
                    "statement_closing_date": None,
                    "statement_due_date": None,
                },
                "entry_tags": entry_tags,
            },
            {
                "entry": {
                    "id": 101,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": entry_updated_at,
                    "transaction_id": transaction_id,
                    "ledger_account_id": 2,
                    "amount": entry_two_amount,
                    "currency_id": 1,
                    "statement_closing_date": "2026-05-31",
                    "statement_due_date": "2026-06-10",
                },
                "entry_tags": [],
            },
        ],
    }


def _build_transaction_with_entries(
    *,
    transaction_id: int = 1,
    title: str = "Airline tickets",
    description: str | None = "Family vacation purchase",
    status: TransactionStatus = TransactionStatus.PENDING,
    effective_at: datetime | None = None,
    transaction_updated_at: datetime | None = None,
    entry_one_amount: Decimal = Decimal("1200.00"),
    entry_two_amount: Decimal = Decimal("-1200.00"),
    first_entry_tag_ids: tuple[int, ...] = (10, 11),
    entry_updated_at: datetime | None = None,
) -> TransactionWithEntries:
    effective_at = effective_at or _build_timestamp(11)
    transaction_updated_at = transaction_updated_at or _build_timestamp(1)
    entry_updated_at = entry_updated_at or _build_timestamp(1)

    return TransactionWithEntries(
        transaction=Transaction(
            id=transaction_id,
            created_at=_build_timestamp(1),
            updated_at=transaction_updated_at,
            effective_at=effective_at,
            title=title,
            description=description,
            status=status,
        ),
        entries=(
            EntryWithTags(
                entry=Entry(
                    id=100,
                    created_at=_build_timestamp(1),
                    updated_at=entry_updated_at,
                    transaction_id=transaction_id,
                    ledger_account_id=1,
                    amount=entry_one_amount,
                    currency_id=1,
                    statement_closing_date=None,
                    statement_due_date=None,
                ),
                entry_tags=tuple(
                    EntryTag(entry_id=100, tag_id=tag_id)
                    for tag_id in first_entry_tag_ids
                ),
            ),
            EntryWithTags(
                entry=Entry(
                    id=101,
                    created_at=_build_timestamp(1),
                    updated_at=entry_updated_at,
                    transaction_id=transaction_id,
                    ledger_account_id=2,
                    amount=entry_two_amount,
                    currency_id=1,
                    statement_closing_date=date(2026, 5, 31),
                    statement_due_date=date(2026, 6, 10),
                ),
                entry_tags=(),
            ),
        ),
    )


class _TransactionInputPortStub:
    def __init__(self) -> None:
        self.transactions_by_id: dict[int, TransactionWithEntries] = {}
        self.create_calls: list[CreateTransactionData] = []
        self.update_calls: list[tuple[int, UpdateTransactionData]] = []
        self.post_calls: list[int] = []
        self.void_calls: list[int] = []
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self.post_error: Exception | None = None
        self.void_error: Exception | None = None
        self._next_transaction_id = 1

    async def get_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        transaction = self.transactions_by_id.get(transaction_id)

        if transaction is None:
            raise TransactionNotFoundError()

        return transaction

    async def create_transaction(
        self,
        data: CreateTransactionData,
    ) -> TransactionWithEntries:
        self.create_calls.append(data)

        if self.create_error is not None:
            raise self.create_error

        transaction = _build_transaction_with_entries(
            transaction_id=self._next_transaction_id,
            title=data.title,
            description=data.description,
            status=data.status,
            effective_at=data.effective_at,
            entry_one_amount=data.entries[0].amount,
            entry_two_amount=data.entries[1].amount,
            first_entry_tag_ids=tuple(
                entry_tag.tag_id for entry_tag in data.entries[0].entry_tags
            ),
        )
        self.transactions_by_id[transaction.transaction.id] = transaction
        self._next_transaction_id += 1
        return transaction

    async def update_transaction(
        self,
        transaction_id: int,
        data: UpdateTransactionData,
    ) -> TransactionWithEntries:
        self.update_calls.append((transaction_id, data))

        if self.update_error is not None:
            raise self.update_error

        current = await self.get_transaction(transaction_id)

        if current.transaction.status != TransactionStatus.PENDING:
            raise TransactionMustBePendingError()

        updated = _build_transaction_with_entries(
            transaction_id=transaction_id,
            title=data.title,
            description=data.description,
            status=current.transaction.status,
            effective_at=data.effective_at,
            transaction_updated_at=_build_timestamp(2),
            entry_one_amount=data.entries[0].amount,
            entry_two_amount=data.entries[1].amount,
            first_entry_tag_ids=tuple(
                entry_tag.tag_id for entry_tag in data.entries[0].entry_tags
            ),
            entry_updated_at=_build_timestamp(2),
        )
        self.transactions_by_id[transaction_id] = updated
        return updated

    async def post_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        self.post_calls.append(transaction_id)

        if self.post_error is not None:
            raise self.post_error

        current = await self.get_transaction(transaction_id)

        if current.transaction.status != TransactionStatus.PENDING:
            raise TransactionStatusTransitionNotAllowedError()

        posted = _build_transaction_with_entries(
            transaction_id=transaction_id,
            title=current.transaction.title,
            description=current.transaction.description,
            status=TransactionStatus.POSTED,
            effective_at=current.transaction.effective_at,
            transaction_updated_at=_build_timestamp(2),
            entry_one_amount=current.entries[0].entry.amount,
            entry_two_amount=current.entries[1].entry.amount,
            first_entry_tag_ids=tuple(
                entry_tag.tag_id for entry_tag in current.entries[0].entry_tags
            ),
            entry_updated_at=current.entries[0].entry.updated_at,
        )
        self.transactions_by_id[transaction_id] = posted
        return posted

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        self.void_calls.append(transaction_id)

        if self.void_error is not None:
            raise self.void_error

        current = await self.get_transaction(transaction_id)

        if current.transaction.status != TransactionStatus.PENDING:
            raise TransactionStatusTransitionNotAllowedError()

        voided = _build_transaction_with_entries(
            transaction_id=transaction_id,
            title=current.transaction.title,
            description=current.transaction.description,
            status=TransactionStatus.VOIDED,
            effective_at=current.transaction.effective_at,
            transaction_updated_at=_build_timestamp(2),
            entry_one_amount=current.entries[0].entry.amount,
            entry_two_amount=current.entries[1].entry.amount,
            first_entry_tag_ids=tuple(
                entry_tag.tag_id for entry_tag in current.entries[0].entry_tags
            ),
            entry_updated_at=current.entries[0].entry.updated_at,
        )
        self.transactions_by_id[transaction_id] = voided
        return voided


def _create_test_app(
    transaction_input_port: _TransactionInputPortStub,
) -> FastAPI:
    app = FastAPI()
    app.include_router(create_router(transaction_input_port=transaction_input_port))
    return app


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
    assert response.json() == _build_transaction_response_payload()


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
        response = await client.post("/transaction", json=_build_create_payload())

    assert response.status_code == 201
    assert response.json() == _build_transaction_response_payload()
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
        response = await client.post("/transaction", json=_build_create_payload())

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
            json=_build_update_payload(),
        )

    assert response.status_code == 200
    assert response.json() == _build_transaction_response_payload(
        title="Updated airline tickets",
        description="Updated family vacation purchase",
        effective_at="2026-05-12T00:00:00.000Z",
        transaction_updated_at="2026-05-02T00:00:00.000Z",
        entry_one_amount="1300.00",
        entry_two_amount="-1300.00",
        entry_tags=[{"entry_id": 100, "tag_id": 11}],
        entry_updated_at="2026-05-02T00:00:00.000Z",
    )
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
            json=_build_update_payload(),
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
            json=_build_update_payload(),
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
    assert response.json() == _build_transaction_response_payload(
        status="posted",
        transaction_updated_at="2026-05-02T00:00:00.000Z",
    )
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
    assert response.json() == _build_transaction_response_payload(
        status="voided",
        transaction_updated_at="2026-05-02T00:00:00.000Z",
    )
    assert transaction_input_port_stub.void_calls == [1]


@pytest.mark.anyio
async def test_void_transaction_returns_404_when_transaction_does_not_exist() -> None:
    app = _create_test_app(_TransactionInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/transaction/void", params={"id": 1})

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found."

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from src.adapters.input.api.schemas.transaction_schema import (
    CreateTransactionRequest,
    TransactionEntryRequest,
    TransactionEntryResponse,
    TransactionEntryTagRequest,
    TransactionEntryTagResponse,
    TransactionEntryWithTagsResponse,
    TransactionResponse,
    TransactionStatusSchema,
    TransactionSummaryResponse,
)


def test_create_transaction_request_parses_nested_entries() -> None:
    payload = CreateTransactionRequest.model_validate(
        {
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
                    "entry_tags": [{"tag_id": 10}],
                },
            ],
        },
    )

    assert payload.status is TransactionStatusSchema.PENDING
    assert payload.entries == (
        TransactionEntryRequest(
            ledger_account_id=1,
            amount=Decimal("1200.00"),
            currency_id=1,
            statement_closing_date=None,
            statement_due_date=None,
            entry_tags=(TransactionEntryTagRequest(tag_id=10),),
        ),
    )


def test_transaction_response_serializes_nested_dates_datetimes_and_decimals() -> None:
    response = TransactionResponse(
        id=1,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
        effective_at=datetime(2026, 5, 11, tzinfo=UTC),
        title="Airline tickets",
        description="Family vacation purchase",
        status=TransactionStatusSchema.POSTED,
        entries=(
            TransactionEntryWithTagsResponse(
                entry=TransactionEntryResponse(
                    id=100,
                    created_at=datetime(2026, 5, 1, tzinfo=UTC),
                    updated_at=datetime(2026, 5, 2, tzinfo=UTC),
                    transaction_id=1,
                    ledger_account_id=2,
                    amount_in_dollars=Decimal("-240.00"),
                    currency_id=1,
                    planned_exchange_rate_to_dollars=Decimal("0.20"),
                    posting_exchange_rate_to_dollars=Decimal("0.20"),
                    statement_closing_date=date(2026, 5, 31),
                    statement_due_date=date(2026, 6, 10),
                ),
                entry_tags=(
                    TransactionEntryTagResponse(
                        entry_id=100,
                        tag_id=10,
                    ),
                ),
            ),
        ),
    )

    payload = json.loads(response.model_dump_json())

    assert payload == {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
        "effective_at": "2026-05-11T00:00:00.000Z",
        "title": "Airline tickets",
        "description": "Family vacation purchase",
        "status": "posted",
        "entries": [
            {
                "entry": {
                    "id": 100,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": "2026-05-02T00:00:00.000Z",
                    "transaction_id": 1,
                    "ledger_account_id": 2,
                    "amount_in_dollars": "-240.00",
                    "currency_id": 1,
                    "planned_exchange_rate_to_dollars": "0.20",
                    "posting_exchange_rate_to_dollars": "0.20",
                    "statement_closing_date": "2026-05-31",
                    "statement_due_date": "2026-06-10",
                },
                "entry_tags": [{"entry_id": 100, "tag_id": 10}],
            },
        ],
    }


def test_transaction_summary_response_serializes_timestamps() -> None:
    response = TransactionSummaryResponse(
        id=1,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
        effective_at=datetime(2026, 5, 11, tzinfo=UTC),
        title="Airline tickets",
        description="Family vacation purchase",
        status=TransactionStatusSchema.PENDING,
    )

    payload = json.loads(response.model_dump_json())

    assert payload == {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
        "effective_at": "2026-05-11T00:00:00.000Z",
        "title": "Airline tickets",
        "description": "Family vacation purchase",
        "status": "pending",
    }

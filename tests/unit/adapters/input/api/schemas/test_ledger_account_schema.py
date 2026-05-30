import json
from datetime import UTC, datetime
from decimal import Decimal

from src.adapters.input.api.schemas.ledger_account_schema import (
    CreateLedgerAccountRequest,
    LedgerAccountBalanceResponse,
    LedgerAccountInstrumentKindSchema,
    LedgerAccountResponse,
    LedgerAccountTypeSchema,
)


def test_create_ledger_account_request_accepts_instrument_kind() -> None:
    payload = CreateLedgerAccountRequest(
        title="Main Account",
        type=LedgerAccountTypeSchema.ASSET,
        instrument_kind=LedgerAccountInstrumentKindSchema.BANK_ACCOUNT,
    )

    assert payload.instrument_kind == LedgerAccountInstrumentKindSchema.BANK_ACCOUNT


def test_create_ledger_account_request_allows_missing_instrument_kind() -> None:
    payload = CreateLedgerAccountRequest(
        title="Salary",
        type=LedgerAccountTypeSchema.INCOME,
    )

    assert payload.instrument_kind is None


def test_ledger_account_response_serializes_balances() -> None:
    response = LedgerAccountResponse(
        id=1,
        title="Main Account",
        type=LedgerAccountTypeSchema.ASSET,
        instrument_kind=LedgerAccountInstrumentKindSchema.BANK_ACCOUNT,
        balances=(
            LedgerAccountBalanceResponse(
                currency_id=1,
                current_balance=Decimal("100.00"),
                future_balance=Decimal("150.00"),
            ),
        ),
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    payload = json.loads(response.model_dump_json())

    assert payload["balances"] == [
        {
            "currency_id": 1,
            "current_balance": "100.00",
            "future_balance": "150.00",
        },
    ]


def test_ledger_account_response_serializes_null_instrument_kind() -> None:
    response = LedgerAccountResponse(
        id=1,
        title="Salary",
        type=LedgerAccountTypeSchema.INCOME,
        instrument_kind=None,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    payload = json.loads(response.model_dump_json())

    assert payload["instrument_kind"] is None
    assert payload["balances"] == []

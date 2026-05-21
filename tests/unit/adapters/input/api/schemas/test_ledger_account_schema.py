import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.adapters.input.api.schemas.ledger_account_schema import (
    CreateLedgerAccountRequest,
    LedgerAccountKindSchema,
    LedgerAccountResponse,
    LedgerAccountTypeSchema,
)


def test_create_ledger_account_request_accepts_three_letter_currency_code() -> None:
    payload = CreateLedgerAccountRequest(
        title="Main Account",
        type=LedgerAccountTypeSchema.ASSET,
        kind=LedgerAccountKindSchema.BANK_ACCOUNT,
        currency_iso_code="brl",
    )

    assert payload.currency_iso_code == "brl"


def test_create_ledger_account_request_rejects_invalid_currency_code_length() -> None:
    with pytest.raises(ValidationError):
        CreateLedgerAccountRequest(
            title="Main Account",
            type=LedgerAccountTypeSchema.ASSET,
            kind=LedgerAccountKindSchema.BANK_ACCOUNT,
            currency_iso_code="BR",
        )


def test_ledger_account_response_serializes_currency_code_as_string() -> None:
    response = LedgerAccountResponse(
        id=1,
        title="Main Account",
        type=LedgerAccountTypeSchema.ASSET,
        kind=LedgerAccountKindSchema.BANK_ACCOUNT,
        currency_iso_code="BRL",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    payload = json.loads(response.model_dump_json())

    assert payload["currency_iso_code"] == "BRL"

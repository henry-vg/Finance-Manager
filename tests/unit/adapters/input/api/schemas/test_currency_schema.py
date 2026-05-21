import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.adapters.input.api.schemas.currency_schema import (
    CreateCurrencyRequest,
    CurrencyResponse,
)


def test_create_currency_request_accepts_valid_payload() -> None:
    payload = CreateCurrencyRequest(
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
    )

    assert payload.iso_code == "BRL"


def test_create_currency_request_rejects_invalid_iso_numeric() -> None:
    with pytest.raises(ValidationError):
        CreateCurrencyRequest(
            iso_code="BRL",
            iso_numeric="98",
            name="Real",
            symbol="R$",
            decimal_places=2,
        )


def test_currency_response_serializes_storage_decimal_places() -> None:
    response = CurrencyResponse(
        id=1,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        storage_decimal_places=3,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    payload = json.loads(response.model_dump_json())

    assert payload["storage_decimal_places"] == 3

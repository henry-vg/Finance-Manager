from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.core.domain.currency import (
    DOLLAR_ISO_CODE,
    CreateCurrencyData,
    Currency,
    CurrencyChanges,
    CurrencyDataValidationError,
    CurrencyISOCodeConflictError,
    CurrencyNotFoundError,
    CurrencySortableField,
    ExchangeRateQuote,
    NewCurrency,
    UpdateCurrencyData,
)


def _timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def test_currency_keeps_persisted_fields_and_computes_storage_decimal_places() -> None:
    currency = Currency(
        id=1,
        iso_code="BRL",
        iso_numeric="986",
        name="Real",
        symbol="R$",
        decimal_places=2,
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
    )

    assert currency.id == 1
    assert currency.iso_code == "BRL"
    assert currency.iso_numeric == "986"
    assert currency.name == "Real"
    assert currency.symbol == "R$"
    assert currency.decimal_places == 2
    assert currency.created_at == _timestamp(1)
    assert currency.updated_at == _timestamp(2)
    assert currency.storage_decimal_places == 3


@pytest.mark.parametrize(
    "factory",
    [NewCurrency, CurrencyChanges, CreateCurrencyData, UpdateCurrencyData],
)
def test_currency_write_models_keep_currency_fields(
    factory: type[
        NewCurrency | CurrencyChanges | CreateCurrencyData | UpdateCurrencyData
    ],
) -> None:
    currency_data = factory(
        iso_code="USD",
        iso_numeric="840",
        name="US Dollar",
        symbol="$",
        decimal_places=2,
    )

    assert currency_data.iso_code == "USD"
    assert currency_data.iso_numeric == "840"
    assert currency_data.name == "US Dollar"
    assert currency_data.symbol == "$"
    assert currency_data.decimal_places == 2


def test_exchange_rate_quote_keeps_rate_direction_and_timestamp() -> None:
    quote = ExchangeRateQuote(
        currency_iso_code="EUR",
        rate_to_dollars=Decimal("1.17"),
        quoted_at=_timestamp(3),
    )

    assert quote.currency_iso_code == "EUR"
    assert quote.rate_to_dollars == Decimal("1.17")
    assert quote.quoted_at == _timestamp(3)


def test_currency_sortable_field_exposes_all_public_members() -> None:
    assert tuple(CurrencySortableField.__members__) == (
        "ID",
        "CREATED_AT",
        "UPDATED_AT",
        "ISO_CODE",
        "ISO_NUMERIC",
        "NAME",
        "SYMBOL",
        "DECIMAL_PLACES",
    )


def test_dollar_iso_code_constant_is_usd() -> None:
    assert DOLLAR_ISO_CODE == "USD"


@pytest.mark.parametrize(
    "error_type",
    [CurrencyNotFoundError, CurrencyISOCodeConflictError, CurrencyDataValidationError],
)
def test_currency_errors_are_domain_exceptions(
    error_type: type[Exception],
) -> None:
    assert isinstance(error_type(), Exception)

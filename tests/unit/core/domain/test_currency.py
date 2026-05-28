from datetime import UTC, datetime

from src.core.domain.currency import DOLLAR_ISO_CODE, Currency


def _timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def test_currency_storage_decimal_places_adds_one_guard_digit() -> None:
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

    assert currency.storage_decimal_places == 3


def test_dollar_iso_code_constant_is_usd() -> None:
    assert DOLLAR_ISO_CODE == "USD"

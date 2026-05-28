from datetime import date

import pytest

from src.core.domain.currency import DOLLAR_ISO_CODE
from src.infra.exchange_rate import MockExchangeRateOutputAdapter


@pytest.mark.anyio
async def test_get_exchange_rate_to_dollars_returns_mock_quote() -> None:
    adapter = MockExchangeRateOutputAdapter()

    quote = await adapter.get_exchange_rate_to_dollars("brl")

    assert quote.currency_iso_code == "BRL"
    assert DOLLAR_ISO_CODE == "USD"
    assert str(quote.rate_to_dollars) == "0.20"


@pytest.mark.anyio
async def test_get_exchange_rate_to_dollars_uses_quote_date_at_utc_midnight() -> None:
    adapter = MockExchangeRateOutputAdapter()

    quote = await adapter.get_exchange_rate_to_dollars(
        "eur",
        quote_date=date(2026, 5, 20),
    )

    assert quote.currency_iso_code == "EUR"
    assert quote.quoted_at.isoformat() == "2026-05-20T00:00:00+00:00"


@pytest.mark.anyio
async def test_get_exchange_rate_to_dollars_rejects_unknown_currency() -> None:
    adapter = MockExchangeRateOutputAdapter()

    with pytest.raises(NotImplementedError, match="XAU"):
        await adapter.get_exchange_rate_to_dollars("xau")

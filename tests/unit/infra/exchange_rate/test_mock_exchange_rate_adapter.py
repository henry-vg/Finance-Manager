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

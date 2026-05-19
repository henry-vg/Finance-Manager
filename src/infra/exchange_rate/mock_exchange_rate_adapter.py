from datetime import UTC, date, datetime, time
from decimal import Decimal

from src.core.domain.currency import (
    DOLLAR_ISO_CODE,
    ExchangeRateQuote,
)
from src.core.ports.output.exchange_rate_output_port import ExchangeRateOutputPort


def _normalize_currency_iso_code(
    currency_iso_code: str,
) -> str:
    return currency_iso_code.strip().upper()


def _build_quote_datetime(
    quote_date: date | None,
) -> datetime:
    if quote_date is None:
        return datetime.now(tz=UTC)

    return datetime.combine(quote_date, time.min, tzinfo=UTC)


_MOCK_EXCHANGE_RATES_TO_DOLLARS: dict[str, Decimal] = {
    DOLLAR_ISO_CODE: Decimal("1"),
    "BRL": Decimal("0.20"),
    "EUR": Decimal("1.08"),
    "BTC": Decimal("65000"),
}


class MockExchangeRateOutputAdapter(ExchangeRateOutputPort):
    async def get_exchange_rate_to_dollars(
        self,
        currency_iso_code: str,
        quote_date: date | None = None,
    ) -> ExchangeRateQuote:
        normalized_currency_iso_code = _normalize_currency_iso_code(currency_iso_code)

        # TODO: replace this mock with a real market-data provider adapter.
        rate_to_dollars = _MOCK_EXCHANGE_RATES_TO_DOLLARS.get(
            normalized_currency_iso_code,
        )

        if rate_to_dollars is None:
            raise NotImplementedError(
                "No mock exchange rate configured for "
                f"'{normalized_currency_iso_code}'",
            )

        return ExchangeRateQuote(
            currency_iso_code=normalized_currency_iso_code,
            rate_to_dollars=rate_to_dollars,
            quoted_at=_build_quote_datetime(quote_date),
        )

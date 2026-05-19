from datetime import date
from typing import Protocol

from src.core.domain.currency import ExchangeRateQuote


class ExchangeRateOutputPort(Protocol):
    async def get_exchange_rate_to_dollars(
        self,
        currency_iso_code: str,
        quote_date: date | None = None,
    ) -> ExchangeRateQuote: ...

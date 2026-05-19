from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntEnum

DOLLAR_ISO_CODE = "USD"


class CurrencySortableField(IntEnum):
    ID = 1
    CREATED_AT = 2
    UPDATED_AT = 3
    ISO_CODE = 4
    ISO_NUMERIC = 5
    NAME = 6
    SYMBOL = 7
    DECIMAL_PLACES = 8


@dataclass(frozen=True)
class Currency:
    id: int
    created_at: datetime
    updated_at: datetime
    iso_code: str
    iso_numeric: str
    name: str
    symbol: str
    decimal_places: int

    @property
    def storage_decimal_places(self) -> int:
        return self.decimal_places + 1


@dataclass(frozen=True)
class NewCurrency:
    iso_code: str
    iso_numeric: str
    name: str
    symbol: str
    decimal_places: int


@dataclass(frozen=True)
class CurrencyChanges:
    iso_code: str
    iso_numeric: str
    name: str
    symbol: str
    decimal_places: int


@dataclass(frozen=True)
class CreateCurrencyData:
    iso_code: str
    iso_numeric: str
    name: str
    symbol: str
    decimal_places: int


@dataclass(frozen=True)
class UpdateCurrencyData:
    iso_code: str
    iso_numeric: str
    name: str
    symbol: str
    decimal_places: int


@dataclass(frozen=True)
class ExchangeRateQuote:
    currency_iso_code: str
    rate_to_dollars: Decimal
    quoted_at: datetime


class CurrencyNotFoundError(Exception):
    pass


class CurrencyISOCodeConflictError(Exception):
    pass


class CurrencyDataValidationError(Exception):
    pass

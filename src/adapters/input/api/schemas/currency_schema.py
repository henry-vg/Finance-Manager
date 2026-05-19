from datetime import datetime

from pydantic import Field

from .base import ApiSchemaBase


class CreateCurrencyRequest(ApiSchemaBase):
    iso_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    iso_numeric: str = Field(min_length=3, max_length=3, pattern=r"^[0-9]{3}$")
    name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    decimal_places: int = Field(ge=0)


class UpdateCurrencyRequest(ApiSchemaBase):
    iso_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    iso_numeric: str = Field(min_length=3, max_length=3, pattern=r"^[0-9]{3}$")
    name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    decimal_places: int = Field(ge=0)


class CurrencyResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    iso_code: str
    iso_numeric: str
    name: str
    symbol: str
    decimal_places: int
    storage_decimal_places: int

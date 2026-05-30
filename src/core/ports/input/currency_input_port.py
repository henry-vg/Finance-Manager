from typing import Protocol

from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    UpdateCurrencyData,
)
from src.core.shared import ListQuery, Page


class CurrencyInputPort(Protocol):  # pragma: no cover
    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]: ...

    async def get_currency(
        self,
        currency_id: int,
    ) -> Currency: ...

    async def create_currency(
        self,
        data: CreateCurrencyData,
    ) -> Currency: ...

    async def update_currency(
        self,
        currency_id: int,
        data: UpdateCurrencyData,
    ) -> Currency: ...

    async def delete_currency(
        self,
        currency_id: int,
        hard_delete: bool = False,
    ) -> None: ...

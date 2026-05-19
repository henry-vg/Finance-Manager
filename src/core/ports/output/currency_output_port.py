from typing import Protocol

from src.core.domain.currency import Currency, CurrencyChanges, NewCurrency
from src.core.shared import ListQuery, Page


class CurrencyNotFoundOutputPortError(Exception):
    pass


class CurrencyISOCodeConflictOutputPortError(Exception):
    pass


class CurrencyOutputPort(Protocol):
    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]: ...

    async def get_currency_by_id(
        self,
        currency_id: int,
    ) -> Currency | None: ...

    async def get_currency_by_id_including_deleted(
        self,
        currency_id: int,
    ) -> Currency | None: ...

    async def get_currency_by_iso_code(
        self,
        iso_code: str,
    ) -> Currency | None: ...

    async def create_currency(
        self,
        new_currency: NewCurrency,
    ) -> Currency: ...

    async def update_currency(
        self,
        currency_id: int,
        changes: CurrencyChanges,
    ) -> Currency: ...

    async def soft_delete_currency(
        self,
        currency_id: int,
    ) -> None: ...

    async def hard_delete_currency(
        self,
        currency_id: int,
    ) -> None: ...

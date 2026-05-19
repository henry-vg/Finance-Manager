from datetime import UTC, datetime

from src.core.domain.currency import CreateCurrencyData, Currency, UpdateCurrencyData
from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.shared import ListQuery, Page


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class CurrencyInputPortStub(CurrencyInputPort):
    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]:
        return Page[Currency](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_currency(
        self,
        currency_id: int,
    ) -> Currency:
        return Currency(
            id=currency_id,
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def create_currency(
        self,
        data: CreateCurrencyData,
    ) -> Currency:
        return Currency(
            id=1,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )

    async def update_currency(
        self,
        currency_id: int,
        data: UpdateCurrencyData,
    ) -> Currency:
        return Currency(
            id=currency_id,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def delete_currency(
        self,
        currency_id: int,
        hard_delete: bool = False,
    ) -> None:
        del currency_id
        del hard_delete
        return None

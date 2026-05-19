from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.currency import (
    Currency,
    CurrencyChanges,
    CurrencySortableField,
    NewCurrency,
)
from src.core.ports.output.currency_output_port import (
    CurrencyISOCodeConflictOutputPortError,
    CurrencyNotFoundOutputPortError,
    CurrencyOutputPort,
)
from src.core.shared import ListQuery, Page, SortDirection

from ...integrity import is_unique_violation
from ...listing import build_order_clauses
from .models import CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME, CurrencyRecord

_CURRENCY_LIST_SORT_COLUMNS: dict[CurrencySortableField, Any] = {
    CurrencySortableField.ID: CurrencyRecord.id,
    CurrencySortableField.ISO_CODE: CurrencyRecord.iso_code,
    CurrencySortableField.ISO_NUMERIC: CurrencyRecord.iso_numeric,
    CurrencySortableField.NAME: CurrencyRecord.name,
    CurrencySortableField.SYMBOL: CurrencyRecord.symbol,
    CurrencySortableField.DECIMAL_PLACES: CurrencyRecord.decimal_places,
    CurrencySortableField.CREATED_AT: CurrencyRecord.created_at,
    CurrencySortableField.UPDATED_AT: CurrencyRecord.updated_at,
}


def _to_domain_currency(
    currency_record: CurrencyRecord,
) -> Currency:
    return Currency(
        id=currency_record.id,
        created_at=currency_record.created_at,
        updated_at=currency_record.updated_at,
        iso_code=currency_record.iso_code,
        iso_numeric=currency_record.iso_numeric,
        name=currency_record.name,
        symbol=currency_record.symbol,
        decimal_places=currency_record.decimal_places,
    )


class SQLAlchemyCurrencyOutputAdapter(CurrencyOutputPort):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]:
        statement = (
            select(CurrencyRecord)
            .where(CurrencyRecord.is_deleted.is_(False))
            .order_by(
                *build_order_clauses(
                    sort_terms=list_query.sort,
                    sort_field_enum=CurrencySortableField,
                    sort_columns=_CURRENCY_LIST_SORT_COLUMNS,
                    tie_break_field=CurrencySortableField.ID,
                    tie_break_direction=SortDirection.DESC,
                ),
            )
            .offset(list_query.offset)
            .limit(list_query.limit)
        )
        total_statement = (
            select(func.count())
            .select_from(CurrencyRecord)
            .where(CurrencyRecord.is_deleted.is_(False))
        )

        currency_records = cast(
            list[CurrencyRecord],
            list((await self._session.scalars(statement)).all()),
        )
        total = cast(int, await self._session.scalar(total_statement))

        return Page[Currency](
            items=[
                _to_domain_currency(currency_record=currency_record)
                for currency_record in currency_records
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=total,
        )

    async def get_currency_by_id(
        self,
        currency_id: int,
    ) -> Currency | None:
        currency_record = await self._get_currency_record_by_id(currency_id=currency_id)

        if currency_record is None:
            return None

        return _to_domain_currency(currency_record=currency_record)

    async def get_currency_by_id_including_deleted(
        self,
        currency_id: int,
    ) -> Currency | None:
        currency_record = await self._get_currency_record_by_id(
            currency_id=currency_id,
            include_deleted=True,
        )

        if currency_record is None:
            return None

        return _to_domain_currency(currency_record=currency_record)

    async def get_currency_by_iso_code(
        self,
        iso_code: str,
    ) -> Currency | None:
        currency_record = await self._get_currency_record_by_iso_code(
            iso_code=iso_code,
        )

        if currency_record is None:
            return None

        return _to_domain_currency(currency_record=currency_record)

    async def create_currency(
        self,
        new_currency: NewCurrency,
    ) -> Currency:
        currency_record = CurrencyRecord()
        currency_record.iso_code = new_currency.iso_code
        currency_record.iso_numeric = new_currency.iso_numeric
        currency_record.name = new_currency.name
        currency_record.symbol = new_currency.symbol
        currency_record.decimal_places = new_currency.decimal_places

        self._session.add(currency_record)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            if is_unique_violation(
                exc,
                constraint_name=CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME,
            ):
                raise CurrencyISOCodeConflictOutputPortError() from exc

            raise

        await self._session.refresh(currency_record)

        return _to_domain_currency(currency_record=currency_record)

    async def update_currency(
        self,
        currency_id: int,
        changes: CurrencyChanges,
    ) -> Currency:
        currency_record = await self._get_currency_record_by_id(currency_id=currency_id)

        if currency_record is None:
            raise CurrencyNotFoundOutputPortError()

        currency_record.iso_code = changes.iso_code
        currency_record.iso_numeric = changes.iso_numeric
        currency_record.name = changes.name
        currency_record.symbol = changes.symbol
        currency_record.decimal_places = changes.decimal_places

        try:
            await self._session.flush()
        except IntegrityError as exc:
            if is_unique_violation(
                exc,
                constraint_name=CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME,
            ):
                raise CurrencyISOCodeConflictOutputPortError() from exc

            raise

        await self._session.refresh(currency_record)

        return _to_domain_currency(currency_record=currency_record)

    async def soft_delete_currency(
        self,
        currency_id: int,
    ) -> None:
        currency_record = await self._get_currency_record_by_id(currency_id=currency_id)

        if currency_record is None:
            raise CurrencyNotFoundOutputPortError()

        currency_record.is_deleted = True
        await self._session.flush()

    async def hard_delete_currency(
        self,
        currency_id: int,
    ) -> None:
        currency_record = await self._get_currency_record_by_id(
            currency_id=currency_id,
            include_deleted=True,
        )

        if currency_record is None:
            raise CurrencyNotFoundOutputPortError()

        await self._session.delete(currency_record)
        await self._session.flush()

    async def _get_currency_record_by_id(
        self,
        *,
        currency_id: int,
        include_deleted: bool = False,
    ) -> CurrencyRecord | None:
        statement = select(CurrencyRecord).where(CurrencyRecord.id == currency_id)

        if not include_deleted:
            statement = statement.where(CurrencyRecord.is_deleted.is_(False))

        return cast(CurrencyRecord | None, await self._session.scalar(statement))

    async def _get_currency_record_by_iso_code(
        self,
        *,
        iso_code: str,
    ) -> CurrencyRecord | None:
        statement = select(CurrencyRecord).where(
            CurrencyRecord.iso_code == iso_code,
            CurrencyRecord.is_deleted.is_(False),
        )

        return cast(CurrencyRecord | None, await self._session.scalar(statement))

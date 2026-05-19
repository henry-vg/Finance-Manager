from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.ledger_account import (
    LedgerAccount,
    LedgerAccountChanges,
    LedgerAccountSortableField,
    NewLedgerAccount,
)
from src.core.ports.output.ledger_account_output_port import (
    LedgerAccountNotFoundOutputPortError,
    LedgerAccountOutputPort,
)
from src.core.shared import ListQuery, Page, SortDirection

from ...listing import build_order_clauses
from .models import LedgerAccountRecord

_LEDGER_ACCOUNT_LIST_SORT_COLUMNS: dict[LedgerAccountSortableField, Any] = {
    LedgerAccountSortableField.ID: LedgerAccountRecord.id,
    LedgerAccountSortableField.TITLE: LedgerAccountRecord.title,
    LedgerAccountSortableField.TYPE: LedgerAccountRecord.type,
    LedgerAccountSortableField.KIND: LedgerAccountRecord.kind,
    LedgerAccountSortableField.CURRENCY_ISO_CODE: LedgerAccountRecord.currency_iso_code,
    LedgerAccountSortableField.CREATED_AT: LedgerAccountRecord.created_at,
    LedgerAccountSortableField.UPDATED_AT: LedgerAccountRecord.updated_at,
}


def _to_domain_ledger_account(
    ledger_account_record: LedgerAccountRecord,
) -> LedgerAccount:
    return LedgerAccount(
        id=ledger_account_record.id,
        title=ledger_account_record.title,
        type=ledger_account_record.type,
        kind=ledger_account_record.kind,
        currency_iso_code=ledger_account_record.currency_iso_code,
        created_at=ledger_account_record.created_at,
        updated_at=ledger_account_record.updated_at,
    )


class SQLAlchemyLedgerAccountOutputAdapter(LedgerAccountOutputPort):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]:
        statement = (
            select(LedgerAccountRecord)
            .where(LedgerAccountRecord.is_deleted.is_(False))
            .order_by(
                *build_order_clauses(
                    sort_terms=list_query.sort,
                    sort_field_enum=LedgerAccountSortableField,
                    sort_columns=_LEDGER_ACCOUNT_LIST_SORT_COLUMNS,
                    tie_break_field=LedgerAccountSortableField.ID,
                    tie_break_direction=SortDirection.DESC,
                ),
            )
            .offset(list_query.offset)
            .limit(list_query.limit)
        )
        total_statement = (
            select(func.count())
            .select_from(LedgerAccountRecord)
            .where(LedgerAccountRecord.is_deleted.is_(False))
        )

        ledger_account_records = cast(
            list[LedgerAccountRecord],
            list((await self._session.scalars(statement)).all()),
        )
        total = cast(int, await self._session.scalar(total_statement))

        return Page[LedgerAccount](
            items=[
                _to_domain_ledger_account(
                    ledger_account_record=ledger_account_record,
                )
                for ledger_account_record in ledger_account_records
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=total,
        )

    async def get_ledger_account_by_id(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        ledger_account_record = await self._get_ledger_account_record_by_id(
            ledger_account_id=ledger_account_id,
        )

        if ledger_account_record is None:
            return None

        return _to_domain_ledger_account(
            ledger_account_record=ledger_account_record,
        )

    async def get_ledger_account_by_id_including_deleted(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        ledger_account_record = await self._get_ledger_account_record_by_id(
            ledger_account_id=ledger_account_id,
            include_deleted=True,
        )

        if ledger_account_record is None:
            return None

        return _to_domain_ledger_account(
            ledger_account_record=ledger_account_record,
        )

    async def create_ledger_account(
        self,
        new_ledger_account: NewLedgerAccount,
    ) -> LedgerAccount:
        ledger_account_record = LedgerAccountRecord()
        ledger_account_record.title = new_ledger_account.title
        ledger_account_record.type = new_ledger_account.type
        ledger_account_record.kind = new_ledger_account.kind
        ledger_account_record.currency_iso_code = new_ledger_account.currency_iso_code

        self._session.add(ledger_account_record)
        await self._session.flush()
        await self._session.refresh(ledger_account_record)

        return _to_domain_ledger_account(
            ledger_account_record=ledger_account_record,
        )

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        changes: LedgerAccountChanges,
    ) -> LedgerAccount:
        ledger_account_record = await self._get_ledger_account_record_by_id(
            ledger_account_id=ledger_account_id,
        )

        if ledger_account_record is None:
            raise LedgerAccountNotFoundOutputPortError()

        ledger_account_record.title = changes.title
        ledger_account_record.type = changes.type
        ledger_account_record.kind = changes.kind
        ledger_account_record.currency_iso_code = changes.currency_iso_code

        await self._session.flush()
        await self._session.refresh(ledger_account_record)

        return _to_domain_ledger_account(
            ledger_account_record=ledger_account_record,
        )

    async def soft_delete_ledger_account(
        self,
        ledger_account_id: int,
    ) -> None:
        ledger_account_record = await self._get_ledger_account_record_by_id(
            ledger_account_id=ledger_account_id,
        )

        if ledger_account_record is None:
            raise LedgerAccountNotFoundOutputPortError()

        ledger_account_record.is_deleted = True
        await self._session.flush()

    async def hard_delete_ledger_account(
        self,
        ledger_account_id: int,
    ) -> None:
        ledger_account_record = await self._get_ledger_account_record_by_id(
            ledger_account_id=ledger_account_id,
            include_deleted=True,
        )

        if ledger_account_record is None:
            raise LedgerAccountNotFoundOutputPortError()

        await self._session.delete(ledger_account_record)
        await self._session.flush()

    async def _get_ledger_account_record_by_id(
        self,
        *,
        ledger_account_id: int,
        include_deleted: bool = False,
    ) -> LedgerAccountRecord | None:
        statement = select(LedgerAccountRecord).where(
            LedgerAccountRecord.id == ledger_account_id,
        )

        if not include_deleted:
            statement = statement.where(LedgerAccountRecord.is_deleted.is_(False))

        return cast(
            LedgerAccountRecord | None,
            await self._session.scalar(statement),
        )

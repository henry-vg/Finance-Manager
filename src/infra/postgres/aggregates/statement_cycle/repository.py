from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.statement_cycle import (
    NewStatementCycle,
    StatementCycle,
    StatementCycleChanges,
    StatementCycleSortableField,
)
from src.core.ports.output.statement_cycle_output_port import (
    StatementCycleNotFoundOutputPortError,
    StatementCycleOutputPort,
)
from src.core.shared import ListQuery, Page, SortDirection

from ...listing import build_order_clauses
from .models import StatementCycleRecord

_STATEMENT_CYCLE_LIST_SORT_COLUMNS: dict[StatementCycleSortableField, Any] = {
    StatementCycleSortableField.ID: StatementCycleRecord.id,
    StatementCycleSortableField.LEDGER_ACCOUNT_ID: (
        StatementCycleRecord.ledger_account_id
    ),
    StatementCycleSortableField.CYCLE_START: StatementCycleRecord.cycle_start,
    StatementCycleSortableField.CYCLE_END: StatementCycleRecord.cycle_end,
    StatementCycleSortableField.CLOSING_DATE: StatementCycleRecord.closing_date,
    StatementCycleSortableField.DUE_DATE: StatementCycleRecord.due_date,
    StatementCycleSortableField.CREATED_AT: StatementCycleRecord.created_at,
    StatementCycleSortableField.UPDATED_AT: StatementCycleRecord.updated_at,
}


def _to_domain_statement_cycle(
    statement_cycle_record: StatementCycleRecord,
) -> StatementCycle:
    return StatementCycle(
        id=statement_cycle_record.id,
        ledger_account_id=statement_cycle_record.ledger_account_id,
        cycle_start=statement_cycle_record.cycle_start,
        cycle_end=statement_cycle_record.cycle_end,
        closing_date=statement_cycle_record.closing_date,
        due_date=statement_cycle_record.due_date,
        created_at=statement_cycle_record.created_at,
        updated_at=statement_cycle_record.updated_at,
    )


class SQLAlchemyStatementCycleOutputAdapter(StatementCycleOutputPort):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]:
        statement = (
            select(StatementCycleRecord)
            .where(StatementCycleRecord.is_deleted.is_(False))
            .order_by(
                *build_order_clauses(
                    sort_terms=list_query.sort,
                    sort_field_enum=StatementCycleSortableField,
                    sort_columns=_STATEMENT_CYCLE_LIST_SORT_COLUMNS,
                    tie_break_field=StatementCycleSortableField.ID,
                    tie_break_direction=SortDirection.DESC,
                ),
            )
            .offset(list_query.offset)
            .limit(list_query.limit)
        )
        total_statement = (
            select(func.count())
            .select_from(StatementCycleRecord)
            .where(StatementCycleRecord.is_deleted.is_(False))
        )

        statement_cycle_records = cast(
            list[StatementCycleRecord],
            list((await self._session.scalars(statement)).all()),
        )
        total = cast(int, await self._session.scalar(total_statement))

        return Page[StatementCycle](
            items=[
                _to_domain_statement_cycle(
                    statement_cycle_record=statement_cycle_record,
                )
                for statement_cycle_record in statement_cycle_records
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=total,
        )

    async def get_statement_cycle_by_id(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle | None:
        statement_cycle_record = await self._get_statement_cycle_record_by_id(
            statement_cycle_id=statement_cycle_id,
        )

        if statement_cycle_record is None:
            return None

        return _to_domain_statement_cycle(
            statement_cycle_record=statement_cycle_record,
        )

    async def get_statement_cycle_by_id_including_deleted(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle | None:
        statement_cycle_record = await self._get_statement_cycle_record_by_id(
            statement_cycle_id=statement_cycle_id,
            include_deleted=True,
        )

        if statement_cycle_record is None:
            return None

        return _to_domain_statement_cycle(
            statement_cycle_record=statement_cycle_record,
        )

    async def create_statement_cycle(
        self,
        new_statement_cycle: NewStatementCycle,
    ) -> StatementCycle:
        statement_cycle_record = StatementCycleRecord()
        statement_cycle_record.ledger_account_id = new_statement_cycle.ledger_account_id
        statement_cycle_record.cycle_start = new_statement_cycle.cycle_start
        statement_cycle_record.cycle_end = new_statement_cycle.cycle_end
        statement_cycle_record.closing_date = new_statement_cycle.closing_date
        statement_cycle_record.due_date = new_statement_cycle.due_date

        self._session.add(statement_cycle_record)
        await self._session.flush()
        await self._session.refresh(statement_cycle_record)

        return _to_domain_statement_cycle(
            statement_cycle_record=statement_cycle_record,
        )

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        changes: StatementCycleChanges,
    ) -> StatementCycle:
        statement_cycle_record = await self._get_statement_cycle_record_by_id(
            statement_cycle_id=statement_cycle_id,
        )

        if statement_cycle_record is None:
            raise StatementCycleNotFoundOutputPortError()

        statement_cycle_record.ledger_account_id = changes.ledger_account_id
        statement_cycle_record.cycle_start = changes.cycle_start
        statement_cycle_record.cycle_end = changes.cycle_end
        statement_cycle_record.closing_date = changes.closing_date
        statement_cycle_record.due_date = changes.due_date

        await self._session.flush()
        await self._session.refresh(statement_cycle_record)

        return _to_domain_statement_cycle(
            statement_cycle_record=statement_cycle_record,
        )

    async def soft_delete_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> None:
        statement_cycle_record = await self._get_statement_cycle_record_by_id(
            statement_cycle_id=statement_cycle_id,
        )

        if statement_cycle_record is None:
            raise StatementCycleNotFoundOutputPortError()

        statement_cycle_record.is_deleted = True
        await self._session.flush()

    async def hard_delete_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> None:
        statement_cycle_record = await self._get_statement_cycle_record_by_id(
            statement_cycle_id=statement_cycle_id,
            include_deleted=True,
        )

        if statement_cycle_record is None:
            raise StatementCycleNotFoundOutputPortError()

        await self._session.delete(statement_cycle_record)
        await self._session.flush()

    async def _get_statement_cycle_record_by_id(
        self,
        *,
        statement_cycle_id: int,
        include_deleted: bool = False,
    ) -> StatementCycleRecord | None:
        statement = select(StatementCycleRecord).where(
            StatementCycleRecord.id == statement_cycle_id,
        )

        if not include_deleted:
            statement = statement.where(StatementCycleRecord.is_deleted.is_(False))

        return cast(
            StatementCycleRecord | None,
            await self._session.scalar(statement),
        )

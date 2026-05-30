from collections import defaultdict
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.transaction import (
    Entry,
    EntryTag,
    EntryWithTags,
    NewEntry,
    NewTransaction,
    Transaction,
    TransactionChanges,
    TransactionMustBePendingError,
    TransactionSortableField,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
    TransactionWithEntries,
    can_transition_transaction_status,
)
from src.core.ports.output.transaction_output_port import (
    TransactionNotFoundOutputPortError,
    TransactionOutputPort,
)
from src.core.shared import ListQuery, Page, SortDirection

from ...listing import build_order_clauses
from .models import EntryRecord, EntryTagRecord, TransactionRecord


_TRANSACTION_LIST_SORT_COLUMNS: dict[TransactionSortableField, Any] = {
    TransactionSortableField.ID: TransactionRecord.id,
    TransactionSortableField.CREATED_AT: TransactionRecord.created_at,
    TransactionSortableField.UPDATED_AT: TransactionRecord.updated_at,
    TransactionSortableField.EFFECTIVE_AT: TransactionRecord.effective_at,
    TransactionSortableField.TITLE: TransactionRecord.title,
    TransactionSortableField.STATUS: TransactionRecord.status,
}


def _to_domain_transaction(
    transaction_record: TransactionRecord,
) -> Transaction:
    return Transaction(
        id=transaction_record.id,
        created_at=transaction_record.created_at,
        updated_at=transaction_record.updated_at,
        effective_at=transaction_record.effective_at,
        title=transaction_record.title,
        description=transaction_record.description,
        status=transaction_record.status,
    )


def _to_domain_entry(
    entry_record: EntryRecord,
) -> Entry:
    return Entry(
        id=entry_record.id,
        created_at=entry_record.created_at,
        updated_at=entry_record.updated_at,
        transaction_id=entry_record.transaction_id,
        ledger_account_id=entry_record.ledger_account_id,
        amount=entry_record.amount,
        currency_id=entry_record.currency_id,
        statement_closing_date=entry_record.statement_closing_date,
        statement_due_date=entry_record.statement_due_date,
    )


def _to_domain_entry_tag(
    entry_tag_record: EntryTagRecord,
) -> EntryTag:
    return EntryTag(
        entry_id=entry_tag_record.entry_id,
        tag_id=entry_tag_record.tag_id,
    )


def _build_transaction_with_entries(
    *,
    transaction_record: TransactionRecord,
    entry_records: list[EntryRecord],
    entry_tag_records: list[EntryTagRecord],
) -> TransactionWithEntries:
    entry_tags_by_entry_id: dict[int, list[EntryTag]] = defaultdict(list)

    for entry_tag_record in entry_tag_records:
        entry_tags_by_entry_id[entry_tag_record.entry_id].append(
            _to_domain_entry_tag(entry_tag_record),
        )

    return TransactionWithEntries(
        transaction=_to_domain_transaction(transaction_record),
        entries=tuple(
            EntryWithTags(
                entry=_to_domain_entry(entry_record),
                entry_tags=tuple(entry_tags_by_entry_id[entry_record.id]),
            )
            for entry_record in entry_records
        ),
    )


class SQLAlchemyTransactionRepository(TransactionOutputPort):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_transactions(
        self,
        list_query: ListQuery,
    ) -> Page[Transaction]:
        statement = (
            select(TransactionRecord)
            .where(TransactionRecord.is_deleted.is_(False))
            .order_by(
                *build_order_clauses(
                    sort_terms=list_query.sort,
                    sort_field_enum=TransactionSortableField,
                    sort_columns=_TRANSACTION_LIST_SORT_COLUMNS,
                    tie_break_field=TransactionSortableField.ID,
                    tie_break_direction=SortDirection.DESC,
                ),
            )
            .offset(list_query.offset)
            .limit(list_query.limit)
        )
        total_statement = (
            select(func.count())
            .select_from(TransactionRecord)
            .where(TransactionRecord.is_deleted.is_(False))
        )

        transaction_records = cast(
            list[TransactionRecord],
            list((await self._session.scalars(statement)).all()),
        )
        total = cast(int, await self._session.scalar(total_statement))

        return Page[Transaction](
            items=[
                _to_domain_transaction(
                    transaction_record=transaction_record,
                )
                for transaction_record in transaction_records
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=total,
        )

    async def create_transaction(
        self,
        new_transaction: NewTransaction,
    ) -> TransactionWithEntries:
        transaction_record = TransactionRecord()
        transaction_record.status = new_transaction.status
        self._apply_transaction_values(
            transaction_record=transaction_record,
            effective_at=new_transaction.effective_at,
            title=new_transaction.title,
            description=new_transaction.description,
        )

        self._session.add(transaction_record)
        await self._session.flush()
        await self._session.refresh(transaction_record)

        entry_records, entry_tag_records = await self._replace_entries(
            transaction_id=transaction_record.id,
            entries=new_transaction.entries,
        )

        return _build_transaction_with_entries(
            transaction_record=transaction_record,
            entry_records=entry_records,
            entry_tag_records=entry_tag_records,
        )

    async def update_transaction(
        self,
        transaction_id: int,
        changes: TransactionChanges,
    ) -> TransactionWithEntries:
        transaction_record = await self._get_transaction_record_by_id(
            transaction_id=transaction_id,
            for_update=True,
        )

        if transaction_record is None:
            raise TransactionNotFoundOutputPortError()

        if transaction_record.status != TransactionStatus.PENDING:
            raise TransactionMustBePendingError()

        self._apply_transaction_values(
            transaction_record=transaction_record,
            effective_at=changes.effective_at,
            title=changes.title,
            description=changes.description,
        )
        await self._session.flush()

        entry_records, entry_tag_records = await self._replace_entries(
            transaction_id=transaction_id,
            entries=changes.entries,
            purge_existing=True,
        )
        await self._session.refresh(transaction_record)

        return _build_transaction_with_entries(
            transaction_record=transaction_record,
            entry_records=entry_records,
            entry_tag_records=entry_tag_records,
        )

    async def post_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        return await self._transition_transaction_status(
            transaction_id=transaction_id,
            new_status=TransactionStatus.POSTED,
        )

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        return await self._transition_transaction_status(
            transaction_id=transaction_id,
            new_status=TransactionStatus.VOIDED,
        )

    async def _replace_entries(
        self,
        *,
        transaction_id: int,
        entries: tuple[NewEntry, ...],
        purge_existing: bool = False,
    ) -> tuple[list[EntryRecord], list[EntryTagRecord]]:
        if purge_existing:
            existing_entry_records = cast(
                list[EntryRecord],
                list(
                    (
                        await self._session.scalars(
                            select(EntryRecord).where(
                                EntryRecord.transaction_id == transaction_id,
                            ),
                        )
                    ).all(),
                ),
            )

            for entry_record in existing_entry_records:
                await self._session.delete(entry_record)

            if existing_entry_records:
                await self._session.flush()

        entry_records: list[EntryRecord] = []
        entry_tag_records: list[EntryTagRecord] = []

        for new_entry in entries:
            entry_record = EntryRecord()
            entry_record.transaction_id = transaction_id
            entry_record.ledger_account_id = new_entry.ledger_account_id
            entry_record.currency_id = new_entry.currency_id
            entry_record.amount = new_entry.amount
            entry_record.statement_closing_date = new_entry.statement_closing_date
            entry_record.statement_due_date = new_entry.statement_due_date
            self._session.add(entry_record)
            entry_records.append(entry_record)

        if entry_records:
            await self._session.flush()

            for entry_record in entry_records:
                await self._session.refresh(entry_record)

        for entry_record, new_entry in zip(
            entry_records,
            entries,
            strict=True,
        ):
            for new_entry_tag in new_entry.entry_tags:
                entry_tag_record = EntryTagRecord()
                entry_tag_record.entry_id = entry_record.id
                entry_tag_record.tag_id = new_entry_tag.tag_id
                self._session.add(entry_tag_record)
                entry_tag_records.append(entry_tag_record)

        if entry_tag_records:
            await self._session.flush()

        return entry_records, entry_tag_records

    async def get_transaction_by_id(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries | None:
        transaction_record = await self._get_transaction_record_by_id(
            transaction_id=transaction_id,
        )

        if transaction_record is None:
            return None

        entry_records = cast(
            list[EntryRecord],
            list(
                (
                    await self._session.scalars(
                        select(EntryRecord)
                        .where(
                            EntryRecord.transaction_id == transaction_id,
                            EntryRecord.is_deleted.is_(False),
                        )
                        .order_by(EntryRecord.id.asc()),
                    )
                ).all(),
            ),
        )

        if not entry_records:
            return _build_transaction_with_entries(
                transaction_record=transaction_record,
                entry_records=[],
                entry_tag_records=[],
            )

        entry_ids = [entry_record.id for entry_record in entry_records]
        entry_tag_records = cast(
            list[EntryTagRecord],
            list(
                (
                    await self._session.scalars(
                        select(EntryTagRecord)
                        .where(EntryTagRecord.entry_id.in_(entry_ids))
                        .order_by(
                            EntryTagRecord.entry_id.asc(),
                            EntryTagRecord.tag_id.asc(),
                        ),
                    )
                ).all(),
            ),
        )

        return _build_transaction_with_entries(
            transaction_record=transaction_record,
            entry_records=entry_records,
            entry_tag_records=entry_tag_records,
        )

    async def _get_transaction_record_by_id(
        self,
        *,
        transaction_id: int,
        for_update: bool = False,
    ) -> TransactionRecord | None:
        query = select(TransactionRecord).where(
            TransactionRecord.id == transaction_id,
            TransactionRecord.is_deleted.is_(False),
        )

        if for_update:
            query = query.with_for_update()

        return cast(
            TransactionRecord | None,
            await self._session.scalar(query),
        )

    async def _transition_transaction_status(
        self,
        *,
        transaction_id: int,
        new_status: TransactionStatus,
    ) -> TransactionWithEntries:
        transaction_record = await self._get_transaction_record_by_id(
            transaction_id=transaction_id,
            for_update=True,
        )

        if transaction_record is None:
            raise TransactionNotFoundOutputPortError()

        if not can_transition_transaction_status(
            current_status=transaction_record.status,
            new_status=new_status,
        ):
            raise TransactionStatusTransitionNotAllowedError()

        transaction_record.status = new_status
        await self._session.flush()

        transitioned_transaction = await self.get_transaction_by_id(transaction_id)

        if transitioned_transaction is None:
            raise TransactionNotFoundOutputPortError()

        return transitioned_transaction

    def _apply_transaction_values(
        self,
        *,
        transaction_record: TransactionRecord,
        effective_at,
        title: str,
        description: str | None,
    ) -> None:
        transaction_record.effective_at = effective_at
        transaction_record.title = title
        transaction_record.description = description

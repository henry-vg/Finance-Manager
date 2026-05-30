from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.ledger_account import (
    LedgerAccountInstrumentKind,
    LedgerAccountType,
)
from src.core.domain.transaction import (
    TransactionMustBePendingError,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    EntryRecord,
    EntryTagRecord,
    SQLAlchemyCurrencyOutputAdapter,
    SQLAlchemyLedgerAccountOutputAdapter,
    SQLAlchemyTagOutputAdapter,
    TransactionRecord,
)
from src.infra.postgres.aggregates.transaction import SQLAlchemyTransactionRepository
from tests.integration.postgres.helpers.builders import (
    build_new_currency,
    build_new_ledger_account,
    build_new_tag,
    build_new_transaction,
    build_transaction_changes,
)


async def _create_ledger_account(
    session: AsyncSession,
    *,
    title: str,
    type: LedgerAccountType,
    instrument_kind: LedgerAccountInstrumentKind | None,
) -> int:
    adapter = SQLAlchemyLedgerAccountOutputAdapter(session)
    ledger_account = await adapter.create_ledger_account(
        build_new_ledger_account(
            title=title,
            type=type,
            instrument_kind=instrument_kind,
        ),
    )
    return ledger_account.id


async def _create_currency(
    session: AsyncSession,
) -> int:
    adapter = SQLAlchemyCurrencyOutputAdapter(session)
    currency = await adapter.create_currency(
        build_new_currency(
            iso_code="BRL",
            iso_numeric="986",
            name="Brazilian Real",
            symbol="R$",
            decimal_places=2,
        ),
    )
    return currency.id


async def _create_tag(
    session: AsyncSession,
    *,
    title: str,
) -> int:
    adapter = SQLAlchemyTagOutputAdapter(session)
    tag = await adapter.create_tag(build_new_tag(title=title))
    return tag.id


async def _create_transaction_dependencies(
    session: AsyncSession,
    *,
    food_tag_title: str = "Food",
    travel_tag_title: str = "Travel",
) -> tuple[int, int, int, int]:
    await _create_currency(session)
    expense_ledger_account_id = await _create_ledger_account(
        session,
        title="Travel Expense",
        type=LedgerAccountType.EXPENSE,
        instrument_kind=None,
    )
    credit_card_ledger_account_id = await _create_ledger_account(
        session,
        title="Visa Platinum",
        type=LedgerAccountType.LIABILITY,
        instrument_kind=LedgerAccountInstrumentKind.CREDIT_CARD,
    )
    food_tag_id = await _create_tag(session, title=food_tag_title)
    travel_tag_id = await _create_tag(session, title=travel_tag_title)

    return (
        expense_ledger_account_id,
        credit_card_ledger_account_id,
        food_tag_id,
        travel_tag_id,
    )


@pytest.mark.anyio
async def test_create_transaction_persists_transaction_entries_and_entry_tags(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            food_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(session)
        repository = SQLAlchemyTransactionRepository(session)

        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
            ),
        )
        await session.commit()

        transaction_record = await session.get(
            TransactionRecord,
            created_transaction.transaction.id,
        )
        entry_records = list(
            (
                await session.scalars(
                    select(EntryRecord)
                    .where(
                        EntryRecord.transaction_id
                        == created_transaction.transaction.id,
                    )
                    .order_by(EntryRecord.id.asc()),
                )
            ).all(),
        )

    assert created_transaction.transaction.id > 0
    assert transaction_record is not None
    assert len(created_transaction.entries) == 2
    assert [
        entry_tag.tag_id for entry_tag in created_transaction.entries[0].entry_tags
    ] == [food_tag_id, travel_tag_id]
    assert {entry_record.currency_id for entry_record in entry_records} == {1}
    assert created_transaction.entries[1].entry.statement_closing_date == date(
        2026,
        5,
        31,
    )
    assert created_transaction.entries[1].entry.statement_due_date == date(2026, 6, 10)
    assert len(entry_records) == 2

    async with postgres_session_factory() as session:
        persisted_entry_records = list(
            (
                await session.scalars(
                    select(EntryRecord)
                    .where(
                        EntryRecord.transaction_id
                        == created_transaction.transaction.id,
                    )
                    .order_by(EntryRecord.id.asc()),
                )
            ).all(),
        )
        persisted_entry_tag_records = list(
            (
                await session.scalars(
                    select(EntryTagRecord)
                    .where(
                        EntryTagRecord.entry_id == persisted_entry_records[0].id,
                    )
                    .order_by(EntryTagRecord.tag_id.asc()),
                )
            ).all(),
        )

    assert len(persisted_entry_records) == 2
    assert {entry_record.amount for entry_record in persisted_entry_records} == {
        Decimal("1200.00"),
        Decimal("-1200.00"),
    }
    assert {
        entry_tag_record.tag_id for entry_tag_record in persisted_entry_tag_records
    } == {
        food_tag_id,
        travel_tag_id,
    }


@pytest.mark.anyio
async def test_create_transaction_persists_explicit_posted_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            food_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(session)
        repository = SQLAlchemyTransactionRepository(session)

        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.POSTED,
            ),
        )
        await session.commit()

        transaction_record = await session.get(
            TransactionRecord,
            created_transaction.transaction.id,
        )

    assert created_transaction.transaction.status == TransactionStatus.POSTED
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.POSTED


@pytest.mark.anyio
async def test_list_transactions_returns_paginated_transactions_with_total(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            food_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(session)
        repository = SQLAlchemyTransactionRepository(session)

        first_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
            ),
        )
        second_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.POSTED,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)
        page = await repository.list_transactions(
            ListQuery(
                offset=0,
                limit=10,
                sort=(SortTerm(field="id", direction=SortDirection.ASC),),
            ),
        )

    assert [transaction.id for transaction in page.items] == [
        first_transaction.transaction.id,
        second_transaction.transaction.id,
    ]
    assert [transaction.status for transaction in page.items] == [
        TransactionStatus.PENDING,
        TransactionStatus.POSTED,
    ]
    assert page.total == 2


@pytest.mark.anyio
async def test_create_transaction_persists_explicit_voided_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            food_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(session)
        repository = SQLAlchemyTransactionRepository(session)

        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.VOIDED,
            ),
        )
        await session.commit()

        transaction_record = await session.get(
            TransactionRecord,
            created_transaction.transaction.id,
        )

    assert created_transaction.transaction.status == TransactionStatus.VOIDED
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.VOIDED


@pytest.mark.anyio
async def test_get_transaction_by_id_hydrates_private_transaction_graph(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            food_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(session)
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)
        loaded_transaction = await repository.get_transaction_by_id(
            created_transaction.transaction.id,
        )

    assert loaded_transaction is not None
    assert loaded_transaction.transaction.id == created_transaction.transaction.id
    assert loaded_transaction.transaction.title == "Airline tickets"
    assert loaded_transaction.transaction.status == TransactionStatus.PENDING
    assert [
        entry_with_tags.entry.amount for entry_with_tags in loaded_transaction.entries
    ] == [
        Decimal("1200.00"),
        Decimal("-1200.00"),
    ]
    assert [
        entry_tag.tag_id for entry_tag in loaded_transaction.entries[0].entry_tags
    ] == [food_tag_id, travel_tag_id]
    assert loaded_transaction.entries[1].entry.statement_closing_date == date(
        2026,
        5,
        31,
    )
    assert loaded_transaction.entries[1].entry.statement_due_date == date(2026, 6, 10)


@pytest.mark.anyio
async def test_update_transaction_replaces_entries_and_entry_tags(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            groceries_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(
            session,
            food_tag_title="Groceries",
        )
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)
        updated_transaction = await repository.update_transaction(
            created_transaction.transaction.id,
            build_transaction_changes(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                travel_tag_id=travel_tag_id,
            ),
        )
        await session.commit()

    assert updated_transaction.transaction.id == created_transaction.transaction.id
    assert updated_transaction.transaction.status == TransactionStatus.PENDING
    assert updated_transaction.transaction.title == "Hotel reservation"
    assert [
        entry_with_tags.entry.amount for entry_with_tags in updated_transaction.entries
    ] == [
        Decimal("900.00"),
        Decimal("-900.00"),
    ]
    assert [
        entry_tag.tag_id for entry_tag in updated_transaction.entries[0].entry_tags
    ] == [travel_tag_id]

    async with postgres_session_factory() as session:
        persisted_entry_records = list(
            (
                await session.scalars(
                    select(EntryRecord)
                    .where(
                        EntryRecord.transaction_id
                        == created_transaction.transaction.id,
                    )
                    .order_by(EntryRecord.id.asc()),
                )
            ).all(),
        )
        persisted_entry_tag_records = list(
            (
                await session.scalars(
                    select(EntryTagRecord)
                    .where(
                        EntryTagRecord.entry_id == persisted_entry_records[0].id,
                    )
                    .order_by(EntryTagRecord.tag_id.asc()),
                )
            ).all(),
        )

    assert len(persisted_entry_records) == 2
    assert {entry_record.amount for entry_record in persisted_entry_records} == {
        Decimal("900.00"),
        Decimal("-900.00"),
    }
    assert {
        entry_tag_record.tag_id for entry_tag_record in persisted_entry_tag_records
    } == {travel_tag_id}


@pytest.mark.anyio
async def test_update_transaction_rejects_non_pending_transaction(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            groceries_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(
            session,
            food_tag_title="Groceries",
        )
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.POSTED,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)

        with pytest.raises(TransactionMustBePendingError):
            await repository.update_transaction(
                created_transaction.transaction.id,
                build_transaction_changes(
                    expense_ledger_account_id=expense_ledger_account_id,
                    credit_card_ledger_account_id=credit_card_ledger_account_id,
                    travel_tag_id=travel_tag_id,
                ),
            )


@pytest.mark.anyio
async def test_post_transaction_updates_status_without_replacing_entries(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            groceries_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(
            session,
            food_tag_title="Groceries",
        )
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        original_entry_records = list(
            (
                await session.scalars(
                    select(EntryRecord)
                    .where(
                        EntryRecord.transaction_id
                        == created_transaction.transaction.id,
                    )
                    .order_by(EntryRecord.id.asc()),
                )
            ).all(),
        )
        original_entry_ids = [
            entry_record.id for entry_record in original_entry_records
        ]
        repository = SQLAlchemyTransactionRepository(session)

        transitioned_transaction = await repository.post_transaction(
            created_transaction.transaction.id,
        )
        await session.commit()

        transitioned_entry_records = list(
            (
                await session.scalars(
                    select(EntryRecord)
                    .where(
                        EntryRecord.transaction_id
                        == created_transaction.transaction.id,
                    )
                    .order_by(EntryRecord.id.asc()),
                )
            ).all(),
        )
        transaction_record = await session.get(
            TransactionRecord,
            created_transaction.transaction.id,
        )

    assert transitioned_transaction.transaction.status == TransactionStatus.POSTED
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.POSTED
    assert [
        entry_record.id for entry_record in transitioned_entry_records
    ] == original_entry_ids


@pytest.mark.anyio
async def test_void_transaction_rejects_posted_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            groceries_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(
            session,
            food_tag_title="Groceries",
        )
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.POSTED,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)

        with pytest.raises(TransactionStatusTransitionNotAllowedError):
            await repository.void_transaction(created_transaction.transaction.id)


@pytest.mark.anyio
async def test_void_transaction_rejects_terminal_voided_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        (
            expense_ledger_account_id,
            credit_card_ledger_account_id,
            groceries_tag_id,
            travel_tag_id,
        ) = await _create_transaction_dependencies(
            session,
            food_tag_title="Groceries",
        )
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.VOIDED,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)

        with pytest.raises(TransactionStatusTransitionNotAllowedError):
            await repository.void_transaction(created_transaction.transaction.id)

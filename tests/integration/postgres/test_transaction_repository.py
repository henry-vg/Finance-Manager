import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.domain.ledger_account import (
    LedgerAccountKind,
    LedgerAccountType,
    NewLedgerAccount,
)
from src.core.domain.tag import NewTag
from src.core.domain.transaction import (
    NewEntry,
    NewEntryTag,
    NewTransaction,
    TransactionChanges,
    TransactionMustBePendingError,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
)
from src.infra.postgres import (
    EntryRecord,
    EntryTagRecord,
    SQLAlchemyLedgerAccountOutputAdapter,
    SQLAlchemyTagOutputAdapter,
    TransactionRecord,
    create_postgres_engine,
    create_postgres_session_factory,
    dispose_postgres_engine,
    postgres_metadata,
)
from src.infra.postgres.aggregates.transaction import SQLAlchemyTransactionRepository
from src.infra.settings.models import PostgresSettings


def _build_postgres_settings() -> PostgresSettings:
    return PostgresSettings(
        host=os.getenv("CFG_POSTGRES_HOST", "localhost"),
        port=int(os.getenv("CFG_POSTGRES_PORT", "5432")),
        user=os.getenv("CFG_POSTGRES_USER", "finance_manager"),
        password=os.getenv("CFG_POSTGRES_PASSWORD", "finance_manager"),
        database=os.getenv("CFG_POSTGRES_DATABASE", "finance_manager"),
        echo=False,
        pool_size=10,
        max_overflow=20,
    )


async def _prepare_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(postgres_metadata.drop_all)
        await connection.run_sync(postgres_metadata.create_all)


async def _cleanup_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(postgres_metadata.drop_all)


@pytest.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_postgres_engine(_build_postgres_settings())

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        await dispose_postgres_engine(engine)
        pytest.skip(f"Postgres integration database is not available: {exc}")

    await _prepare_database(engine)

    try:
        yield create_postgres_session_factory(engine)
    finally:
        await _cleanup_database(engine)
        await dispose_postgres_engine(engine)


async def _create_ledger_account(
    session: AsyncSession,
    *,
    title: str,
    type: LedgerAccountType,
    kind: LedgerAccountKind,
) -> int:
    adapter = SQLAlchemyLedgerAccountOutputAdapter(session)
    ledger_account = await adapter.create_ledger_account(
        NewLedgerAccount(
            title=title,
            type=type,
            kind=kind,
            currency_iso_code="BRL",
        ),
    )
    return ledger_account.id


async def _create_tag(
    session: AsyncSession,
    *,
    title: str,
) -> int:
    adapter = SQLAlchemyTagOutputAdapter(session)
    tag = await adapter.create_tag(NewTag(title=title))
    return tag.id


def _build_new_transaction(
    *,
    expense_ledger_account_id: int,
    credit_card_ledger_account_id: int,
    food_tag_id: int,
    travel_tag_id: int,
    status: TransactionStatus = TransactionStatus.PENDING,
) -> NewTransaction:
    return NewTransaction(
        effective_at=datetime(2026, 5, 11, 14, 30, tzinfo=UTC),
        title="Airline tickets",
        description="Family vacation purchase",
        status=status,
        currency="BRL",
        entries=(
            NewEntry(
                ledger_account_id=expense_ledger_account_id,
                amount=Decimal("1200.00"),
                statement_closing_date=None,
                statement_due_date=None,
                entry_tags=(
                    NewEntryTag(tag_id=food_tag_id),
                    NewEntryTag(tag_id=travel_tag_id),
                ),
            ),
            NewEntry(
                ledger_account_id=credit_card_ledger_account_id,
                amount=Decimal("-1200.00"),
                statement_closing_date=date(2026, 5, 31),
                statement_due_date=date(2026, 6, 10),
            ),
        ),
    )


@pytest.mark.anyio
async def test_create_transaction_persists_transaction_entries_and_entry_tags(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        food_tag_id = await _create_tag(session, title="Food")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)

        created_transaction = await repository.create_transaction(
            _build_new_transaction(
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
async def test_create_transaction_persists_explicit_effective_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        food_tag_id = await _create_tag(session, title="Food")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)

        created_transaction = await repository.create_transaction(
            _build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.EFFECTIVE,
            ),
        )
        await session.commit()

        transaction_record = await session.get(
            TransactionRecord,
            created_transaction.transaction.id,
        )

    assert created_transaction.transaction.status == TransactionStatus.EFFECTIVE
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.EFFECTIVE


@pytest.mark.anyio
async def test_create_transaction_persists_explicit_canceled_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        food_tag_id = await _create_tag(session, title="Food")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)

        created_transaction = await repository.create_transaction(
            _build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=food_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.CANCELED,
            ),
        )
        await session.commit()

        transaction_record = await session.get(
            TransactionRecord,
            created_transaction.transaction.id,
        )

    assert created_transaction.transaction.status == TransactionStatus.CANCELED
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.CANCELED


@pytest.mark.anyio
async def test_get_transaction_by_id_hydrates_private_transaction_graph(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        food_tag_id = await _create_tag(session, title="Food")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            _build_new_transaction(
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
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        groceries_tag_id = await _create_tag(session, title="Groceries")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            _build_new_transaction(
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
            TransactionChanges(
                effective_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
                title="Hotel reservation",
                description="Updated pending purchase",
                currency="BRL",
                entries=(
                    NewEntry(
                        ledger_account_id=expense_ledger_account_id,
                        amount=Decimal("900.00"),
                        statement_closing_date=None,
                        statement_due_date=None,
                        entry_tags=(NewEntryTag(tag_id=travel_tag_id),),
                    ),
                    NewEntry(
                        ledger_account_id=credit_card_ledger_account_id,
                        amount=Decimal("-900.00"),
                        statement_closing_date=date(2026, 6, 30),
                        statement_due_date=date(2026, 7, 10),
                    ),
                ),
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
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        groceries_tag_id = await _create_tag(session, title="Groceries")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            _build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.EFFECTIVE,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)

        with pytest.raises(TransactionMustBePendingError):
            await repository.update_transaction(
                created_transaction.transaction.id,
                TransactionChanges(
                    effective_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
                    title="Hotel reservation",
                    description="Updated pending purchase",
                    currency="BRL",
                    entries=(
                        NewEntry(
                            ledger_account_id=expense_ledger_account_id,
                            amount=Decimal("900.00"),
                            statement_closing_date=None,
                            statement_due_date=None,
                            entry_tags=(NewEntryTag(tag_id=travel_tag_id),),
                        ),
                        NewEntry(
                            ledger_account_id=credit_card_ledger_account_id,
                            amount=Decimal("-900.00"),
                            statement_closing_date=date(2026, 6, 30),
                            statement_due_date=date(2026, 7, 10),
                        ),
                    ),
                ),
            )


@pytest.mark.anyio
async def test_mark_transaction_effective_updates_status_without_replacing_entries(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        groceries_tag_id = await _create_tag(session, title="Groceries")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            _build_new_transaction(
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

        transitioned_transaction = await repository.mark_transaction_effective(
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

    assert transitioned_transaction.transaction.status == TransactionStatus.EFFECTIVE
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.EFFECTIVE
    assert [
        entry_record.id for entry_record in transitioned_entry_records
    ] == original_entry_ids


@pytest.mark.anyio
async def test_cancel_transaction_allows_effective_status_without_replacing_entries(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        groceries_tag_id = await _create_tag(session, title="Groceries")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            _build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.EFFECTIVE,
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

        transitioned_transaction = await repository.cancel_transaction(
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

    assert transitioned_transaction.transaction.status == TransactionStatus.CANCELED
    assert transaction_record is not None
    assert transaction_record.status == TransactionStatus.CANCELED
    assert [
        entry_record.id for entry_record in transitioned_entry_records
    ] == original_entry_ids


@pytest.mark.anyio
async def test_cancel_transaction_rejects_terminal_canceled_status(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        expense_ledger_account_id = await _create_ledger_account(
            session,
            title="Travel Expense",
            type=LedgerAccountType.EXPENSE,
            kind=LedgerAccountKind.OTHER,
        )
        credit_card_ledger_account_id = await _create_ledger_account(
            session,
            title="Visa Platinum",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
        )
        groceries_tag_id = await _create_tag(session, title="Groceries")
        travel_tag_id = await _create_tag(session, title="Travel")
        repository = SQLAlchemyTransactionRepository(session)
        created_transaction = await repository.create_transaction(
            _build_new_transaction(
                expense_ledger_account_id=expense_ledger_account_id,
                credit_card_ledger_account_id=credit_card_ledger_account_id,
                food_tag_id=groceries_tag_id,
                travel_tag_id=travel_tag_id,
                status=TransactionStatus.CANCELED,
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTransactionRepository(session)

        with pytest.raises(TransactionStatusTransitionNotAllowedError):
            await repository.cancel_transaction(created_transaction.transaction.id)

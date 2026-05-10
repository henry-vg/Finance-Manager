import os
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.domain.ledger_account import (
    Currency,
    LedgerAccountKind,
    LedgerAccountType,
    NewLedgerAccount,
)
from src.core.domain.statement_cycle import (
    NewStatementCycle,
    StatementCycleChanges,
    StatementCycleSortableField,
)
from src.core.ports.output.statement_cycle_output_port import (
    StatementCycleNotFoundOutputPortError,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    SQLAlchemyLedgerAccountOutputAdapter,
    SQLAlchemyStatementCycleOutputAdapter,
    StatementCycleRecord,
    create_postgres_engine,
    create_postgres_session_factory,
    dispose_postgres_engine,
    postgres_metadata,
)
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
        await connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION set_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = TIMEZONE('UTC', CURRENT_TIMESTAMP);

                    IF NEW.is_deleted IS TRUE AND OLD.is_deleted IS FALSE THEN
                        NEW.deleted_at = TIMEZONE('UTC', CURRENT_TIMESTAMP);
                    END IF;

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """,
            ),
        )
        await connection.run_sync(postgres_metadata.drop_all)
        await connection.run_sync(postgres_metadata.create_all)
        await connection.execute(
            text(
                (
                    "DROP TRIGGER IF EXISTS set_ledger_accounts_updated_at "
                    "ON ledger_accounts"
                ),
            ),
        )
        await connection.execute(
            text(
                (
                    "DROP TRIGGER IF EXISTS set_statement_cycles_updated_at "
                    "ON statement_cycles"
                ),
            ),
        )
        await connection.execute(
            text(
                """
                CREATE TRIGGER set_ledger_accounts_updated_at
                BEFORE UPDATE ON ledger_accounts
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at()
                """,
            ),
        )
        await connection.execute(
            text(
                """
                CREATE TRIGGER set_statement_cycles_updated_at
                BEFORE UPDATE ON statement_cycles
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at()
                """,
            ),
        )


async def _cleanup_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(postgres_metadata.drop_all)
        await connection.execute(text("DROP FUNCTION IF EXISTS set_updated_at()"))


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


async def _create_credit_card_ledger_account(
    session: AsyncSession,
) -> int:
    ledger_accounts = SQLAlchemyLedgerAccountOutputAdapter(session)
    ledger_account = await ledger_accounts.create_ledger_account(
        new_ledger_account=NewLedgerAccount(
            title="Credit Card",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
            currency=Currency.BRL,
        ),
    )
    await session.flush()
    return ledger_account.id


@pytest.mark.anyio
async def test_create_statement_cycle_generates_id_and_timestamps_with_active_defaults(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        ledger_account_id = await _create_credit_card_ledger_account(session)
        repository = SQLAlchemyStatementCycleOutputAdapter(session)

        created_statement_cycle = await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 5, 1),
                cycle_end=date(2026, 5, 31),
                closing_date=date(2026, 5, 28),
                due_date=date(2026, 6, 5),
            ),
        )
        await session.commit()
        statement_cycle_record = await session.get(
            StatementCycleRecord,
            created_statement_cycle.id,
        )

    assert created_statement_cycle.id > 0
    assert created_statement_cycle.created_at is not None
    assert created_statement_cycle.updated_at == created_statement_cycle.created_at
    assert statement_cycle_record is not None
    assert statement_cycle_record.is_deleted is False
    assert statement_cycle_record.deleted_at is None


@pytest.mark.anyio
async def test_update_statement_cycle_preserves_created_at_and_refreshes_updated_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        ledger_account_id = await _create_credit_card_ledger_account(session)
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        created_statement_cycle = await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 5, 1),
                cycle_end=date(2026, 5, 31),
                closing_date=date(2026, 5, 28),
                due_date=date(2026, 6, 5),
            ),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        updated_statement_cycle = await repository.update_statement_cycle(
            statement_cycle_id=created_statement_cycle.id,
            changes=StatementCycleChanges(
                ledger_account_id=created_statement_cycle.ledger_account_id,
                cycle_start=date(2026, 6, 1),
                cycle_end=date(2026, 6, 30),
                closing_date=date(2026, 6, 28),
                due_date=date(2026, 7, 5),
            ),
        )
        await session.commit()

    assert updated_statement_cycle.id == created_statement_cycle.id
    assert updated_statement_cycle.created_at == created_statement_cycle.created_at
    assert updated_statement_cycle.updated_at > created_statement_cycle.updated_at


@pytest.mark.anyio
async def test_list_statement_cycles_returns_active_page_with_total(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        ledger_account_id = await _create_credit_card_ledger_account(session)
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 5, 1),
                cycle_end=date(2026, 5, 31),
                closing_date=date(2026, 5, 28),
                due_date=date(2026, 6, 5),
            ),
        )
        soft_deleted_statement_cycle = await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 6, 1),
                cycle_end=date(2026, 6, 30),
                closing_date=date(2026, 6, 28),
                due_date=date(2026, 7, 5),
            ),
        )
        await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 7, 1),
                cycle_end=date(2026, 7, 31),
                closing_date=date(2026, 7, 28),
                due_date=date(2026, 8, 5),
            ),
        )
        await repository.soft_delete_statement_cycle(
            statement_cycle_id=soft_deleted_statement_cycle.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        page = await repository.list_statement_cycles(
            list_query=ListQuery(
                offset=0,
                limit=10,
                sort=(
                    SortTerm(
                        field=StatementCycleSortableField.CYCLE_START.name.lower(),
                        direction=SortDirection.ASC,
                    ),
                ),
            ),
        )

    assert page.total == 2
    assert [
        statement_cycle.cycle_start.isoformat() for statement_cycle in page.items
    ] == [
        "2026-05-01",
        "2026-07-01",
    ]


@pytest.mark.anyio
async def test_soft_delete_statement_cycle_hides_statement_cycle_from_active_reads(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        ledger_account_id = await _create_credit_card_ledger_account(session)
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        created_statement_cycle = await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 5, 1),
                cycle_end=date(2026, 5, 31),
                closing_date=date(2026, 5, 28),
                due_date=date(2026, 6, 5),
            ),
        )
        await repository.soft_delete_statement_cycle(
            statement_cycle_id=created_statement_cycle.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        active_statement_cycle = await repository.get_statement_cycle_by_id(
            statement_cycle_id=created_statement_cycle.id,
        )
        deleted_statement_cycle = (
            await repository.get_statement_cycle_by_id_including_deleted(
                statement_cycle_id=created_statement_cycle.id,
            )
        )

    assert active_statement_cycle is None
    assert deleted_statement_cycle is not None


@pytest.mark.anyio
async def test_hard_delete_statement_cycle_removes_record_permanently(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        ledger_account_id = await _create_credit_card_ledger_account(session)
        repository = SQLAlchemyStatementCycleOutputAdapter(session)
        created_statement_cycle = await repository.create_statement_cycle(
            new_statement_cycle=NewStatementCycle(
                ledger_account_id=ledger_account_id,
                cycle_start=date(2026, 5, 1),
                cycle_end=date(2026, 5, 31),
                closing_date=date(2026, 5, 28),
                due_date=date(2026, 6, 5),
            ),
        )
        await repository.soft_delete_statement_cycle(
            statement_cycle_id=created_statement_cycle.id,
        )
        await repository.hard_delete_statement_cycle(
            statement_cycle_id=created_statement_cycle.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        statement_cycle_record = await session.get(
            StatementCycleRecord,
            created_statement_cycle.id,
        )

    assert statement_cycle_record is None


@pytest.mark.anyio
async def test_update_missing_statement_cycle_raises_not_found_output_port(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyStatementCycleOutputAdapter(session)

        with pytest.raises(StatementCycleNotFoundOutputPortError):
            await repository.update_statement_cycle(
                statement_cycle_id=999,
                changes=StatementCycleChanges(
                    ledger_account_id=1,
                    cycle_start=date(2026, 6, 1),
                    cycle_end=date(2026, 6, 30),
                    closing_date=date(2026, 6, 28),
                    due_date=date(2026, 7, 5),
                ),
            )

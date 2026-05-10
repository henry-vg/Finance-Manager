import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.domain.ledger_account import (
    Currency,
    LedgerAccountChanges,
    LedgerAccountKind,
    LedgerAccountSortableField,
    LedgerAccountType,
    NewLedgerAccount,
)
from src.core.ports.output.ledger_account_output_port import (
    LedgerAccountNotFoundOutputPortError,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    LedgerAccountRecord,
    SQLAlchemyLedgerAccountOutputAdapter,
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


def _build_new_ledger_account(
    *,
    title: str = "Main Account",
    type: LedgerAccountType = LedgerAccountType.ASSET,
    kind: LedgerAccountKind = LedgerAccountKind.BANK_ACCOUNT,
    currency: Currency = Currency.BRL,
) -> NewLedgerAccount:
    return NewLedgerAccount(
        title=title,
        type=type,
        kind=kind,
        currency=currency,
    )


def _build_ledger_account_changes(
    *,
    title: str = "Credit Card",
    type: LedgerAccountType = LedgerAccountType.LIABILITY,
    kind: LedgerAccountKind = LedgerAccountKind.CREDIT_CARD,
    currency: Currency = Currency.USD,
) -> LedgerAccountChanges:
    return LedgerAccountChanges(
        title=title,
        type=type,
        kind=kind,
        currency=currency,
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
                """
                CREATE TRIGGER set_ledger_accounts_updated_at
                BEFORE UPDATE ON ledger_accounts
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


@pytest.mark.anyio
async def test_create_ledger_account_generates_id_and_timestamps_with_active_defaults(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)

        created_ledger_account = await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(),
        )
        await session.commit()
        ledger_account_record = await session.get(
            LedgerAccountRecord,
            created_ledger_account.id,
        )

    assert created_ledger_account.id > 0
    assert created_ledger_account.created_at is not None
    assert created_ledger_account.updated_at == created_ledger_account.created_at
    assert ledger_account_record is not None
    assert ledger_account_record.type == LedgerAccountType.ASSET
    assert ledger_account_record.kind == LedgerAccountKind.BANK_ACCOUNT
    assert ledger_account_record.currency == Currency.BRL
    assert ledger_account_record.is_deleted is False
    assert ledger_account_record.deleted_at is None


@pytest.mark.anyio
async def test_update_ledger_account_preserves_created_at_and_refreshes_updated_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        created_ledger_account = await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        updated_ledger_account = await repository.update_ledger_account(
            ledger_account_id=created_ledger_account.id,
            changes=_build_ledger_account_changes(),
        )
        await session.commit()

    assert updated_ledger_account.id == created_ledger_account.id
    assert updated_ledger_account.created_at == created_ledger_account.created_at
    assert updated_ledger_account.updated_at > created_ledger_account.updated_at


@pytest.mark.anyio
async def test_list_ledger_accounts_returns_paginated_active_ledger_accounts_with_total(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(title="Main Account"),
        )
        soft_deleted_ledger_account = await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(
                title="Wallet",
                kind=LedgerAccountKind.WALLET,
            ),
        )
        await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(
                title="Credit Card",
                type=LedgerAccountType.LIABILITY,
                kind=LedgerAccountKind.CREDIT_CARD,
                currency=Currency.USD,
            ),
        )
        await repository.soft_delete_ledger_account(
            ledger_account_id=soft_deleted_ledger_account.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        page = await repository.list_ledger_accounts(
            list_query=ListQuery(
                offset=0,
                limit=10,
                sort=(
                    SortTerm(
                        field=LedgerAccountSortableField.TITLE.name.lower(),
                        direction=SortDirection.ASC,
                    ),
                ),
            ),
        )

    assert page.total == 2
    assert [ledger_account.title for ledger_account in page.items] == [
        "Credit Card",
        "Main Account",
    ]


@pytest.mark.anyio
async def test_soft_delete_ledger_account_hides_ledger_account_from_active_reads(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        created_ledger_account = await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(),
        )
        await repository.soft_delete_ledger_account(
            ledger_account_id=created_ledger_account.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        active_ledger_account = await repository.get_ledger_account_by_id(
            ledger_account_id=created_ledger_account.id,
        )
        deleted_ledger_account = (
            await repository.get_ledger_account_by_id_including_deleted(
                ledger_account_id=created_ledger_account.id,
            )
        )

    assert active_ledger_account is None
    assert deleted_ledger_account is not None


@pytest.mark.anyio
async def test_hard_delete_ledger_account_removes_record_permanently(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        created_ledger_account = await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(),
        )
        await repository.soft_delete_ledger_account(
            ledger_account_id=created_ledger_account.id,
        )
        await repository.hard_delete_ledger_account(
            ledger_account_id=created_ledger_account.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        ledger_account_record = await session.get(
            LedgerAccountRecord,
            created_ledger_account.id,
        )

    assert ledger_account_record is None


@pytest.mark.anyio
async def test_update_missing_ledger_account_raises_not_found_output_port(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)

        with pytest.raises(LedgerAccountNotFoundOutputPortError):
            await repository.update_ledger_account(
                ledger_account_id=999,
                changes=_build_ledger_account_changes(),
            )

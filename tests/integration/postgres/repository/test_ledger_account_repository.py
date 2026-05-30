import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.ledger_account import (
    LedgerAccountInstrumentKind,
    LedgerAccountSortableField,
    LedgerAccountType,
)
from src.core.ports.output.ledger_account_output_port import (
    LedgerAccountNotFoundOutputPortError,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    LedgerAccountRecord,
    SQLAlchemyLedgerAccountOutputAdapter,
)
from tests.integration.postgres.helpers.builders import (
    build_ledger_account_changes as _build_ledger_account_changes,
)
from tests.integration.postgres.helpers.builders import (
    build_new_ledger_account as _build_new_ledger_account,
)
from tests.integration.postgres.helpers.clock import (
    advance_postgres_clock,
)


@pytest.fixture
def postgres_trigger_specs() -> tuple[tuple[str, str], ...]:
    return (("set_ledger_accounts_updated_at", "ledger_accounts"),)


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
    assert (
        ledger_account_record.instrument_kind
        == LedgerAccountInstrumentKind.BANK_ACCOUNT
    )
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
        await advance_postgres_clock(session)

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
                instrument_kind=LedgerAccountInstrumentKind.WALLET,
            ),
        )
        await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(
                title="Credit Card",
                type=LedgerAccountType.LIABILITY,
                instrument_kind=LedgerAccountInstrumentKind.CREDIT_CARD,
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
async def test_soft_delete_ledger_account_raises_not_found_for_deleted_record(
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

        with pytest.raises(LedgerAccountNotFoundOutputPortError):
            await repository.soft_delete_ledger_account(
                ledger_account_id=created_ledger_account.id,
            )


@pytest.mark.anyio
async def test_hard_delete_ledger_account_removes_active_row_without_prior_soft_delete(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        created_ledger_account = await repository.create_ledger_account(
            new_ledger_account=_build_new_ledger_account(),
        )
        await repository.hard_delete_ledger_account(
            ledger_account_id=created_ledger_account.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)
        ledger_account_record = await session.get(
            LedgerAccountRecord,
            created_ledger_account.id,
        )
        deleted_ledger_account = (
            await repository.get_ledger_account_by_id_including_deleted(
                ledger_account_id=created_ledger_account.id,
            )
        )

    assert ledger_account_record is None
    assert deleted_ledger_account is None


@pytest.mark.anyio
async def test_update_ledger_account_raises_not_found_when_record_is_missing(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyLedgerAccountOutputAdapter(session)

        with pytest.raises(LedgerAccountNotFoundOutputPortError):
            await repository.update_ledger_account(
                ledger_account_id=999,
                changes=_build_ledger_account_changes(),
            )

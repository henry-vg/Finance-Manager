import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.currency import CurrencyChanges, CurrencySortableField, NewCurrency
from src.core.ports.output.currency_output_port import (
    CurrencyISOCodeConflictOutputPortError,
    CurrencyNotFoundOutputPortError,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    CurrencyRecord,
    SQLAlchemyCurrencyOutputAdapter,
)


def _build_new_currency(
    *,
    iso_code: str = "USD",
    iso_numeric: str = "840",
    name: str = "US Dollar",
    symbol: str = "$",
    decimal_places: int = 2,
) -> NewCurrency:
    return NewCurrency(
        iso_code=iso_code,
        iso_numeric=iso_numeric,
        name=name,
        symbol=symbol,
        decimal_places=decimal_places,
    )


def _build_currency_changes(
    *,
    iso_code: str = "BRL",
    iso_numeric: str = "986",
    name: str = "Brazilian Real",
    symbol: str = "R$",
    decimal_places: int = 2,
) -> CurrencyChanges:
    return CurrencyChanges(
        iso_code=iso_code,
        iso_numeric=iso_numeric,
        name=name,
        symbol=symbol,
        decimal_places=decimal_places,
    )


@pytest.fixture
def postgres_trigger_specs() -> tuple[tuple[str, str], ...]:
    return (("set_currencies_updated_at", "currencies"),)


@pytest.mark.anyio
async def test_create_currency_generates_id_and_persists_metadata(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)

        created_currency = await repository.create_currency(_build_new_currency())
        await session.commit()
        currency_record = await session.get(CurrencyRecord, created_currency.id)

    assert created_currency.id > 0
    assert created_currency.storage_decimal_places == 3
    assert currency_record is not None
    assert currency_record.iso_code == "USD"


@pytest.mark.anyio
async def test_create_currency_raises_code_conflict_for_duplicate_code(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        await repository.create_currency(_build_new_currency())

        with pytest.raises(CurrencyISOCodeConflictOutputPortError):
            await repository.create_currency(_build_new_currency())


@pytest.mark.anyio
async def test_update_currency_preserves_created_at_and_refreshes_updated_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        created_currency = await repository.create_currency(_build_new_currency())
        await session.commit()

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        updated_currency = await repository.update_currency(
            currency_id=created_currency.id,
            changes=_build_currency_changes(),
        )
        await session.commit()

    assert updated_currency.id == created_currency.id
    assert updated_currency.created_at == created_currency.created_at
    assert updated_currency.updated_at > created_currency.updated_at
    assert updated_currency.iso_code == "BRL"


@pytest.mark.anyio
async def test_list_currencies_returns_paginated_active_currencies_with_total(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        await repository.create_currency(_build_new_currency(iso_code="USD"))
        soft_deleted_currency = await repository.create_currency(
            _build_new_currency(
                iso_code="EUR",
                iso_numeric="978",
                name="Euro",
                symbol="EUR",
            ),
        )
        await repository.create_currency(
            _build_new_currency(
                iso_code="BRL",
                iso_numeric="986",
                name="Brazilian Real",
                symbol="R$",
            ),
        )
        await repository.soft_delete_currency(currency_id=soft_deleted_currency.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        page = await repository.list_currencies(
            list_query=ListQuery(
                offset=0,
                limit=10,
                sort=(
                    SortTerm(
                        field=CurrencySortableField.ISO_CODE.name.lower(),
                        direction=SortDirection.ASC,
                    ),
                ),
            ),
        )

    assert page.total == 2
    assert [currency.iso_code for currency in page.items] == ["BRL", "USD"]


@pytest.mark.anyio
async def test_soft_delete_currency_hides_currency_from_active_reads(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        created_currency = await repository.create_currency(_build_new_currency())
        await repository.soft_delete_currency(currency_id=created_currency.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        active_currency = await repository.get_currency_by_id(
            currency_id=created_currency.id,
        )
        deleted_currency = await repository.get_currency_by_id_including_deleted(
            currency_id=created_currency.id,
        )

    assert active_currency is None
    assert deleted_currency is not None


@pytest.mark.anyio
async def test_soft_delete_currency_raises_not_found_when_record_was_already_deleted(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        created_currency = await repository.create_currency(_build_new_currency())
        await repository.soft_delete_currency(currency_id=created_currency.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)

        with pytest.raises(CurrencyNotFoundOutputPortError):
            await repository.soft_delete_currency(currency_id=created_currency.id)


@pytest.mark.anyio
async def test_hard_delete_currency_removes_active_row_without_prior_soft_delete(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        created_currency = await repository.create_currency(_build_new_currency())
        await repository.hard_delete_currency(currency_id=created_currency.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)
        currency_record = await session.get(CurrencyRecord, created_currency.id)
        deleted_currency = await repository.get_currency_by_id_including_deleted(
            currency_id=created_currency.id,
        )

    assert currency_record is None
    assert deleted_currency is None


@pytest.mark.anyio
async def test_update_currency_raises_not_found_when_record_is_missing(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyCurrencyOutputAdapter(session)

        with pytest.raises(CurrencyNotFoundOutputPortError):
            await repository.update_currency(
                currency_id=999,
                changes=_build_currency_changes(),
            )

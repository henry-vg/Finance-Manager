import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.domain.tag import NewTag, TagChanges, TagSortableField
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    SQLAlchemyTagOutputAdapter,
    TagRecord,
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


def _build_new_tag(*, title: str = "Food") -> NewTag:
    return NewTag(title=title)


def _build_tag_changes(*, title: str = "Utilities") -> TagChanges:
    return TagChanges(title=title)


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
            text("DROP TRIGGER IF EXISTS set_tags_updated_at ON tags"),
        )
        await connection.execute(
            text(
                """
                CREATE TRIGGER set_tags_updated_at
                BEFORE UPDATE ON tags
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
async def test_create_tag_generates_id_and_timestamps_with_active_defaults(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)

        created_tag = await repository.create_tag(new_tag=_build_new_tag())
        await session.commit()
        tag_record = await session.get(TagRecord, created_tag.id)

    assert created_tag.id > 0
    assert created_tag.created_at is not None
    assert created_tag.updated_at == created_tag.created_at
    assert tag_record is not None
    assert tag_record.is_deleted is False
    assert tag_record.deleted_at is None


@pytest.mark.anyio
async def test_update_tag_preserves_created_at_and_refreshes_updated_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        created_tag = await repository.create_tag(new_tag=_build_new_tag())
        await session.commit()

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        updated_tag = await repository.update_tag(
            tag_id=created_tag.id,
            changes=_build_tag_changes(),
        )
        await session.commit()

    assert updated_tag.id == created_tag.id
    assert updated_tag.created_at == created_tag.created_at
    assert updated_tag.updated_at > created_tag.updated_at


@pytest.mark.anyio
async def test_list_tags_returns_paginated_active_tags_with_total(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        await repository.create_tag(new_tag=_build_new_tag(title="Food"))
        soft_deleted_tag = await repository.create_tag(
            new_tag=_build_new_tag(title="Travel"),
        )
        await repository.create_tag(new_tag=_build_new_tag(title="Utilities"))
        await repository.soft_delete_tag(tag_id=soft_deleted_tag.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        page = await repository.list_tags(
            list_query=ListQuery(
                offset=0,
                limit=10,
                sort=(
                    SortTerm(
                        field=TagSortableField.TITLE.name.lower(),
                        direction=SortDirection.ASC,
                    ),
                ),
            ),
        )

    assert page.total == 2
    assert [tag.title for tag in page.items] == ["Food", "Utilities"]


@pytest.mark.anyio
async def test_soft_delete_tag_hides_tag_from_active_reads(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        created_tag = await repository.create_tag(new_tag=_build_new_tag())
        await repository.soft_delete_tag(tag_id=created_tag.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        active_tag = await repository.get_tag_by_id(tag_id=created_tag.id)
        deleted_tag = await repository.get_tag_by_id_including_deleted(
            tag_id=created_tag.id,
        )

    assert active_tag is None
    assert deleted_tag is not None


@pytest.mark.anyio
async def test_hard_delete_tag_removes_record_permanently(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        created_tag = await repository.create_tag(new_tag=_build_new_tag())
        await repository.soft_delete_tag(tag_id=created_tag.id)
        await repository.hard_delete_tag(tag_id=created_tag.id)
        await session.commit()

    async with postgres_session_factory() as session:
        tag_record = await session.get(TagRecord, created_tag.id)

    assert tag_record is None

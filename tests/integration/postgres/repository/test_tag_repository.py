import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.tag import TagSortableField
from src.core.ports.output.tag_output_port import TagNotFoundOutputPortError
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.postgres import (
    SQLAlchemyTagOutputAdapter,
    TagRecord,
)
from tests.integration.postgres.helpers.builders import (
    build_new_tag as _build_new_tag,
)
from tests.integration.postgres.helpers.builders import (
    build_tag_changes as _build_tag_changes,
)
from tests.integration.postgres.helpers.clock import (
    advance_postgres_clock,
)


@pytest.fixture
def postgres_trigger_specs() -> tuple[tuple[str, str], ...]:
    return (("set_tags_updated_at", "tags"),)


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
        await advance_postgres_clock(session)

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
async def test_soft_delete_tag_raises_not_found_when_record_was_already_deleted(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        created_tag = await repository.create_tag(new_tag=_build_new_tag())
        await repository.soft_delete_tag(tag_id=created_tag.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)

        with pytest.raises(TagNotFoundOutputPortError):
            await repository.soft_delete_tag(tag_id=created_tag.id)


@pytest.mark.anyio
async def test_hard_delete_tag_removes_active_row_without_prior_soft_delete(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        created_tag = await repository.create_tag(new_tag=_build_new_tag())
        await repository.hard_delete_tag(tag_id=created_tag.id)
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)
        tag_record = await session.get(TagRecord, created_tag.id)
        deleted_tag = await repository.get_tag_by_id_including_deleted(
            tag_id=created_tag.id,
        )

    assert tag_record is None
    assert deleted_tag is None


@pytest.mark.anyio
async def test_update_tag_raises_not_found_when_record_is_missing(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyTagOutputAdapter(session)

        with pytest.raises(TagNotFoundOutputPortError):
            await repository.update_tag(
                tag_id=999,
                changes=_build_tag_changes(),
            )

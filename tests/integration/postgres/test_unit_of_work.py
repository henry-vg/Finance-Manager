import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infra.postgres import (
    SQLAlchemyPostgresUnitOfWorkFactory,
    SQLAlchemyUserOutputAdapter,
)
from tests.integration.postgres.helpers.builders import (
    build_new_user as _build_new_user,
)
from tests.integration.postgres.helpers.builders import (
    build_user_changes as _build_user_changes,
)


@pytest.mark.anyio
async def test_unit_of_work_commit_persists_changes(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unit_of_work_factory = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )

    async with unit_of_work_factory() as unit_of_work:
        created_user = await unit_of_work.users.create_user(
            new_user=_build_new_user(),
        )
        await unit_of_work.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        persisted_user = await repository.get_user_by_email("ada@example.com")

    assert persisted_user is not None
    assert persisted_user.id == created_user.id


@pytest.mark.anyio
async def test_unit_of_work_rolls_back_when_exiting_without_commit(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unit_of_work_factory = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )

    async with unit_of_work_factory() as unit_of_work:
        await unit_of_work.users.create_user(
            new_user=_build_new_user(),
        )

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        persisted_user = await repository.get_user_by_email("ada@example.com")

    assert persisted_user is None


@pytest.mark.anyio
async def test_unit_of_work_rolls_back_when_exception_is_raised(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unit_of_work_factory = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )

    with pytest.raises(RuntimeError, match="boom"):
        async with unit_of_work_factory() as unit_of_work:
            await unit_of_work.users.create_user(
                new_user=_build_new_user(),
            )
            raise RuntimeError("boom")

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        persisted_user = await repository.get_user_by_email("ada@example.com")

    assert persisted_user is None


@pytest.mark.anyio
async def test_unit_of_work_rolls_back_pending_changes_after_a_prior_commit(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unit_of_work_factory = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )

    async with unit_of_work_factory() as unit_of_work:
        created_user = await unit_of_work.users.create_user(
            new_user=_build_new_user(),
        )
        await unit_of_work.commit()

        await unit_of_work.users.update_user(
            user_id=created_user.id,
            changes=_build_user_changes(),
        )

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        persisted_user = await repository.get_user_by_email("ada@example.com")

    assert persisted_user is not None
    assert persisted_user.id == created_user.id
    assert persisted_user.first_name == "Ada"
    assert persisted_user.last_name == "Lovelace"
    assert persisted_user.email == "ada@example.com"


@pytest.mark.anyio
async def test_unit_of_work_cannot_be_reused_after_exit(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unit_of_work = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )()

    async with unit_of_work:
        pass

    with pytest.raises(RuntimeError, match="cannot be reused"):
        async with unit_of_work:
            pass

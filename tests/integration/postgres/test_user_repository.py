import os
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.domain.user import NewUser, UserChanges
from src.core.ports.output.user_output_port import UserEmailConflictOutputPortError
from src.core.shared import ListQuery
from src.infra.postgres import (
    SQLAlchemyPostgresUnitOfWorkFactory,
    SQLAlchemyUserOutputAdapter,
    UserRecord,
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


def _build_new_user(
    *,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = "ada@example.com",
    password_hash: str = "hashed::plain-password",
    birth_date: date = date(1815, 12, 10),
) -> NewUser:
    return NewUser(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        birth_date=birth_date,
    )


def _build_user_changes(
    *,
    first_name: str = "Grace",
    last_name: str = "Hopper",
    email: str = "grace@example.com",
    password_hash: str = "hashed::new-password",
    birth_date: date = date(1906, 12, 9),
) -> UserChanges:
    return UserChanges(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        birth_date=birth_date,
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
            text("DROP TRIGGER IF EXISTS set_users_updated_at ON users"),
        )
        await connection.execute(
            text(
                """
                CREATE TRIGGER set_users_updated_at
                BEFORE UPDATE ON users
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
async def test_create_user_generates_id_and_timestamps_with_active_defaults(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        created_user = await repository.create_user(
            new_user=_build_new_user(),
        )
        await session.commit()
        user_record = await session.get(UserRecord, created_user.id)

    assert created_user.id > 0
    assert created_user.created_at is not None
    assert created_user.updated_at is not None
    assert created_user.updated_at == created_user.created_at
    assert user_record is not None
    assert user_record.is_deleted is False
    assert user_record.deleted_at is None


@pytest.mark.anyio
async def test_update_user_preserves_created_at_and_refreshes_updated_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        created_user = await repository.create_user(
            new_user=_build_new_user(),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        updated_user = await repository.update_user(
            user_id=created_user.id,
            changes=_build_user_changes(),
        )
        await session.commit()

    assert updated_user.id == created_user.id
    assert updated_user.created_at == created_user.created_at
    assert updated_user.updated_at > created_user.updated_at


@pytest.mark.anyio
async def test_create_user_raises_on_email_conflict(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        await repository.create_user(
            new_user=_build_new_user(),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        with pytest.raises(UserEmailConflictOutputPortError):
            await repository.create_user(
                new_user=_build_new_user(
                    first_name="Grace",
                    last_name="Hopper",
                    password_hash="hashed::another-password",
                    birth_date=date(1906, 12, 9),
                ),
            )


@pytest.mark.anyio
async def test_list_users_returns_paginated_active_users_with_total(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        await repository.create_user(
            new_user=_build_new_user(
                first_name="Ada",
                email="ada@example.com",
            ),
        )
        soft_deleted_user = await repository.create_user(
            new_user=_build_new_user(
                first_name="Grace",
                email="grace@example.com",
            ),
        )
        await repository.create_user(
            new_user=_build_new_user(
                first_name="Katherine",
                email="katherine@example.com",
            ),
        )
        await repository.soft_delete_user(
            user_id=soft_deleted_user.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        page = await repository.list_users(
            list_query=ListQuery(
                offset=1,
                limit=1,
            ),
        )

    assert page.offset == 1
    assert page.limit == 1
    assert page.total == 2
    assert [user.email for user in page.items] == ["katherine@example.com"]


@pytest.mark.anyio
async def test_list_users_returns_empty_page_when_no_active_users_exist(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        page = await repository.list_users(
            list_query=ListQuery(
                offset=0,
                limit=10,
            ),
        )

    assert page.items == []
    assert page.offset == 0
    assert page.limit == 10
    assert page.total == 0


@pytest.mark.anyio
async def test_soft_delete_user_hides_user_and_sets_deleted_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        created_user = await repository.create_user(
            new_user=_build_new_user(),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        await repository.soft_delete_user(
            user_id=created_user.id,
        )
        await session.commit()

        deleted_user = await repository.get_user_by_email("ada@example.com")
        included_user = await repository.get_user_by_email_including_deleted(
            "ada@example.com",
        )
        user_record = await session.get(UserRecord, created_user.id)

    assert deleted_user is None
    assert included_user is not None
    assert user_record is not None
    assert user_record.is_deleted is True
    assert user_record.deleted_at is not None
    assert user_record.deleted_at >= user_record.updated_at


@pytest.mark.anyio
async def test_hard_delete_user_removes_soft_deleted_row(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        created_user = await repository.create_user(
            new_user=_build_new_user(),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        await repository.soft_delete_user(
            user_id=created_user.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        await repository.hard_delete_user(
            user_id=created_user.id,
        )
        await session.commit()

        user_record = await session.get(UserRecord, created_user.id)
        included_user = await repository.get_user_by_email_including_deleted(
            "ada@example.com",
        )

    assert user_record is None
    assert included_user is None


@pytest.mark.anyio
async def test_create_user_still_raises_on_email_conflict_after_soft_delete(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        created_user = await repository.create_user(
            new_user=_build_new_user(),
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)
        await repository.soft_delete_user(
            user_id=created_user.id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        repository = SQLAlchemyUserOutputAdapter(session)

        with pytest.raises(UserEmailConflictOutputPortError):
            await repository.create_user(
                new_user=_build_new_user(
                    first_name="Grace",
                    last_name="Hopper",
                    password_hash="hashed::another-password",
                    birth_date=date(1906, 12, 9),
                ),
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

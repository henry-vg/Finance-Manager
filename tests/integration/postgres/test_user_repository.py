import os
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.domain.user import NewUser, UserChanges, UserEmailConflictError
from src.infra.postgres import (
    SQLAlchemyUserOutputAdapter,
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
async def test_create_user_generates_id_and_timestamps(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SQLAlchemyUserOutputAdapter(postgres_session_factory)

    created_user = await repository.create_user(
        new_user=NewUser(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            password_hash="hashed::plain-password",
            birth_date=date(1815, 12, 10),
        ),
    )

    assert created_user.id > 0
    assert created_user.created_at is not None
    assert created_user.updated_at is not None
    assert created_user.updated_at == created_user.created_at


@pytest.mark.anyio
async def test_update_user_preserves_created_at_and_refreshes_updated_at(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SQLAlchemyUserOutputAdapter(postgres_session_factory)

    created_user = await repository.create_user(
        new_user=NewUser(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            password_hash="hashed::plain-password",
            birth_date=date(1815, 12, 10),
        ),
    )

    async with postgres_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(0.01)"))
        await session.commit()

    updated_user = await repository.update_user(
        user_id=created_user.id,
        changes=UserChanges(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            password_hash="hashed::new-password",
            birth_date=date(1906, 12, 9),
        ),
    )

    assert updated_user.id == created_user.id
    assert updated_user.created_at == created_user.created_at
    assert updated_user.updated_at > created_user.updated_at


@pytest.mark.anyio
async def test_create_user_raises_on_email_conflict(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SQLAlchemyUserOutputAdapter(postgres_session_factory)

    await repository.create_user(
        new_user=NewUser(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            password_hash="hashed::plain-password",
            birth_date=date(1815, 12, 10),
        ),
    )

    with pytest.raises(UserEmailConflictError):
        await repository.create_user(
            new_user=NewUser(
                first_name="Grace",
                last_name="Hopper",
                email="ada@example.com",
                password_hash="hashed::another-password",
                birth_date=date(1906, 12, 9),
            ),
        )

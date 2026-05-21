import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infra.postgres import (
    create_postgres_engine,
    create_postgres_session_factory,
    dispose_postgres_engine,
    postgres_metadata,
)
from src.infra.settings.models import PostgresSettings

type PostgresTriggerSpec = tuple[str, str]


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


@pytest.fixture
def postgres_trigger_specs() -> tuple[PostgresTriggerSpec, ...]:
    return ()


async def _prepare_database(
    trigger_specs: tuple[PostgresTriggerSpec, ...],
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_postgres_engine(_build_postgres_settings())

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        await dispose_postgres_engine(engine)
        pytest.skip(f"Postgres integration database is not available: {exc}")

    async with engine.begin() as connection:
        if trigger_specs:
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

        for trigger_name, table_name in trigger_specs:
            await connection.execute(
                text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}"),
            )
            await connection.execute(
                text(
                    f"""
                    CREATE TRIGGER {trigger_name}
                    BEFORE UPDATE ON {table_name}
                    FOR EACH ROW
                    EXECUTE FUNCTION set_updated_at()
                    """,
                ),
            )

    try:
        yield create_postgres_session_factory(engine)
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(postgres_metadata.drop_all)
            if trigger_specs:
                await connection.execute(
                    text("DROP FUNCTION IF EXISTS set_updated_at()")
                )
        await dispose_postgres_engine(engine)


@pytest.fixture
async def postgres_session_factory(
    postgres_trigger_specs: tuple[PostgresTriggerSpec, ...],
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async for session_factory in _prepare_database(postgres_trigger_specs):
        yield session_factory

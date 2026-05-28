from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.core.domain.healthz import HealthzStatus
from src.infra.postgres.health import SQLAlchemyPostgresHealthAdapter
from src.infra.postgres.runtime import (
    create_postgres_engine,
    create_postgres_session_factory,
    dispose_postgres_engine,
    get_postgres_session,
)
from src.infra.settings.models import PostgresSettings


def _build_postgres_settings() -> PostgresSettings:
    return PostgresSettings(
        host="postgres",
        port=5432,
        user="finance_manager",
        password="finance_manager",
        database="finance_manager",
        echo=False,
        pool_size=10,
        max_overflow=20,
    )


def test_create_postgres_engine_uses_postgres_settings() -> None:
    engine = create_postgres_engine(_build_postgres_settings())

    assert isinstance(engine, AsyncEngine)
    assert engine.url.render_as_string(hide_password=False) == (
        "postgresql+asyncpg://finance_manager:finance_manager@postgres:5432/"
        "finance_manager"
    )
    assert engine.echo is False


def test_create_postgres_session_factory_binds_engine() -> None:
    engine = create_postgres_engine(_build_postgres_settings())

    session_factory = create_postgres_session_factory(engine)

    assert isinstance(session_factory, async_sessionmaker)
    assert session_factory.kw["bind"] is engine
    assert session_factory.kw["expire_on_commit"] is False


class _SuccessfulConnection:
    async def execute(self, _: Any) -> None:
        return None


class _SuccessfulConnectContext:
    async def __aenter__(self) -> _SuccessfulConnection:
        return _SuccessfulConnection()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FailingConnectContext:
    async def __aenter__(self) -> Any:
        raise RuntimeError("boom")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeEngine:
    def __init__(self, *, should_fail: bool = False) -> None:
        self._should_fail = should_fail
        self.disposed = False

    def connect(self) -> _SuccessfulConnectContext | _FailingConnectContext:
        if self._should_fail:
            return _FailingConnectContext()
        return _SuccessfulConnectContext()

    async def dispose(self) -> None:
        self.disposed = True


class _FakeSessionContext:
    def __init__(self, session: object) -> None:
        self._session = session
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> object:
        self.entered = True
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type
        del exc
        del tb
        self.exited = True


class _FakeSessionFactory:
    def __init__(self, session: object) -> None:
        self.context = _FakeSessionContext(session)

    def __call__(self) -> _FakeSessionContext:
        return self.context


@pytest.mark.anyio
async def test_postgres_health_adapter_returns_ok_when_query_succeeds() -> None:
    adapter = SQLAlchemyPostgresHealthAdapter(engine=cast(Any, _FakeEngine()))

    status = await adapter.get_database_status()

    assert status == HealthzStatus.OK


@pytest.mark.anyio
async def test_postgres_health_adapter_returns_not_ok_when_query_fails() -> None:
    adapter = SQLAlchemyPostgresHealthAdapter(
        engine=cast(Any, _FakeEngine(should_fail=True)),
    )

    status = await adapter.get_database_status()

    assert status == HealthzStatus.NOT_OK


@pytest.mark.anyio
async def test_dispose_postgres_engine_calls_engine_dispose() -> None:
    engine = _FakeEngine()

    await dispose_postgres_engine(cast(Any, engine))

    assert engine.disposed is True


@pytest.mark.anyio
async def test_get_postgres_session_yields_session_from_factory_context() -> None:
    session = object()
    session_factory = _FakeSessionFactory(session)

    produced_sessions = []
    async for produced_session in get_postgres_session(cast(Any, session_factory)):
        produced_sessions.append(produced_session)

    assert produced_sessions == [session]
    assert session_factory.context.entered is True
    assert session_factory.context.exited is True

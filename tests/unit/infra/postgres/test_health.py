from typing import Any, cast

import pytest

from src.core.domain.healthz import HealthzStatus
from src.infra.postgres.health import SQLAlchemyPostgresHealthAdapter


class _ConnectionStub:
    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    async def __aenter__(self) -> "_ConnectionStub":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        del exc_type
        del exc
        del traceback

    async def execute(self, query) -> None:
        del query
        if self._should_fail:
            raise RuntimeError("database unavailable")


class _EngineStub:
    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    def connect(self) -> _ConnectionStub:
        return _ConnectionStub(should_fail=self._should_fail)


@pytest.mark.anyio
async def test_get_database_status_returns_ok_when_query_succeeds() -> None:
    adapter = SQLAlchemyPostgresHealthAdapter(cast(Any, _EngineStub()))

    status = await adapter.get_database_status()

    assert status == HealthzStatus.OK


@pytest.mark.anyio
async def test_get_database_status_returns_not_ok_when_query_fails() -> None:
    adapter = SQLAlchemyPostgresHealthAdapter(
        cast(Any, _EngineStub(should_fail=True)),
    )

    status = await adapter.get_database_status()

    assert status == HealthzStatus.NOT_OK

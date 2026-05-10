from typing import Any, cast

import pytest

from src.infra.postgres.unit_of_work import (
    SQLAlchemyPostgresUnitOfWork,
    UnitOfWorkCannotBeReusedAfterExitError,
    UnitOfWorkHasNotBeenEnteredError,
    UnitOfWorkIsAlreadyActiveError,
)


class _FakeSession:
    def __init__(self) -> None:
        self._in_transaction = False
        self.rollback_calls = 0
        self.close_calls = 0
        self.commit_calls = 0

    def in_transaction(self) -> bool:
        return self._in_transaction

    async def rollback(self) -> None:
        self.rollback_calls += 1
        self._in_transaction = False

    async def close(self) -> None:
        self.close_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1


def _build_unit_of_work() -> SQLAlchemyPostgresUnitOfWork:
    return SQLAlchemyPostgresUnitOfWork(
        session_factory=cast(Any, lambda: _FakeSession()),
    )


def test_unit_of_work_raises_when_repository_is_accessed_before_enter() -> None:
    unit_of_work = _build_unit_of_work()

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        _ = unit_of_work.users


@pytest.mark.anyio
async def test_unit_of_work_raises_when_enter_is_called_twice_while_active() -> None:
    unit_of_work = _build_unit_of_work()

    await unit_of_work.__aenter__()

    with pytest.raises(UnitOfWorkIsAlreadyActiveError):
        await unit_of_work.__aenter__()

    await unit_of_work.__aexit__(None, None, None)


@pytest.mark.anyio
async def test_unit_of_work_raises_when_reused_after_exit() -> None:
    unit_of_work = _build_unit_of_work()

    await unit_of_work.__aenter__()
    await unit_of_work.__aexit__(None, None, None)

    with pytest.raises(UnitOfWorkCannotBeReusedAfterExitError):
        await unit_of_work.__aenter__()


@pytest.mark.anyio
async def test_unit_of_work_commit_raises_before_enter() -> None:
    unit_of_work = _build_unit_of_work()

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        await unit_of_work.commit()
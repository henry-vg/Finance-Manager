from typing import Any, cast

import pytest

from src.infra.postgres.unit_of_work import (
    SQLAlchemyPostgresUnitOfWork,
    SQLAlchemyPostgresUnitOfWorkFactory,
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
        _ = unit_of_work.currencies

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        _ = unit_of_work.ledger_accounts

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        _ = unit_of_work.tags

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        _ = unit_of_work.users

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        _ = unit_of_work.transactions


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


@pytest.mark.anyio
async def test_unit_of_work_exit_returns_when_session_was_never_entered() -> None:
    unit_of_work = _build_unit_of_work()

    await unit_of_work.__aexit__(None, None, None)

    with pytest.raises(UnitOfWorkHasNotBeenEnteredError):
        _ = unit_of_work.currencies


def _patch_output_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.infra.postgres.unit_of_work as unit_of_work_module

    monkeypatch.setattr(
        unit_of_work_module,
        "SQLAlchemyCurrencyOutputAdapter",
        lambda session: ("currencies", session),
    )
    monkeypatch.setattr(
        unit_of_work_module,
        "SQLAlchemyLedgerAccountOutputAdapter",
        lambda session: ("ledger_accounts", session),
    )
    monkeypatch.setattr(
        unit_of_work_module,
        "SQLAlchemyTagOutputAdapter",
        lambda session: ("tags", session),
    )
    monkeypatch.setattr(
        unit_of_work_module,
        "SQLAlchemyTransactionRepository",
        lambda session: ("transactions", session),
    )
    monkeypatch.setattr(
        unit_of_work_module,
        "SQLAlchemyUserOutputAdapter",
        lambda session: ("users", session),
    )


@pytest.mark.anyio
async def test_unit_of_work_initializes_repositories_and_closes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_output_adapters(monkeypatch)
    session = _FakeSession()
    unit_of_work = SQLAlchemyPostgresUnitOfWork(
        session_factory=cast(Any, lambda: session),
    )

    entered_unit_of_work = await unit_of_work.__aenter__()
    currencies = unit_of_work.currencies
    ledger_accounts = unit_of_work.ledger_accounts
    tags = unit_of_work.tags
    transactions = unit_of_work.transactions
    users = unit_of_work.users
    await unit_of_work.commit()
    await unit_of_work.__aexit__(None, None, None)

    assert entered_unit_of_work is unit_of_work
    assert currencies == ("currencies", session)
    assert ledger_accounts == ("ledger_accounts", session)
    assert tags == ("tags", session)
    assert transactions == ("transactions", session)
    assert users == ("users", session)
    assert session.commit_calls == 1
    assert session.rollback_calls == 0
    assert session.close_calls == 1


@pytest.mark.anyio
async def test_unit_of_work_rolls_back_active_transaction_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_output_adapters(monkeypatch)
    session = _FakeSession()
    session._in_transaction = True
    unit_of_work = SQLAlchemyPostgresUnitOfWork(
        session_factory=cast(Any, lambda: session),
    )

    await unit_of_work.__aenter__()
    await unit_of_work.__aexit__(RuntimeError, RuntimeError("boom"), None)

    assert session.rollback_calls == 1
    assert session.close_calls == 1


def test_unit_of_work_factory_creates_postgres_unit_of_work() -> None:
    factory = SQLAlchemyPostgresUnitOfWorkFactory(
        session_factory=cast(Any, lambda: _FakeSession()),
    )

    assert isinstance(factory(), SQLAlchemyPostgresUnitOfWork)

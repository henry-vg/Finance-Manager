from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.core.domain.transaction import TransactionStatus
from src.core.ports.output.transaction_output_port import (
    TransactionNotFoundOutputPortError,
)
from src.infra.postgres.aggregates.transaction.repository import (
    SQLAlchemyTransactionRepository,
)


class _FakeScalarsResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return list(self._values)


class _FakeSession:
    def __init__(
        self,
        *,
        scalar_results: tuple[object | None, ...] = (),
        scalars_results: tuple[list[object], ...] = (),
    ) -> None:
        self._scalar_results = list(scalar_results)
        self._scalars_results = list(scalars_results)
        self.flush_calls = 0

    async def scalar(self, statement: object) -> object | None:
        del statement
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    async def scalars(self, statement: object) -> _FakeScalarsResult:
        del statement
        if not self._scalars_results:
            return _FakeScalarsResult([])
        return _FakeScalarsResult(self._scalars_results.pop(0))

    async def flush(self) -> None:
        self.flush_calls += 1


def _build_transaction_record(**overrides: Any) -> SimpleNamespace:
    timestamp = datetime(2026, 5, 1, tzinfo=UTC)
    values = {
        "id": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        "effective_at": timestamp,
        "title": "Airline tickets",
        "description": "Family vacation purchase",
        "status": TransactionStatus.PENDING,
        "is_deleted": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.anyio
async def test_update_transaction_raises_not_found_when_record_is_missing() -> None:
    repository = SQLAlchemyTransactionRepository(cast(Any, _FakeSession()))

    with pytest.raises(TransactionNotFoundOutputPortError):
        await repository.update_transaction(
            1,
            cast(Any, SimpleNamespace()),
        )


@pytest.mark.anyio
async def test_get_transaction_by_id_returns_none_when_record_is_missing() -> None:
    repository = SQLAlchemyTransactionRepository(cast(Any, _FakeSession()))

    transaction = await repository.get_transaction_by_id(1)

    assert transaction is None


@pytest.mark.anyio
async def test_get_transaction_by_id_returns_transaction_with_empty_entries() -> None:
    repository = SQLAlchemyTransactionRepository(
        cast(
            Any,
            _FakeSession(
                scalar_results=(_build_transaction_record(),),
                scalars_results=([],),
            ),
        ),
    )

    transaction = await repository.get_transaction_by_id(1)

    assert transaction is not None
    assert transaction.transaction.id == 1
    assert transaction.entries == ()


@pytest.mark.anyio
async def test_post_transaction_raises_not_found_when_record_is_missing() -> None:
    repository = SQLAlchemyTransactionRepository(cast(Any, _FakeSession()))

    with pytest.raises(TransactionNotFoundOutputPortError):
        await repository.post_transaction(1)


@pytest.mark.anyio
async def test_post_transaction_raises_not_found_when_reload_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(scalar_results=(_build_transaction_record(),))
    repository = SQLAlchemyTransactionRepository(cast(Any, session))

    async def _missing_transaction(transaction_id: int) -> None:
        del transaction_id
        return None

    monkeypatch.setattr(repository, "get_transaction_by_id", _missing_transaction)

    with pytest.raises(TransactionNotFoundOutputPortError):
        await repository.post_transaction(1)

    assert session.flush_calls == 1

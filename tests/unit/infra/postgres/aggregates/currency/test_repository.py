from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.domain.currency import CurrencyChanges, NewCurrency
from src.core.ports.output.currency_output_port import (
    CurrencyISOCodeConflictOutputPortError,
    CurrencyNotFoundOutputPortError,
)
from src.infra.postgres.aggregates.currency import (
    repository as currency_repository_module,
)
from src.infra.postgres.aggregates.currency.repository import (
    SQLAlchemyCurrencyOutputAdapter,
)


class _FakeSession:
    def __init__(
        self,
        *,
        scalar_results: tuple[object | None, ...] = (),
        flush_error: Exception | None = None,
    ) -> None:
        self._scalar_results = list(scalar_results)
        self._flush_error = flush_error
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.refreshed: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def scalar(self, statement: object) -> object | None:
        del statement
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    async def flush(self) -> None:
        if self._flush_error is not None:
            raise self._flush_error

    async def refresh(self, value: object) -> None:
        self.refreshed.append(value)

    async def delete(self, value: object) -> None:
        self.deleted.append(value)


def _build_currency_record(**overrides: Any) -> SimpleNamespace:
    timestamp = datetime(2026, 5, 1, tzinfo=UTC)
    values = {
        "id": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        "iso_code": "USD",
        "iso_numeric": "840",
        "name": "US Dollar",
        "symbol": "$",
        "decimal_places": 2,
        "is_deleted": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.anyio
async def test_get_currency_by_id_returns_domain_currency_when_record_exists() -> None:
    repository = SQLAlchemyCurrencyOutputAdapter(
        cast(Any, _FakeSession(scalar_results=(_build_currency_record(),))),
    )

    currency = await repository.get_currency_by_id(1)

    assert currency is not None
    assert currency.id == 1
    assert currency.iso_code == "USD"


@pytest.mark.anyio
async def test_get_currency_by_iso_code_returns_currency_when_record_exists() -> None:
    repository = SQLAlchemyCurrencyOutputAdapter(
        cast(
            Any,
            _FakeSession(scalar_results=(_build_currency_record(iso_code="BRL"),)),
        ),
    )

    currency = await repository.get_currency_by_iso_code("BRL")

    assert currency is not None
    assert currency.iso_code == "BRL"


@pytest.mark.anyio
async def test_get_currency_by_iso_code_returns_none_when_record_is_missing() -> None:
    repository = SQLAlchemyCurrencyOutputAdapter(cast(Any, _FakeSession()))

    currency = await repository.get_currency_by_iso_code("BRL")

    assert currency is None


@pytest.mark.anyio
async def test_create_currency_reraises_integrity_error_when_violation_is_unmapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        flush_error=IntegrityError("statement", {}, Exception("boom")),
    )
    repository = SQLAlchemyCurrencyOutputAdapter(cast(Any, session))

    monkeypatch.setattr(
        currency_repository_module,
        "is_unique_violation",
        lambda exc, constraint_name: False,
    )

    with pytest.raises(IntegrityError):
        await repository.create_currency(
            NewCurrency(
                iso_code="USD",
                iso_numeric="840",
                name="US Dollar",
                symbol="$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_update_currency_reraises_integrity_error_when_violation_is_unmapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        scalar_results=(_build_currency_record(),),
        flush_error=IntegrityError("statement", {}, Exception("boom")),
    )
    repository = SQLAlchemyCurrencyOutputAdapter(cast(Any, session))

    monkeypatch.setattr(
        currency_repository_module,
        "is_unique_violation",
        lambda exc, constraint_name: False,
    )

    with pytest.raises(IntegrityError):
        await repository.update_currency(
            1,
            CurrencyChanges(
                iso_code="BRL",
                iso_numeric="986",
                name="Brazilian Real",
                symbol="R$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_update_currency_raises_conflict_when_unique_violation_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        scalar_results=(_build_currency_record(),),
        flush_error=IntegrityError("statement", {}, Exception("boom")),
    )
    repository = SQLAlchemyCurrencyOutputAdapter(cast(Any, session))

    monkeypatch.setattr(
        currency_repository_module,
        "is_unique_violation",
        lambda exc, constraint_name: True,
    )

    with pytest.raises(CurrencyISOCodeConflictOutputPortError):
        await repository.update_currency(
            1,
            CurrencyChanges(
                iso_code="BRL",
                iso_numeric="986",
                name="Brazilian Real",
                symbol="R$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_hard_delete_currency_raises_not_found_when_record_is_missing() -> None:
    repository = SQLAlchemyCurrencyOutputAdapter(cast(Any, _FakeSession()))

    with pytest.raises(CurrencyNotFoundOutputPortError):
        await repository.hard_delete_currency(1)

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.core.ports.output.ledger_account_output_port import (
    LedgerAccountNotFoundOutputPortError,
)
from src.infra.postgres.aggregates.ledger_account.repository import (
    SQLAlchemyLedgerAccountOutputAdapter,
)


class _FakeSession:
    def __init__(self, *, scalar_results: tuple[object | None, ...] = ()) -> None:
        self._scalar_results = list(scalar_results)

    async def scalar(self, statement: object) -> object | None:
        del statement
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    async def delete(self, value: object) -> None:
        del value

    async def flush(self) -> None:
        return None


def _build_ledger_account_record(**overrides: Any) -> SimpleNamespace:
    timestamp = datetime(2026, 5, 1, tzinfo=UTC)
    values = {
        "id": 1,
        "title": "Main Account",
        "type": "ASSET",
        "kind": "BANK_ACCOUNT",
        "currency_iso_code": "BRL",
        "created_at": timestamp,
        "updated_at": timestamp,
        "is_deleted": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.anyio
async def test_get_ledger_account_by_id_returns_domain_account_when_record_exists() -> (
    None
):
    repository = SQLAlchemyLedgerAccountOutputAdapter(
        cast(Any, _FakeSession(scalar_results=(_build_ledger_account_record(),))),
    )

    ledger_account = await repository.get_ledger_account_by_id(1)

    assert ledger_account is not None
    assert ledger_account.id == 1
    assert ledger_account.title == "Main Account"


@pytest.mark.anyio
async def test_hard_delete_ledger_account_raises_not_found_when_record_is_missing() -> (
    None
):
    repository = SQLAlchemyLedgerAccountOutputAdapter(cast(Any, _FakeSession()))

    with pytest.raises(LedgerAccountNotFoundOutputPortError):
        await repository.hard_delete_ledger_account(1)

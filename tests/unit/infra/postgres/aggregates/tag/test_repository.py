from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.core.ports.output.tag_output_port import TagNotFoundOutputPortError
from src.infra.postgres.aggregates.tag.repository import SQLAlchemyTagOutputAdapter


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


def _build_tag_record(**overrides: Any) -> SimpleNamespace:
    timestamp = datetime(2026, 5, 1, tzinfo=UTC)
    values = {
        "id": 1,
        "title": "Food",
        "created_at": timestamp,
        "updated_at": timestamp,
        "is_deleted": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.anyio
async def test_get_tag_by_id_returns_domain_tag_when_record_exists() -> None:
    repository = SQLAlchemyTagOutputAdapter(
        cast(Any, _FakeSession(scalar_results=(_build_tag_record(),))),
    )

    tag = await repository.get_tag_by_id(1)

    assert tag is not None
    assert tag.id == 1
    assert tag.title == "Food"


@pytest.mark.anyio
async def test_hard_delete_tag_raises_not_found_when_record_is_missing() -> None:
    repository = SQLAlchemyTagOutputAdapter(cast(Any, _FakeSession()))

    with pytest.raises(TagNotFoundOutputPortError):
        await repository.hard_delete_tag(1)

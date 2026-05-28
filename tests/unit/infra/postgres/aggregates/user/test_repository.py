from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.domain.user import NewUser, UserChanges
from src.core.ports.output.user_output_port import (
    UserEmailConflictOutputPortError,
    UserNotFoundOutputPortError,
)
from src.infra.postgres.aggregates.user import repository as user_repository_module
from src.infra.postgres.aggregates.user.repository import SQLAlchemyUserOutputAdapter


class _FakeSession:
    def __init__(
        self,
        *,
        scalar_results: tuple[object | None, ...] = (),
        flush_error: Exception | None = None,
    ) -> None:
        self._scalar_results = list(scalar_results)
        self._flush_error = flush_error

    def add(self, value: object) -> None:
        del value

    async def scalar(self, statement: object) -> object | None:
        del statement
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    async def flush(self) -> None:
        if self._flush_error is not None:
            raise self._flush_error

    async def refresh(self, value: object) -> None:
        del value

    async def delete(self, value: object) -> None:
        del value


def _build_user_record(**overrides: Any) -> SimpleNamespace:
    timestamp = datetime(2026, 5, 1, tzinfo=UTC)
    values = {
        "id": 1,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "password_hash": "hashed::plain-password",
        "birth_date": date(1815, 12, 10),
        "created_at": timestamp,
        "updated_at": timestamp,
        "is_deleted": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.anyio
async def test_get_user_by_email_returns_domain_user_when_record_exists() -> None:
    repository = SQLAlchemyUserOutputAdapter(
        cast(Any, _FakeSession(scalar_results=(_build_user_record(),))),
    )

    user = await repository.get_user_by_email("ada@example.com")

    assert user is not None
    assert user.id == 1
    assert user.email == "ada@example.com"


@pytest.mark.anyio
async def test_update_user_reraises_integrity_error_when_violation_is_unmapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        scalar_results=(_build_user_record(),),
        flush_error=IntegrityError("statement", {}, Exception("boom")),
    )
    repository = SQLAlchemyUserOutputAdapter(cast(Any, session))

    monkeypatch.setattr(
        user_repository_module,
        "is_unique_violation",
        lambda exc, constraint_name: False,
    )

    with pytest.raises(IntegrityError):
        await repository.update_user(
            1,
            UserChanges(
                first_name="Grace",
                last_name="Hopper",
                email="grace@example.com",
                password_hash="hashed::new-password",
                birth_date=date(1906, 12, 9),
            ),
        )


@pytest.mark.anyio
async def test_create_user_reraises_integrity_error_when_violation_is_unmapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        flush_error=IntegrityError("statement", {}, Exception("boom")),
    )
    repository = SQLAlchemyUserOutputAdapter(cast(Any, session))

    monkeypatch.setattr(
        user_repository_module,
        "is_unique_violation",
        lambda exc, constraint_name: False,
    )

    with pytest.raises(IntegrityError):
        await repository.create_user(
            NewUser(
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.com",
                password_hash="hashed::plain-password",
                birth_date=date(1815, 12, 10),
            ),
        )


@pytest.mark.anyio
async def test_update_user_raises_conflict_when_unique_violation_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession(
        scalar_results=(_build_user_record(),),
        flush_error=IntegrityError("statement", {}, Exception("boom")),
    )
    repository = SQLAlchemyUserOutputAdapter(cast(Any, session))

    monkeypatch.setattr(
        user_repository_module,
        "is_unique_violation",
        lambda exc, constraint_name: True,
    )

    with pytest.raises(UserEmailConflictOutputPortError):
        await repository.update_user(
            1,
            UserChanges(
                first_name="Grace",
                last_name="Hopper",
                email="grace@example.com",
                password_hash="hashed::new-password",
                birth_date=date(1906, 12, 9),
            ),
        )


@pytest.mark.anyio
async def test_hard_delete_user_raises_not_found_when_record_is_missing() -> None:
    repository = SQLAlchemyUserOutputAdapter(cast(Any, _FakeSession()))

    with pytest.raises(UserNotFoundOutputPortError):
        await repository.hard_delete_user(1)

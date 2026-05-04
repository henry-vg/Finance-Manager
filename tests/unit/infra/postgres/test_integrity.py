from sqlalchemy.exc import IntegrityError

from src.infra.postgres.integrity import get_constraint_name, is_unique_violation


class _FakeDiag:
    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name


class _FakeDatabaseError(Exception):
    def __init__(
        self,
        *,
        sqlstate: str | None,
        constraint_name: str | None = None,
        diag_constraint_name: str | None = None,
        message: str = "error",
    ) -> None:
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name
        self.diag = _FakeDiag(diag_constraint_name)
        self._message = message

    def __str__(self) -> str:
        return self._message


def _build_integrity_error(orig: Exception) -> IntegrityError:
    return IntegrityError("statement", {}, orig)


def test_get_constraint_name_prefers_direct_attribute() -> None:
    exc = _build_integrity_error(
        _FakeDatabaseError(
            sqlstate="23505",
            constraint_name="uq_users_email",
        ),
    )

    assert get_constraint_name(exc) == "uq_users_email"


def test_get_constraint_name_falls_back_to_diag() -> None:
    exc = _build_integrity_error(
        _FakeDatabaseError(
            sqlstate="23505",
            diag_constraint_name="uq_users_email",
        ),
    )

    assert get_constraint_name(exc) == "uq_users_email"


def test_is_unique_violation_matches_named_constraint() -> None:
    exc = _build_integrity_error(
        _FakeDatabaseError(
            sqlstate="23505",
            constraint_name="uq_users_email",
        ),
    )

    assert is_unique_violation(exc, constraint_name="uq_users_email") is True


def test_is_unique_violation_falls_back_to_error_message() -> None:
    exc = _build_integrity_error(
        _FakeDatabaseError(
            sqlstate="23505",
            message="duplicate key value violates unique constraint uq_users_email",
        ),
    )

    assert is_unique_violation(exc, constraint_name="uq_users_email") is True


def test_is_unique_violation_rejects_other_constraints() -> None:
    exc = _build_integrity_error(
        _FakeDatabaseError(
            sqlstate="23505",
            constraint_name="uq_other_constraint",
        ),
    )

    assert is_unique_violation(exc, constraint_name="uq_users_email") is False

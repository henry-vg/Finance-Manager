from typing import cast

from sqlalchemy.exc import IntegrityError

_POSTGRES_UNIQUE_VIOLATION_SQLSTATE = "23505"


def get_constraint_name(exc: IntegrityError) -> str | None:
    if exc.orig is None:
        return None

    constraint_name = getattr(exc.orig, "constraint_name", None)

    if constraint_name is not None:
        return cast(str, constraint_name)

    diag = getattr(exc.orig, "diag", None)
    if diag is None:
        return None

    return cast(str | None, getattr(diag, "constraint_name", None))


def is_unique_violation(
    exc: IntegrityError,
    *,
    constraint_name: str,
) -> bool:
    if exc.orig is None:
        return False

    sqlstate = getattr(exc.orig, "sqlstate", None)
    actual_constraint_name = get_constraint_name(exc)

    return sqlstate == _POSTGRES_UNIQUE_VIOLATION_SQLSTATE and (
        actual_constraint_name == constraint_name or constraint_name in str(exc.orig)
    )

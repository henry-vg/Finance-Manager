from typing import Any, cast

from sqlalchemy import Date, String, UniqueConstraint

from src.infra.postgres.aggregates.user.models.users import (
    USER_EMAIL_UNIQUE_CONSTRAINT_NAME,
    UserRecord,
)


def test_user_record_declares_expected_table_name() -> None:
    assert UserRecord.__tablename__ == "users"


def test_user_record_table_matches_expected_shape_and_constraints() -> None:
    users_table = cast(Any, UserRecord).__table__
    constraints_by_name = {
        constraint.name: constraint
        for constraint in users_table.constraints
        if constraint.name is not None
    }

    assert set(users_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "first_name",
        "last_name",
        "email",
        "password_hash",
        "birth_date",
    }
    assert list(users_table.primary_key.columns.keys()) == ["id"]
    assert isinstance(users_table.c.first_name.type, String)
    assert isinstance(users_table.c.last_name.type, String)
    assert isinstance(users_table.c.email.type, String)
    assert isinstance(users_table.c.password_hash.type, String)
    assert isinstance(users_table.c.birth_date.type, Date)
    assert isinstance(
        constraints_by_name[USER_EMAIL_UNIQUE_CONSTRAINT_NAME],
        UniqueConstraint,
    )

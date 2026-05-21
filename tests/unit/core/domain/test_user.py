from datetime import UTC, date, datetime

import pytest

from src.core.domain.user import (
    CreateUserData,
    NewUser,
    UpdateUserData,
    User,
    UserChanges,
    UserEmailConflictError,
    UserNotFoundError,
    UserSortableField,
)


def _timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def test_user_keeps_persisted_fields() -> None:
    user = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::value",
        birth_date=date(1815, 12, 10),
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
    )

    assert user.id == 1
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"
    assert user.email == "ada@example.com"
    assert user.password_hash == "hashed::value"
    assert user.birth_date == date(1815, 12, 10)
    assert user.created_at == _timestamp(1)
    assert user.updated_at == _timestamp(2)


@pytest.mark.parametrize("factory", [NewUser, UserChanges])
def test_user_write_models_keep_hashed_password_fields(
    factory: type[NewUser | UserChanges],
) -> None:
    user_data = factory(
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password_hash="hashed::new-password",
        birth_date=date(1906, 12, 9),
    )

    assert user_data.first_name == "Grace"
    assert user_data.last_name == "Hopper"
    assert user_data.email == "grace@example.com"
    assert user_data.password_hash == "hashed::new-password"
    assert user_data.birth_date == date(1906, 12, 9)


@pytest.mark.parametrize("factory", [CreateUserData, UpdateUserData])
def test_user_input_models_keep_plain_password_fields(
    factory: type[CreateUserData | UpdateUserData],
) -> None:
    user_data = factory(
        first_name="Katherine",
        last_name="Johnson",
        email="katherine@example.com",
        password="plain-password",
        birth_date=date(1918, 8, 26),
    )

    assert user_data.first_name == "Katherine"
    assert user_data.last_name == "Johnson"
    assert user_data.email == "katherine@example.com"
    assert user_data.password == "plain-password"
    assert user_data.birth_date == date(1918, 8, 26)


def test_user_sortable_field_exposes_all_public_members() -> None:
    assert tuple(UserSortableField.__members__) == (
        "ID",
        "CREATED_AT",
        "UPDATED_AT",
        "FIRST_NAME",
        "LAST_NAME",
        "EMAIL",
        "BIRTH_DATE",
    )


@pytest.mark.parametrize(
    "error_type",
    [UserNotFoundError, UserEmailConflictError],
)
def test_user_errors_are_domain_exceptions(error_type: type[Exception]) -> None:
    assert isinstance(error_type(), Exception)

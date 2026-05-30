import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from src.adapters.input.api.schemas.user_schema import CreateUserRequest, UserResponse


def test_user_response_serializes_date_and_datetime_fields() -> None:
    response = UserResponse(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        birth_date=date(1815, 12, 10),
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    payload = json.loads(response.model_dump_json())

    assert payload["birth_date"] == "1815-12-10"
    assert payload["email"] == "ada@example.com"


def test_create_user_request_rejects_blank_first_name() -> None:
    with pytest.raises(ValidationError):
        CreateUserRequest(
            first_name="",
            last_name="Lovelace",
            email="ada@example.com",
            password="plain-password",
            birth_date=date(1815, 12, 10),
        )

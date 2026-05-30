import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.adapters.input.api.schemas.tag_schema import CreateTagRequest, TagResponse


def test_tag_response_serializes_timestamp_fields() -> None:
    response = TagResponse(
        id=1,
        title="Food",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
    )

    payload = json.loads(response.model_dump_json())

    assert payload == {
        "id": 1,
        "title": "Food",
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
    }


def test_create_tag_request_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        CreateTagRequest(title="")

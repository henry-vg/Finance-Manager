import json
from datetime import UTC, datetime

from src.adapters.input.api.schemas.tag_schema import TagResponse


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

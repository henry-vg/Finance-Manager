import json
from datetime import UTC, date, datetime

from src.adapters.input.api.schemas.pagination_schema import PageResponse
from src.adapters.input.api.schemas.user_schema import UserResponse


def test_page_response_serializes_nested_items_with_api_schema_rules() -> None:
    response = PageResponse[UserResponse](
        items=[
            UserResponse(
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.com",
                birth_date=date(1815, 12, 10),
                created_at=datetime(
                    2026,
                    5,
                    3,
                    12,
                    30,
                    15,
                    123000,
                    tzinfo=UTC,
                ),
                updated_at=datetime(
                    2026,
                    5,
                    4,
                    9,
                    45,
                    30,
                    456000,
                    tzinfo=UTC,
                ),
            ),
        ],
        offset=10,
        limit=50,
        total=120,
    )

    payload = json.loads(response.model_dump_json())

    assert payload == {
        "items": [
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "birth_date": "1815-12-10",
                "created_at": "2026-05-03T12:30:15.123Z",
                "updated_at": "2026-05-04T09:45:30.456Z",
            },
        ],
        "offset": 10,
        "limit": 50,
        "total": 120,
    }

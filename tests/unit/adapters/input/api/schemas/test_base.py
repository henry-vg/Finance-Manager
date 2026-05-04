from datetime import UTC, datetime, timedelta

from src.adapters.input.api.schemas import ApiSchemaBase


class _TimestampSchema(ApiSchemaBase):
    created_at: datetime


def test_api_schema_base_serializes_datetimes_as_utc_with_milliseconds_and_z() -> None:
    schema = _TimestampSchema(
        created_at=datetime(
            2026,
            5,
            3,
            14,
            35,
            18,
            123456,
            tzinfo=UTC,
        )
        + timedelta(hours=3),
    )

    assert schema.model_dump(mode="json") == {
        "created_at": "2026-05-03T17:35:18.123Z",
    }

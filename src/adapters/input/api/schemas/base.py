from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, model_serializer


def format_api_datetime(
    value: datetime,
) -> str:
    return (
        value.astimezone(UTC)
        .isoformat(timespec="milliseconds")
        .replace(
            "+00:00",
            "Z",
        )
    )


def _normalize_api_value(
    value: Any,
) -> Any:
    if isinstance(value, BaseModel):
        return {
            key: _normalize_api_value(nested_value)
            for key, nested_value in value.model_dump(mode="python").items()
        }

    if isinstance(value, datetime):
        return format_api_datetime(value)

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {
            key: _normalize_api_value(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_api_value(item) for item in value]

    return value


class ApiSchemaBase(BaseModel):
    @model_serializer(mode="plain", when_used="json")
    def serialize_model(self) -> Any:
        return _normalize_api_value(self)

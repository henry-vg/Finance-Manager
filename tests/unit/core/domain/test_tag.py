from datetime import UTC, datetime

import pytest

from src.core.domain.tag import (
    CreateTagData,
    NewTag,
    Tag,
    TagChanges,
    TagNotFoundError,
    TagSortableField,
    UpdateTagData,
)


def _timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def test_tag_keeps_persisted_fields() -> None:
    tag = Tag(
        id=1,
        title="Food",
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
    )

    assert tag.id == 1
    assert tag.title == "Food"
    assert tag.created_at == _timestamp(1)
    assert tag.updated_at == _timestamp(2)


@pytest.mark.parametrize(
    "factory",
    [NewTag, TagChanges, CreateTagData, UpdateTagData],
)
def test_tag_write_models_keep_title(
    factory: type[NewTag | TagChanges | CreateTagData | UpdateTagData],
) -> None:
    tag_data = factory(title="Utilities")

    assert tag_data.title == "Utilities"


def test_tag_sortable_field_exposes_all_public_members() -> None:
    assert tuple(TagSortableField.__members__) == (
        "ID",
        "CREATED_AT",
        "UPDATED_AT",
        "TITLE",
    )


def test_tag_not_found_error_is_domain_exception() -> None:
    assert isinstance(TagNotFoundError(), Exception)

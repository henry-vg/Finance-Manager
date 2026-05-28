from enum import StrEnum

import pytest
from fastapi.exceptions import RequestValidationError

from src.adapters.input.api.pagination import (
    EndpointSortField,
    ListQuerySortConfig,
    _build_sort_description,
    create_list_query_dependency,
)
from src.core.shared import SortDirection, SortTerm

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500


class _ListItemSortField(StrEnum):
    FIRST_NAME = "first_name"
    CREATED_AT = "created_at"
    CREATED = "created"


def _build_list_query_dependency():
    return create_list_query_dependency(
        default_limit=DEFAULT_PAGE_LIMIT,
        max_limit=MAX_PAGE_LIMIT,
        sort_config=ListQuerySortConfig(
            fields=(
                EndpointSortField(
                    query_name=_ListItemSortField.FIRST_NAME.value,
                    item_field_name="first_name",
                ),
                EndpointSortField(
                    query_name=_ListItemSortField.CREATED_AT.value,
                    item_field_name="created_at",
                ),
            ),
            default_sort=(f"-{_ListItemSortField.CREATED_AT.value}",),
        ),
    )


def _build_alias_list_query_dependency():
    return create_list_query_dependency(
        default_limit=DEFAULT_PAGE_LIMIT,
        max_limit=MAX_PAGE_LIMIT,
        sort_config=ListQuerySortConfig(
            fields=(
                EndpointSortField(
                    query_name=_ListItemSortField.CREATED.value,
                    item_field_name="created_at",
                ),
            ),
        ),
    )


def test_get_list_query_uses_default_limit() -> None:
    query = _build_list_query_dependency()()

    assert query.offset == 0
    assert query.limit == DEFAULT_PAGE_LIMIT
    assert query.sort == (
        SortTerm(
            field="created_at",
            direction=SortDirection.DESC,
        ),
    )


def test_get_list_query_accepts_custom_offset_and_limit() -> None:
    query = _build_list_query_dependency()(
        offset=15,
        limit=120,
        sort="first_name,+created_at",
    )

    assert query.offset == 15
    assert query.limit == 120
    assert query.sort == (
        SortTerm(
            field="first_name",
            direction=SortDirection.ASC,
        ),
        SortTerm(
            field="created_at",
            direction=SortDirection.ASC,
        ),
    )


def test_get_list_query_accepts_maximum_limit() -> None:
    query = _build_list_query_dependency()(
        offset=0,
        limit=MAX_PAGE_LIMIT,
    )

    assert query.limit == MAX_PAGE_LIMIT


def test_get_list_query_rejects_sort_field_outside_endpoint_whitelist() -> None:
    with pytest.raises(RequestValidationError, match="Invalid sort field"):
        _build_list_query_dependency()(
            sort="hidden_value",
        )


def test_get_list_query_rejects_empty_sort_term() -> None:
    with pytest.raises(RequestValidationError, match="cannot be empty"):
        _build_list_query_dependency()(
            sort="first_name,,created_at",
        )


def test_get_list_query_maps_public_sort_alias_to_internal_field() -> None:
    query = _build_alias_list_query_dependency()(
        sort="-created",
    )

    assert query.sort == (
        SortTerm(
            field="created_at",
            direction=SortDirection.DESC,
        ),
    )


def test_build_sort_description_includes_allowed_fields_and_default_sort() -> None:
    description = _build_sort_description(
        ListQuerySortConfig(
            fields=(
                EndpointSortField(
                    query_name="first_name",
                    item_field_name="first_name",
                ),
                EndpointSortField(
                    query_name="created_at",
                    item_field_name="created_at",
                ),
            ),
            default_sort=("-created_at",),
        ),
    )

    assert "Allowed fields: first_name, created_at." in description
    assert "Default sort: -created_at." in description


def test_get_list_query_rejects_sorting_when_endpoint_has_no_sort_config() -> None:
    dependency = create_list_query_dependency(
        default_limit=DEFAULT_PAGE_LIMIT,
        max_limit=MAX_PAGE_LIMIT,
        sort_config=None,
    )

    with pytest.raises(RequestValidationError, match="Sorting is not enabled"):
        dependency(sort="first_name")


def test_get_list_query_rejects_sort_token_without_field_name() -> None:
    with pytest.raises(RequestValidationError, match="Sort fields cannot be empty"):
        _build_list_query_dependency()(sort="-")


def test_get_list_query_returns_empty_sort_when_sorting_is_disabled_and_omitted() -> (
    None
):
    dependency = create_list_query_dependency(
        default_limit=DEFAULT_PAGE_LIMIT,
        max_limit=MAX_PAGE_LIMIT,
        sort_config=None,
    )

    query = dependency(offset=3, limit=7)

    assert query.offset == 3
    assert query.limit == 7
    assert query.sort == ()

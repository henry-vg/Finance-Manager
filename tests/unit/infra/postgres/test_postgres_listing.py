from collections.abc import Mapping
from enum import IntEnum, StrEnum
from typing import Any

import pytest
from sqlalchemy import column

from src.core.shared import SortDirection, SortTerm
from src.infra.postgres.listing import build_order_clauses


class _SortableField(StrEnum):
    ID = "id"
    NAME = "name"
    CREATED_AT = "created_at"


class _InternalSortableField(IntEnum):
    ID = 1
    CREATED_AT = 2


def _build_sort_columns() -> Mapping[_SortableField, Any]:
    return {
        _SortableField.ID: column("id"),
        _SortableField.NAME: column("name"),
        _SortableField.CREATED_AT: column("created_at"),
    }


def test_build_order_clauses_rejects_empty_sort_terms() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        build_order_clauses(
            sort_terms=(),
            sort_field_enum=_SortableField,
            sort_columns=_build_sort_columns(),
        )


def test_build_order_clauses_builds_single_ascending_clause() -> None:
    clauses = build_order_clauses(
        sort_terms=(
            SortTerm(
                field=_SortableField.NAME.value,
                direction=SortDirection.ASC,
            ),
        ),
        sort_field_enum=_SortableField,
        sort_columns=_build_sort_columns(),
    )

    assert [str(clause) for clause in clauses] == ["name ASC"]


def test_build_order_clauses_preserves_multi_sort_order() -> None:
    clauses = build_order_clauses(
        sort_terms=(
            SortTerm(
                field=_SortableField.NAME.value,
                direction=SortDirection.ASC,
            ),
            SortTerm(
                field=_SortableField.CREATED_AT.value,
                direction=SortDirection.DESC,
            ),
        ),
        sort_field_enum=_SortableField,
        sort_columns=_build_sort_columns(),
    )

    assert [str(clause) for clause in clauses] == [
        "name ASC",
        "created_at DESC",
    ]


def test_build_order_clauses_appends_tie_break_when_not_explicit() -> None:
    clauses = build_order_clauses(
        sort_terms=(
            SortTerm(
                field=_SortableField.CREATED_AT.value,
                direction=SortDirection.DESC,
            ),
        ),
        sort_field_enum=_SortableField,
        sort_columns=_build_sort_columns(),
        tie_break_field=_SortableField.ID,
        tie_break_direction=SortDirection.DESC,
    )

    assert [str(clause) for clause in clauses] == [
        "created_at DESC",
        "id DESC",
    ]


def test_build_order_clauses_skips_tie_break_when_already_explicit() -> None:
    clauses = build_order_clauses(
        sort_terms=(
            SortTerm(
                field=_SortableField.ID.value,
                direction=SortDirection.ASC,
            ),
        ),
        sort_field_enum=_SortableField,
        sort_columns=_build_sort_columns(),
        tie_break_field=_SortableField.ID,
        tie_break_direction=SortDirection.DESC,
    )

    assert [str(clause) for clause in clauses] == ["id ASC"]


def test_build_order_clauses_rejects_unsupported_sort_field() -> None:
    with pytest.raises(ValueError, match="Unsupported sort field"):
        build_order_clauses(
            sort_terms=(
                SortTerm(
                    field="missing",
                    direction=SortDirection.ASC,
                ),
            ),
            sort_field_enum=_SortableField,
            sort_columns=_build_sort_columns(),
        )


def test_build_order_clauses_supports_name_derived_internal_enum_fields() -> None:
    clauses = build_order_clauses(
        sort_terms=(
            SortTerm(
                field=_InternalSortableField.CREATED_AT.name.lower(),
                direction=SortDirection.DESC,
            ),
        ),
        sort_field_enum=_InternalSortableField,
        sort_columns={
            _InternalSortableField.ID: column("id"),
            _InternalSortableField.CREATED_AT: column("created_at"),
        },
        tie_break_field=_InternalSortableField.ID,
        tie_break_direction=SortDirection.DESC,
    )

    assert [str(clause) for clause in clauses] == [
        "created_at DESC",
        "id DESC",
    ]

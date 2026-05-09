from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from src.core.shared import SortDirection, SortTerm


def _resolve_sort_field[SortableFieldT: Enum](
    *,
    sort_field_enum: type[SortableFieldT],
    raw_field: str,
) -> SortableFieldT:
    try:
        return sort_field_enum(raw_field)
    except ValueError:
        try:
            return sort_field_enum[raw_field.upper()]
        except KeyError as exc:
            raise ValueError(f"Unsupported sort field '{raw_field}'") from exc


def _get_sort_field_identifier(
    sort_field: Enum,
) -> str:
    if isinstance(sort_field.value, str):
        return sort_field.value

    return sort_field.name.lower()


def build_order_clauses[SortableFieldT: Enum](
    *,
    sort_terms: Sequence[SortTerm],
    sort_field_enum: type[SortableFieldT],
    sort_columns: Mapping[SortableFieldT, Any],
    tie_break_field: SortableFieldT | None = None,
    tie_break_direction: SortDirection = SortDirection.DESC,
) -> tuple[Any, ...]:
    effective_sort_terms = tuple(sort_terms)

    if not effective_sort_terms:
        raise ValueError("Sort terms cannot be empty")

    order_clauses: list[Any] = []
    has_explicit_tie_break = False

    for sort_term in effective_sort_terms:
        try:
            sort_field = _resolve_sort_field(
                sort_field_enum=sort_field_enum,
                raw_field=sort_term.field,
            )
        except ValueError as exc:
            raise ValueError(f"Unsupported sort field '{sort_term.field}'") from exc

        column = sort_columns.get(sort_field)

        if column is None:
            raise ValueError(
                f"Unsupported sort field '{sort_term.field}'",
            )

        has_explicit_tie_break = has_explicit_tie_break or (
            tie_break_field is not None and sort_field == tie_break_field
        )
        order_clauses.append(
            column.desc()
            if sort_term.direction == SortDirection.DESC
            else column.asc(),
        )

    if tie_break_field is not None and not has_explicit_tie_break:
        tie_break_column = sort_columns.get(tie_break_field)

        if tie_break_column is None:
            raise ValueError(
                "Unsupported sort field "
                f"'{_get_sort_field_identifier(tie_break_field)}'",
            )

        order_clauses.append(
            tie_break_column.desc()
            if tie_break_direction == SortDirection.DESC
            else tie_break_column.asc(),
        )

    return tuple(order_clauses)

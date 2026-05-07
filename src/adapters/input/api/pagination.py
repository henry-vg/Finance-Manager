from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, NoReturn

from fastapi import Query
from fastapi.exceptions import RequestValidationError

from src.core.shared import ListQuery, SortDirection, SortTerm


@dataclass(frozen=True)
class EndpointSortField:
    query_name: str
    item_field_name: str


@dataclass(frozen=True)
class ListQuerySortConfig:
    fields: tuple[EndpointSortField, ...] = ()
    default_sort: tuple[str, ...] = ()


def _build_sort_description(
    sort_config: ListQuerySortConfig | None,
) -> str:
    description = (
        "Comma-separated sort fields. Prefix each term with '+' for ascending "
        "or '-' for descending; '+' is assumed when omitted."
    )

    if sort_config is None or not sort_config.fields:
        return description

    allowed_fields = ", ".join(field.query_name for field in sort_config.fields)
    default_sort = ", ".join(sort_config.default_sort) or "none"

    return (
        f"{description} Allowed fields: {allowed_fields}. Default sort: {default_sort}."
    )


def _raise_sort_validation_error(
    *,
    sort_value: str,
    message: str,
) -> NoReturn:
    raise RequestValidationError(
        errors=[
            {
                "type": "value_error",
                "loc": ("query", "sort"),
                "msg": message,
                "input": sort_value,
            },
        ],
    )


def _parse_single_sort_token(
    *,
    raw_token: str,
    sort_mapping: dict[str, EndpointSortField],
    original_value: str,
) -> SortTerm:
    token = raw_token.strip()

    if not token:
        _raise_sort_validation_error(
            sort_value=original_value,
            message="Sort terms cannot be empty",
        )

    direction = SortDirection.ASC
    field_name = token

    if token[0] in "+-":
        direction = SortDirection.DESC if token[0] == "-" else SortDirection.ASC
        field_name = token[1:]

    if not field_name:
        _raise_sort_validation_error(
            sort_value=original_value,
            message="Sort fields cannot be empty",
        )

    endpoint_sort_field = sort_mapping.get(field_name)

    if endpoint_sort_field is None:
        allowed_fields = ", ".join(sorted(sort_mapping)) or "none"
        _raise_sort_validation_error(
            sort_value=original_value,
            message=(
                f"Invalid sort field '{field_name}'. Allowed fields: {allowed_fields}."
            ),
        )

    return SortTerm(
        field=endpoint_sort_field.item_field_name,
        direction=direction,
    )


def _parse_sort_terms(
    *,
    raw_sort: str | None,
    sort_config: ListQuerySortConfig | None,
) -> tuple[SortTerm, ...]:
    if raw_sort is None:
        raw_tokens = tuple(sort_config.default_sort if sort_config is not None else ())
    else:
        raw_tokens = tuple(raw_sort.split(","))

    if not raw_tokens:
        return ()

    sort_mapping = {
        field.query_name: field for field in (sort_config.fields if sort_config else ())
    }
    sort_value = raw_sort if raw_sort is not None else ",".join(raw_tokens)

    if not sort_mapping and raw_tokens:
        _raise_sort_validation_error(
            sort_value=sort_value,
            message="Sorting is not enabled for this endpoint",
        )

    return tuple(
        _parse_single_sort_token(
            raw_token=raw_token,
            sort_mapping=sort_mapping,
            original_value=sort_value,
        )
        for raw_token in raw_tokens
    )


def create_list_query_dependency(
    *,
    default_limit: int,
    max_limit: int,
    sort_config: ListQuerySortConfig | None = None,
) -> Callable[..., ListQuery]:
    def get_list_query(
        offset: Annotated[
            int,
            Query(
                ge=0,
                description="Number of items to skip before collecting results.",
            ),
        ] = 0,
        limit: Annotated[
            int,
            Query(
                ge=1,
                le=max_limit,
                description=(
                    "Maximum number of items to return. Defaults to "
                    f"{default_limit} and is capped at {max_limit}."
                ),
            ),
        ] = default_limit,
        sort: Annotated[
            str | None,
            Query(
                description=_build_sort_description(sort_config),
            ),
        ] = None,
    ) -> ListQuery:
        return ListQuery(
            offset=offset,
            limit=limit,
            sort=_parse_sort_terms(
                raw_sort=sort,
                sort_config=sort_config,
            ),
        )

    return get_list_query

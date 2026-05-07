from collections.abc import Callable
from typing import Annotated

from fastapi import Query

from src.core.shared import ListQuery


def create_list_query_dependency(
    *,
    default_limit: int,
    max_limit: int,
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
    ) -> ListQuery:
        return ListQuery(
            offset=offset,
            limit=limit,
        )

    return get_list_query

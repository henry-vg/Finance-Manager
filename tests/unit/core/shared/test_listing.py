import pytest
from pydantic import ValidationError

from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def test_list_query_accepts_valid_offset_and_limit() -> None:
    query = ListQuery(
        offset=10,
        limit=50,
    )

    assert query.offset == 10
    assert query.limit == 50
    assert query.sort == ()


def test_list_query_accepts_structured_sort_terms() -> None:
    query = ListQuery(
        offset=0,
        limit=10,
        sort=(
            SortTerm(
                field="created_at",
                direction=SortDirection.DESC,
            ),
            SortTerm(
                field="email",
                direction=SortDirection.ASC,
            ),
        ),
    )

    assert query.sort == (
        SortTerm(
            field="created_at",
            direction=SortDirection.DESC,
        ),
        SortTerm(
            field="email",
            direction=SortDirection.ASC,
        ),
    )


def test_list_query_rejects_negative_offset() -> None:
    with pytest.raises(ValidationError, match="offset"):
        ListQuery(
            offset=-1,
            limit=50,
        )


def test_list_query_rejects_non_positive_limit() -> None:
    with pytest.raises(ValidationError, match="limit"):
        ListQuery(
            offset=0,
            limit=0,
        )


def test_page_accepts_valid_shape() -> None:
    page = Page(
        items=["a", "b"],
        offset=0,
        limit=2,
        total=10,
    )

    assert page.items == ["a", "b"]
    assert page.offset == 0
    assert page.limit == 2
    assert page.total == 10


def test_page_rejects_negative_total() -> None:
    with pytest.raises(ValidationError, match="total"):
        Page(
            items=[],
            offset=0,
            limit=10,
            total=-1,
        )


def test_page_rejects_more_items_than_limit() -> None:
    with pytest.raises(ValidationError, match="items length"):
        Page(
            items=[1, 2],
            offset=0,
            limit=1,
            total=2,
        )


def test_sort_term_rejects_empty_field() -> None:
    with pytest.raises(ValidationError, match="field"):
        SortTerm(
            field="",
            direction=SortDirection.ASC,
        )
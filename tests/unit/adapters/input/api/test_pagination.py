from src.adapters.input.api.pagination import create_list_query_dependency

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500


def _build_list_query_dependency():
    return create_list_query_dependency(
        default_limit=DEFAULT_PAGE_LIMIT,
        max_limit=MAX_PAGE_LIMIT,
    )


def test_get_list_query_uses_default_limit() -> None:
    query = _build_list_query_dependency()()

    assert query.offset == 0
    assert query.limit == DEFAULT_PAGE_LIMIT


def test_get_list_query_accepts_custom_offset_and_limit() -> None:
    query = _build_list_query_dependency()(
        offset=15,
        limit=120,
    )

    assert query.offset == 15
    assert query.limit == 120


def test_get_list_query_accepts_maximum_limit() -> None:
    query = _build_list_query_dependency()(
        offset=0,
        limit=MAX_PAGE_LIMIT,
    )

    assert query.limit == MAX_PAGE_LIMIT

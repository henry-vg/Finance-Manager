import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.tag_route import create_router
from src.core.domain.tag import Tag
from src.core.shared import ListQuery, SortDirection, SortTerm
from tests.integration.fastapi.helpers.builders import (
    build_page_response,
    build_tag_create_payload,
    build_tag_response,
    build_tag_update_payload,
)
from tests.integration.fastapi.helpers.stubs import (
    TagInputPortStub as _TagInputPortStub,
)
from tests.integration.fastapi.helpers.stubs import (
    build_timestamp as _build_timestamp,
)


def _create_test_app(tag_input_port: _TagInputPortStub) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_router(
            tag_input_port=tag_input_port,
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )
    return app


@pytest.mark.anyio
async def test_get_tag_returns_tag_response() -> None:
    tag_input_port_stub = _TagInputPortStub()
    tag_input_port_stub.tags_by_id[1] = Tag(
        id=1,
        title="Food",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(tag_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/tag", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == build_tag_response()


@pytest.mark.anyio
async def test_get_tag_returns_404_when_tag_does_not_exist() -> None:
    app = _create_test_app(_TagInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/tag", params={"id": 1})

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found."


@pytest.mark.anyio
async def test_list_tags_returns_paginated_response() -> None:
    tag_input_port_stub = _TagInputPortStub()
    tag_input_port_stub.tags_by_id[1] = Tag(
        id=1,
        title="Food",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    tag_input_port_stub.tags_by_id[2] = Tag(
        id=2,
        title="Travel",
        created_at=_build_timestamp(2),
        updated_at=_build_timestamp(2),
    )
    app = _create_test_app(tag_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/tag/list",
            params={"offset": 0, "limit": 10, "sort": "title"},
        )

    assert response.status_code == 200
    assert response.json() == build_page_response(
        items=[
            build_tag_response(),
            build_tag_response(
                id=2,
                title="Travel",
                created_at="2026-05-02T00:00:00.000Z",
                updated_at="2026-05-02T00:00:00.000Z",
            ),
        ],
        limit=10,
        total=2,
    )
    assert tag_input_port_stub.list_tag_queries == [
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="title", direction=SortDirection.ASC),),
        ),
    ]


@pytest.mark.anyio
async def test_create_tag_returns_created_response() -> None:
    app = _create_test_app(_TagInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/tag", json=build_tag_create_payload())

    assert response.status_code == 201
    assert response.json() == build_tag_response()


@pytest.mark.anyio
async def test_update_tag_returns_404_when_tag_does_not_exist() -> None:
    app = _create_test_app(_TagInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/tag",
            params={"id": 1},
            json=build_tag_update_payload(),
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tag not found."


@pytest.mark.anyio
async def test_delete_tag_soft_deletes_by_default() -> None:
    tag_input_port_stub = _TagInputPortStub()
    tag_input_port_stub.tags_by_id[1] = Tag(
        id=1,
        title="Food",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(tag_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/tag", params={"id": 1})

    assert response.status_code == 204
    assert tag_input_port_stub.delete_calls == [(1, False)]


@pytest.mark.anyio
async def test_delete_tag_forwards_hard_delete_query_param() -> None:
    tag_input_port_stub = _TagInputPortStub()
    tag_input_port_stub.tags_by_id[1] = Tag(
        id=1,
        title="Food",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(tag_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/tag",
            params={"id": 1, "hard_delete": "true"},
        )

    assert response.status_code == 204
    assert tag_input_port_stub.delete_calls == [(1, True)]

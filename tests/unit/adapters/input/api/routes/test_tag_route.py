from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.tag_route import create_router
from src.core.domain.tag import CreateTagData, Tag, TagNotFoundError, UpdateTagData
from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class _TagInputPortStub:
    def __init__(self) -> None:
        self.tags_by_id: dict[int, Tag] = {}
        self.soft_deleted_tag_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_tag_queries: list[ListQuery] = []
        self._next_tag_id = 1

    async def list_tags(self, list_query: ListQuery) -> Page[Tag]:
        self.list_tag_queries.append(list_query)
        active_tags = [
            tag
            for tag_id, tag in self.tags_by_id.items()
            if tag_id not in self.soft_deleted_tag_ids
        ]
        active_tags.sort(key=lambda tag: (tag.title, tag.id))
        return Page[Tag](
            items=active_tags[list_query.offset : list_query.offset + list_query.limit],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_tags),
        )

    async def get_tag(self, tag_id: int) -> Tag:
        if tag_id in self.soft_deleted_tag_ids or tag_id not in self.tags_by_id:
            raise TagNotFoundError()
        return self.tags_by_id[tag_id]

    async def create_tag(self, data: CreateTagData) -> Tag:
        tag = Tag(
            id=self._next_tag_id,
            title=data.title,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.tags_by_id[tag.id] = tag
        self._next_tag_id += 1
        return tag

    async def update_tag(self, tag_id: int, data: UpdateTagData) -> Tag:
        current = await self.get_tag(tag_id)
        updated = Tag(
            id=current.id,
            title=data.title,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.tags_by_id[tag_id] = updated
        return updated

    async def delete_tag(self, tag_id: int, hard_delete: bool = False) -> None:
        self.delete_calls.append((tag_id, hard_delete))
        if tag_id in self.soft_deleted_tag_ids:
            if hard_delete:
                self.soft_deleted_tag_ids.remove(tag_id)
                self.tags_by_id.pop(tag_id, None)
                return
            raise TagNotFoundError()
        if tag_id not in self.tags_by_id:
            raise TagNotFoundError()
        if hard_delete:
            self.tags_by_id.pop(tag_id, None)
            return
        self.soft_deleted_tag_ids.add(tag_id)


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
    assert response.json() == {
        "id": 1,
        "title": "Food",
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
    }


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
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["title"] == "Food"
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
        response = await client.post("/tag", json={"title": "Food"})

    assert response.status_code == 201
    assert response.json()["title"] == "Food"


@pytest.mark.anyio
async def test_update_tag_returns_404_when_tag_does_not_exist() -> None:
    app = _create_test_app(_TagInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/tag",
            params={"id": 1},
            json={"title": "Utilities"},
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

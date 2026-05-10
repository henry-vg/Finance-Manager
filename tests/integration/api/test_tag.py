from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI

from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.domain.tag import CreateTagData, Tag, TagNotFoundError, UpdateTagData
from src.core.domain.user import CreateUserData, UpdateUserData, User
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.shared import ListQuery, Page
from src.infra.fastapi.app import create_http_app
from src.infra.settings import load_settings


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class _ReadyHealthzInputPortStub(HealthzInputPort):
    async def get_healthz_liveness(self) -> HealthzLiveness:
        return HealthzLiveness(status=HealthzStatus.OK)

    async def get_healthz_readiness(self) -> HealthzReadiness:
        return HealthzReadiness(
            status=HealthzStatus.OK,
            dependencies=HealthzReadinessDependencies(
                api=HealthzStatus.OK,
                database=HealthzStatus.OK,
            ),
        )


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
        active_tags.sort(key=lambda tag: tag.id)
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


class _UserInputPortStub(UserInputPort):
    async def list_users(self, list_query: ListQuery) -> Page[User]:
        return Page[User](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_user(self, email) -> User:
        return User(
            id=1,
            first_name="Ada",
            last_name="Lovelace",
            email=email,
            password_hash="hashed::plain-password",
            birth_date=date(1815, 12, 10),
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def create_user(self, data: CreateUserData) -> User:
        return User(
            id=1,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::plain-password",
            birth_date=data.birth_date,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )

    async def update_user(self, current_email, data: UpdateUserData) -> User:
        return User(
            id=1,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::plain-password",
            birth_date=data.birth_date,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def delete_user(self, email, hard_delete: bool = False) -> None:
        del email
        del hard_delete
        return None


def _create_test_app(tag_input_port: _TagInputPortStub) -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=_ReadyHealthzInputPortStub(),
        tag_input_port=tag_input_port,
        user_input_port=_UserInputPortStub(),
    )


@pytest.mark.anyio
async def test_tag_crud_flow_through_http_app() -> None:
    tag_input_port_stub = _TagInputPortStub()
    app = _create_test_app(tag_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post("/tag", json={"title": "Food"})
        created_id = create_response.json()["id"]
        get_response = await client.get("/tag", params={"id": created_id})
        list_response = await client.get("/tag/list")
        update_response = await client.put(
            "/tag",
            params={"id": created_id},
            json={"title": "Utilities"},
        )
        delete_response = await client.delete("/tag", params={"id": created_id})

    assert create_response.status_code == 201
    assert create_response.json()["title"] == "Food"
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_id
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Utilities"
    assert delete_response.status_code == 204

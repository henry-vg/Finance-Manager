from datetime import date

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.user_route import create_router
from src.core.domain.user import User
from src.core.shared import ListQuery, SortDirection, SortTerm
from tests.integration.fastapi.helpers.builders import (
    build_page_response,
    build_updated_user_response,
    build_user_create_payload,
    build_user_response,
    build_user_update_payload,
)
from tests.integration.fastapi.helpers.stubs import (
    UserInputPortStub as _UserInputPortStub,
)
from tests.integration.fastapi.helpers.stubs import (
    build_timestamp as _build_timestamp,
)


def _create_test_app(
    user_input_port: _UserInputPortStub,
) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_router(
            user_input_port=user_input_port,
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )

    return app


@pytest.mark.anyio
async def test_get_user_returns_user_response() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(
            year=2026,
            month=5,
            day=3,
            hour=12,
            minute=30,
            second=15,
            microsecond=123000,
        ),
        updated_at=_build_timestamp(
            year=2026,
            month=5,
            day=3,
            hour=12,
            minute=30,
            second=15,
            microsecond=123000,
        ),
    )
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/user", params={"email": "ada@example.com"})

    assert response.status_code == 200
    assert response.json() == build_user_response()


@pytest.mark.anyio
async def test_list_users_returns_paginated_response() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=1),
    )
    user_input_port_stub.users_by_email["grace@example.com"] = User(
        id=2,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1906, 12, 9),
        created_at=_build_timestamp(year=2026, month=5, day=2),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/user/list",
            params={
                "offset": 0,
                "limit": 1,
                "sort": "email",
            },
        )

    assert response.status_code == 200
    assert response.json() == build_page_response(
        items=[
            build_user_response(
                created_at="2026-05-01T00:00:00.000Z",
                updated_at="2026-05-01T00:00:00.000Z",
            ),
        ],
        limit=1,
        total=2,
    )
    assert user_input_port_stub.list_user_queries == [
        ListQuery(
            offset=0,
            limit=1,
            sort=(
                SortTerm(
                    field="email",
                    direction=SortDirection.ASC,
                ),
            ),
        ),
    ]


@pytest.mark.anyio
async def test_get_user_returns_404_when_user_does_not_exist() -> None:
    app = _create_test_app(_UserInputPortStub())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/user", params={"email": "missing@example.com"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


@pytest.mark.anyio
async def test_create_user_returns_created_response_without_password_fields() -> None:
    app = _create_test_app(_UserInputPortStub())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/user", json=build_user_create_payload())

    assert response.status_code == 201
    assert response.json() == build_user_response()


@pytest.mark.anyio
async def test_create_user_returns_409_when_email_already_exists() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Existing",
        last_name="User",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/user", json=build_user_create_payload())

    assert response.status_code == 409
    assert response.json()["detail"] == "User email already exists."


@pytest.mark.anyio
async def test_update_user_returns_updated_user() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(
            year=2026,
            month=5,
            day=1,
            hour=10,
            microsecond=1000,
        ),
        updated_at=_build_timestamp(
            year=2026,
            month=5,
            day=2,
            hour=11,
            microsecond=2000,
        ),
    )
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/user",
            params={"current_email": "ada@example.com"},
            json=build_user_update_payload(),
        )

    assert response.status_code == 200
    assert response.json() == build_updated_user_response(
        created_at="2026-05-01T10:00:00.001Z",
    )


@pytest.mark.anyio
async def test_delete_user_soft_deletes_by_default() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/user", params={"email": "ada@example.com"})

    assert response.status_code == 204
    assert user_input_port_stub.delete_calls == [("ada@example.com", False)]


@pytest.mark.anyio
async def test_delete_user_forwards_hard_delete_query_param() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/user",
            params={
                "email": "ada@example.com",
                "hard_delete": "true",
            },
        )

    assert response.status_code == 204
    assert user_input_port_stub.delete_calls == [("ada@example.com", True)]

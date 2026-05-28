from datetime import date

import pytest

from src.core.domain.user import (
    User,
)
from src.core.shared import ListQuery, SortDirection, SortTerm
from src.infra.settings import load_settings
from tests.integration.fastapi.helpers.builders import (
    build_page_response,
    build_updated_user_response,
    build_user_create_payload,
    build_user_response,
    build_user_update_payload,
)
from tests.integration.fastapi.helpers.stubs import UserInputPortStub, build_timestamp


@pytest.mark.anyio
async def test_user_crud_flow_through_http_app(
    user_input_port_stub: UserInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(user_input_port=user_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/user",
            json=build_user_create_payload(),
        )

        get_response = await client.get("/user", params={"email": "ada@example.com"})
        update_response = await client.put(
            "/user",
            params={"current_email": "ada@example.com"},
            json=build_user_update_payload(),
        )
        delete_response = await client.delete(
            "/user",
            params={"email": "grace@example.com"},
        )
        missing_response = await client.get(
            "/user",
            params={"email": "grace@example.com"},
        )

    assert create_response.status_code == 201
    assert create_response.json() == build_user_response()
    assert get_response.status_code == 200
    assert get_response.json() == build_user_response()
    assert update_response.status_code == 200
    assert update_response.json() == build_updated_user_response()
    assert delete_response.status_code == 204
    assert user_input_port_stub.delete_calls == [("grace@example.com", False)]
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_delete_user_hard_deletes_when_requested_through_http_app(
    user_input_port_stub: UserInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(user_input_port=user_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/user",
            json=build_user_create_payload(),
        )
        delete_response = await client.delete(
            "/user",
            params={
                "email": "ada@example.com",
                "hard_delete": "true",
            },
        )
        missing_response = await client.get(
            "/user",
            params={"email": "ada@example.com"},
        )

    assert create_response.status_code == 201
    assert delete_response.status_code == 204
    assert user_input_port_stub.delete_calls == [("ada@example.com", True)]
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_list_users_returns_paginated_response_through_http_app(
    user_input_port_stub: UserInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=build_timestamp(day=1, year=2026, month=5),
        updated_at=build_timestamp(day=1, year=2026, month=5),
    )
    user_input_port_stub.users_by_email["grace@example.com"] = User(
        id=2,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1906, 12, 9),
        created_at=build_timestamp(day=2, year=2026, month=5),
        updated_at=build_timestamp(day=2, year=2026, month=5),
    )
    user_input_port_stub.soft_deleted_emails.add("grace@example.com")
    user_input_port_stub.users_by_email["katherine@example.com"] = User(
        id=3,
        first_name="Katherine",
        last_name="Johnson",
        email="katherine@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1918, 8, 26),
        created_at=build_timestamp(day=3, year=2026, month=5),
        updated_at=build_timestamp(day=3, year=2026, month=5),
    )
    app = fastapi_app_builder(user_input_port=user_input_port_stub)

    async with fastapi_client_factory(app) as client:
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
        [
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
async def test_list_users_rejects_invalid_limit_through_http_app(
    user_input_port_stub: UserInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(user_input_port=user_input_port_stub)
    settings = load_settings()

    async with fastapi_client_factory(app) as client:
        response = await client.get(
            "/user/list",
            params={
                "limit": settings.fastapi.pagination_max_limit + 1,
            },
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_list_users_rejects_sort_field_outside_endpoint_whitelist(
    user_input_port_stub: UserInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(user_input_port=user_input_port_stub)

    async with fastapi_client_factory(app) as client:
        response = await client.get(
            "/user/list",
            params={
                "sort": "password_hash",
            },
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_create_user_returns_409_when_email_already_exists_through_http_app(
    user_input_port_stub: UserInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    user_input_port_stub.users_by_email["ada@example.com"] = User(
        id=1,
        first_name="Existing",
        last_name="User",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=build_timestamp(day=1, year=2026, month=5),
        updated_at=build_timestamp(day=2, year=2026, month=5),
    )
    app = fastapi_app_builder(user_input_port=user_input_port_stub)

    async with fastapi_client_factory(app) as client:
        response = await client.post(
            "/user",
            json=build_user_create_payload(),
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "User email already exists."

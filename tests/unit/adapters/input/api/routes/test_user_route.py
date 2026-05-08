from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.user_route import create_router
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.input.user_input_port import UserInputPort
from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def _build_timestamp(
    *,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        tzinfo=UTC,
    )


def _sort_users(
    users: list[User],
    sort_terms: tuple[SortTerm, ...],
) -> list[User]:
    sorted_users = list(users)
    effective_sort_terms = sort_terms or (
        SortTerm(
            field="created_at",
            direction=SortDirection.DESC,
        ),
    )
    sort_chain = (
        *effective_sort_terms,
        SortTerm(
            field="id",
            direction=SortDirection.DESC,
        ),
    )

    for sort_term in reversed(sort_chain):
        sorted_users.sort(
            key=lambda user: getattr(user, sort_term.field),
            reverse=sort_term.direction == SortDirection.DESC,
        )

    return sorted_users


class _UserInputPortStub(UserInputPort):
    def __init__(
        self,
    ) -> None:
        self.users_by_email: dict[str, User] = {}
        self.soft_deleted_emails: set[str] = set()
        self.delete_calls: list[tuple[str, bool]] = []
        self.list_user_queries: list[ListQuery] = []
        self._next_user_id = 1

    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]:
        self.list_user_queries.append(list_query)
        active_users = _sort_users(
            [
                user
                for user in self.users_by_email.values()
                if user.email not in self.soft_deleted_emails
            ],
            list_query.sort,
        )

        return Page[User](
            items=active_users[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_users),
        )

    async def get_user(
        self,
        email: str,
    ) -> User:
        if email in self.soft_deleted_emails:
            raise UserNotFoundError()

        user = self.users_by_email.get(email)

        if user is None:
            raise UserNotFoundError()

        return user

    async def create_user(
        self,
        data: CreateUserData,
    ) -> User:
        if any(
            existing_user.email == data.email
            for existing_user in self.users_by_email.values()
        ):
            raise UserEmailConflictError()

        user = User(
            id=self._next_user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::plain-password",
            birth_date=data.birth_date,
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
        self.users_by_email[user.email] = user
        self._next_user_id += 1

        return user

    async def update_user(
        self,
        current_email: str,
        data: UpdateUserData,
    ) -> User:
        if current_email in self.soft_deleted_emails:
            raise UserNotFoundError()

        current_user = self.users_by_email.get(current_email)

        if current_user is None:
            raise UserNotFoundError()

        for existing_user in self.users_by_email.values():
            if (
                existing_user.id != current_user.id
                and existing_user.email == data.email
            ):
                raise UserEmailConflictError()

        user = User(
            id=current_user.id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::new-password",
            birth_date=data.birth_date,
            created_at=current_user.created_at,
            updated_at=_build_timestamp(
                year=2026,
                month=5,
                day=3,
                hour=13,
                minute=45,
                second=30,
                microsecond=456000,
            ),
        )
        del self.users_by_email[current_email]
        self.users_by_email[user.email] = user

        return user

    async def delete_user(
        self,
        email: str,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((email, hard_delete))

        if email in self.soft_deleted_emails:
            if hard_delete:
                self.soft_deleted_emails.remove(email)
                self.users_by_email.pop(email, None)
                return

            raise UserNotFoundError()

        if email not in self.users_by_email:
            raise UserNotFoundError()

        if hard_delete:
            del self.users_by_email[email]
            return

        self.soft_deleted_emails.add(email)


def _create_test_app(
    user_input_port: UserInputPort,
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
    assert response.json() == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "birth_date": "1815-12-10",
        "created_at": "2026-05-03T12:30:15.123Z",
        "updated_at": "2026-05-03T12:30:15.123Z",
    }


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
    assert response.json() == {
        "items": [
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "birth_date": "1815-12-10",
                "created_at": "2026-05-01T00:00:00.000Z",
                "updated_at": "2026-05-01T00:00:00.000Z",
            },
        ],
        "offset": 0,
        "limit": 1,
        "total": 2,
    }
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
async def test_list_users_uses_default_created_at_asc() -> None:
    user_input_port_stub = _UserInputPortStub()
    user_input_port_stub.users_by_email["katherine@example.com"] = User(
        id=3,
        first_name="Katherine",
        last_name="Johnson",
        email="katherine@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1918, 8, 26),
        created_at=_build_timestamp(year=2026, month=5, day=3),
        updated_at=_build_timestamp(year=2026, month=5, day=3),
    )
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
    app = _create_test_app(user_input_port_stub)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/user/list",
            params={
                "offset": 0,
                "limit": 1,
            },
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["email"] == "ada@example.com"
    assert user_input_port_stub.list_user_queries == [
        ListQuery(
            offset=0,
            limit=1,
            sort=(
                SortTerm(
                    field="created_at",
                    direction=SortDirection.ASC,
                ),
            ),
        ),
    ]


@pytest.mark.anyio
async def test_list_users_accepts_id_as_sort_field() -> None:
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
                "sort": "-id",
            },
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["email"] == "grace@example.com"
    assert user_input_port_stub.list_user_queries == [
        ListQuery(
            offset=0,
            limit=1,
            sort=(
                SortTerm(
                    field="id",
                    direction=SortDirection.DESC,
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
async def test_get_user_returns_422_when_email_query_param_is_missing() -> None:
    app = _create_test_app(_UserInputPortStub())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/user")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_user_returns_201_without_password_fields() -> None:
    app = _create_test_app(_UserInputPortStub())

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/user",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "password": "plain-password",
                "birth_date": "1815-12-10",
            },
        )

    assert response.status_code == 201
    assert response.json()["first_name"] == "Ada"
    assert response.json()["created_at"] == "2026-05-03T12:30:15.123Z"
    assert response.json()["updated_at"] == "2026-05-03T12:30:15.123Z"
    assert "id" not in response.json()
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


@pytest.mark.anyio
async def test_create_user_returns_409_when_email_is_already_used() -> None:
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
        response = await client.post(
            "/user",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "password": "plain-password",
                "birth_date": "1815-12-10",
            },
        )

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
            json={
                "first_name": "Grace",
                "last_name": "Hopper",
                "email": "grace@example.com",
                "password": "new-password",
                "birth_date": "1906-12-09",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@example.com",
        "birth_date": "1906-12-09",
        "created_at": "2026-05-01T10:00:00.001Z",
        "updated_at": "2026-05-03T13:45:30.456Z",
    }


@pytest.mark.anyio
async def test_delete_user_returns_204() -> None:
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
    assert response.text == ""
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

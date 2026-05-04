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
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.infra.fastapi.app import create_http_app
from src.infra.settings import load_settings


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


class _UserInputPortStub(UserInputPort):
    def __init__(
        self,
    ) -> None:
        self.users_by_email: dict[str, User] = {}
        self._next_user_id = 1

    async def get_user(
        self,
        email: str,
    ) -> User:
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
    ) -> None:
        if email not in self.users_by_email:
            raise UserNotFoundError()

        del self.users_by_email[email]


def _create_test_app(
    user_input_port: UserInputPort,
) -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=_ReadyHealthzInputPortStub(),
        user_input_port=user_input_port,
    )


@pytest.mark.anyio
async def test_user_crud_flow_through_http_app() -> None:
    app = _create_test_app(_UserInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/user",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "password": "plain-password",
                "birth_date": "1815-12-10",
            },
        )

        get_response = await client.get("/user", params={"email": "ada@example.com"})
        update_response = await client.put(
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
        delete_response = await client.delete(
            "/user",
            params={"email": "grace@example.com"},
        )
        missing_response = await client.get(
            "/user",
            params={"email": "grace@example.com"},
        )

    assert create_response.status_code == 201
    assert create_response.json() == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "birth_date": "1815-12-10",
        "created_at": "2026-05-03T12:30:15.123Z",
        "updated_at": "2026-05-03T12:30:15.123Z",
    }
    assert get_response.status_code == 200
    assert get_response.json() == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "birth_date": "1815-12-10",
        "created_at": "2026-05-03T12:30:15.123Z",
        "updated_at": "2026-05-03T12:30:15.123Z",
    }
    assert update_response.status_code == 200
    assert update_response.json() == {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@example.com",
        "birth_date": "1906-12-09",
        "created_at": "2026-05-03T12:30:15.123Z",
        "updated_at": "2026-05-03T13:45:30.456Z",
    }
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_create_user_returns_conflict_when_email_already_exists() -> None:
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

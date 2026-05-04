from datetime import UTC, date, datetime

from fastapi.routing import APIRoute

from src.adapters.input.api.router import create_api_router
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
)
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.user_input_port import UserInputPort


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


class _HealthyHealthzInputPortStub(HealthzInputPort):
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
    async def get_user(
        self,
        email,
    ) -> User:
        return User(
            id=1,
            first_name="Ada",
            last_name="Lovelace",
            email=email,
            password_hash="hashed::plain-password",
            birth_date=date(1815, 12, 10),
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def create_user(
        self,
        data: CreateUserData,
    ) -> User:
        return User(
            id=1,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::plain-password",
            birth_date=data.birth_date,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=1),
        )

    async def update_user(
        self,
        current_email,
        data: UpdateUserData,
    ) -> User:
        return User(
            id=1,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::plain-password",
            birth_date=data.birth_date,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def delete_user(
        self,
        email,
    ) -> None:
        return None


def test_create_api_router_mounts_docs_and_healthz_routes():
    router = create_api_router(
        docs_url="/docs",
        docs_title="Docs",
        docs_dark_mode=True,
        openapi_url="/openapi.json",
        healthz_input_port=_HealthyHealthzInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )

    route_paths = {route.path for route in router.routes if isinstance(route, APIRoute)}

    assert "/docs" in route_paths
    assert "/healthz/liveness" in route_paths
    assert "/healthz/readiness" in route_paths
    assert "/user" in route_paths

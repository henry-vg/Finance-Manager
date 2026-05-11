from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI

from src.core.domain.healthz import HealthzStatus
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    Currency,
    LedgerAccount,
    LedgerAccountKind,
    LedgerAccountType,
    UpdateLedgerAccountData,
)
from src.core.domain.tag import CreateTagData, Tag, UpdateTagData
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
)
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.shared import ListQuery, Page
from src.core.usecases.healthz_usecase import HealthzUseCase
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


class _UnhealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.NOT_OK


class _HealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.OK


class _TagInputPortStub(TagInputPort):
    async def list_tags(
        self,
        list_query: ListQuery,
    ) -> Page[Tag]:
        return Page[Tag](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_tag(
        self,
        tag_id: int,
    ) -> Tag:
        return Tag(
            id=tag_id,
            title="Food",
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def create_tag(
        self,
        data: CreateTagData,
    ) -> Tag:
        return Tag(
            id=1,
            title=data.title,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=1),
        )

    async def update_tag(
        self,
        tag_id: int,
        data: UpdateTagData,
    ) -> Tag:
        return Tag(
            id=tag_id,
            title=data.title,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def delete_tag(
        self,
        tag_id: int,
        hard_delete: bool = False,
    ) -> None:
        del tag_id
        del hard_delete
        return None


class _LedgerAccountInputPortStub(LedgerAccountInputPort):
    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]:
        return Page[LedgerAccount](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_ledger_account(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount:
        return LedgerAccount(
            id=ledger_account_id,
            title="Main Account",
            type=LedgerAccountType.ASSET,
            kind=LedgerAccountKind.BANK_ACCOUNT,
            currency=Currency.BRL,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def create_ledger_account(
        self,
        data: CreateLedgerAccountData,
    ) -> LedgerAccount:
        return LedgerAccount(
            id=1,
            title=data.title,
            type=data.type,
            kind=data.kind,
            currency=data.currency,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=1),
        )

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount:
        return LedgerAccount(
            id=ledger_account_id,
            title=data.title,
            type=data.type,
            kind=data.kind,
            currency=data.currency,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None:
        del ledger_account_id
        del hard_delete
        return None


class _UserInputPortStub(UserInputPort):
    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]:
        return Page[User](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

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
        hard_delete: bool = False,
    ) -> None:
        del email
        del hard_delete
        return None


def _create_test_app(
    database_health_output_port: DatabaseHealthOutputPort,
) -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=HealthzUseCase(database_health_output_port),
        ledger_account_input_port=_LedgerAccountInputPortStub(),
        tag_input_port=_TagInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )


@pytest.mark.anyio
async def test_healthz_liveness_returns_ok():
    app = _create_test_app(_HealthyDatabaseHealthOutputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_healthz_readiness_returns_ok():
    app = _create_test_app(_HealthyDatabaseHealthOutputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {"api": "ok", "database": "ok"},
    }


@pytest.mark.anyio
async def test_healthz_readiness_returns_not_ok_when_database_is_unavailable():
    app = _create_test_app(_UnhealthyDatabaseHealthOutputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ok",
        "dependencies": {"api": "ok", "database": "not_ok"},
    }

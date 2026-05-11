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
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountNotFoundError,
    UpdateLedgerAccountData,
)
from src.core.domain.tag import CreateTagData, Tag, UpdateTagData
from src.core.domain.user import CreateUserData, UpdateUserData, User
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.tag_input_port import TagInputPort
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


class _LedgerAccountInputPortStub:
    def __init__(self) -> None:
        self.ledger_accounts_by_id: dict[int, LedgerAccount] = {}
        self.soft_deleted_ledger_account_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_ledger_account_queries: list[ListQuery] = []
        self._next_ledger_account_id = 1

    async def list_ledger_accounts(self, list_query: ListQuery) -> Page[LedgerAccount]:
        self.list_ledger_account_queries.append(list_query)
        active_ledger_accounts = [
            ledger_account
            for ledger_account_id, ledger_account in self.ledger_accounts_by_id.items()
            if ledger_account_id not in self.soft_deleted_ledger_account_ids
        ]
        active_ledger_accounts.sort(key=lambda ledger_account: ledger_account.id)
        return Page[LedgerAccount](
            items=active_ledger_accounts[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_ledger_accounts),
        )

    async def get_ledger_account(self, ledger_account_id: int) -> LedgerAccount:
        if (
            ledger_account_id in self.soft_deleted_ledger_account_ids
            or ledger_account_id not in self.ledger_accounts_by_id
        ):
            raise LedgerAccountNotFoundError()
        return self.ledger_accounts_by_id[ledger_account_id]

    async def create_ledger_account(
        self,
        data: CreateLedgerAccountData,
    ) -> LedgerAccount:
        ledger_account = LedgerAccount(
            id=self._next_ledger_account_id,
            title=data.title,
            type=data.type,
            kind=data.kind,
            currency=data.currency,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.ledger_accounts_by_id[ledger_account.id] = ledger_account
        self._next_ledger_account_id += 1
        return ledger_account

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount:
        current = await self.get_ledger_account(ledger_account_id)
        updated = LedgerAccount(
            id=current.id,
            title=data.title,
            type=data.type,
            kind=data.kind,
            currency=data.currency,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.ledger_accounts_by_id[ledger_account_id] = updated
        return updated

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((ledger_account_id, hard_delete))
        if ledger_account_id in self.soft_deleted_ledger_account_ids:
            if hard_delete:
                self.soft_deleted_ledger_account_ids.remove(ledger_account_id)
                self.ledger_accounts_by_id.pop(ledger_account_id, None)
                return
            raise LedgerAccountNotFoundError()
        if ledger_account_id not in self.ledger_accounts_by_id:
            raise LedgerAccountNotFoundError()
        if hard_delete:
            self.ledger_accounts_by_id.pop(ledger_account_id, None)
            return
        self.soft_deleted_ledger_account_ids.add(ledger_account_id)


class _TagInputPortStub(TagInputPort):
    async def list_tags(self, list_query: ListQuery) -> Page[Tag]:
        return Page[Tag](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_tag(self, tag_id: int) -> Tag:
        return Tag(
            id=tag_id,
            title="Food",
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def create_tag(self, data: CreateTagData) -> Tag:
        return Tag(
            id=1,
            title=data.title,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )

    async def update_tag(self, tag_id: int, data: UpdateTagData) -> Tag:
        return Tag(
            id=tag_id,
            title=data.title,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def delete_tag(self, tag_id: int, hard_delete: bool = False) -> None:
        del tag_id
        del hard_delete
        return None


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


def _create_test_app(ledger_account_input_port: _LedgerAccountInputPortStub) -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=_ReadyHealthzInputPortStub(),
        ledger_account_input_port=ledger_account_input_port,
        tag_input_port=_TagInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )


@pytest.mark.anyio
async def test_ledger_account_crud_flow_through_http_app() -> None:
    ledger_account_input_port_stub = _LedgerAccountInputPortStub()
    app = _create_test_app(ledger_account_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/ledger-account",
            json={
                "title": "Main Account",
                "type": "asset",
                "kind": "bank_account",
                "currency": "BRL",
            },
        )
        created_id = create_response.json()["id"]
        get_response = await client.get("/ledger-account", params={"id": created_id})
        list_response = await client.get("/ledger-account/list")
        update_response = await client.put(
            "/ledger-account",
            params={"id": created_id},
            json={
                "title": "Credit Card",
                "type": "liability",
                "kind": "credit_card",
                "currency": "USD",
            },
        )
        delete_response = await client.delete(
            "/ledger-account",
            params={"id": created_id},
        )

    assert create_response.status_code == 201
    assert list(create_response.json().keys()) == [
        "id",
        "created_at",
        "updated_at",
        "title",
        "type",
        "kind",
        "currency",
    ]
    assert create_response.json()["title"] == "Main Account"
    assert get_response.status_code == 200
    assert list(get_response.json().keys()) == [
        "id",
        "created_at",
        "updated_at",
        "title",
        "type",
        "kind",
        "currency",
    ]
    assert get_response.json()["id"] == created_id
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Credit Card"
    assert update_response.json()["type"] == "liability"
    assert delete_response.status_code == 204

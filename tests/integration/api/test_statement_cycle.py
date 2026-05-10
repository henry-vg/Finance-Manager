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
    Currency,
    LedgerAccount,
    LedgerAccountKind,
    LedgerAccountType,
    UpdateLedgerAccountData,
)
from src.core.domain.statement_cycle import (
    CreateStatementCycleData,
    StatementCycle,
    StatementCycleLedgerAccountInvalidError,
    StatementCycleNotFoundError,
    UpdateStatementCycleData,
)
from src.core.domain.tag import CreateTagData, Tag, UpdateTagData
from src.core.domain.user import CreateUserData, UpdateUserData, User
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
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


class _LedgerAccountInputPortStub(LedgerAccountInputPort):
    async def list_ledger_accounts(self, list_query: ListQuery) -> Page[LedgerAccount]:
        return Page[LedgerAccount](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_ledger_account(self, ledger_account_id: int) -> LedgerAccount:
        return LedgerAccount(
            id=ledger_account_id,
            title="Credit Card",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
            currency=Currency.BRL,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
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
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
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
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(2),
        )

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None:
        del ledger_account_id
        del hard_delete
        return None


class _StatementCycleInputPortStub:
    def __init__(self) -> None:
        self.statement_cycles_by_id: dict[int, StatementCycle] = {}
        self.soft_deleted_statement_cycle_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self._next_statement_cycle_id = 1

    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]:
        active_statement_cycles = [
            statement_cycle
            for statement_cycle_id, statement_cycle in (
                self.statement_cycles_by_id.items()
            )
            if statement_cycle_id not in self.soft_deleted_statement_cycle_ids
        ]
        active_statement_cycles.sort(key=lambda statement_cycle: statement_cycle.id)
        return Page[StatementCycle](
            items=active_statement_cycles[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_statement_cycles),
        )

    async def get_statement_cycle(self, statement_cycle_id: int) -> StatementCycle:
        if (
            statement_cycle_id in self.soft_deleted_statement_cycle_ids
            or statement_cycle_id not in self.statement_cycles_by_id
        ):
            raise StatementCycleNotFoundError()
        return self.statement_cycles_by_id[statement_cycle_id]

    async def create_statement_cycle(
        self,
        data: CreateStatementCycleData,
    ) -> StatementCycle:
        if data.ledger_account_id == 999:
            raise StatementCycleLedgerAccountInvalidError()

        statement_cycle = StatementCycle(
            id=self._next_statement_cycle_id,
            ledger_account_id=data.ledger_account_id,
            cycle_start=data.cycle_start,
            cycle_end=data.cycle_end,
            closing_date=data.closing_date,
            due_date=data.due_date,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.statement_cycles_by_id[statement_cycle.id] = statement_cycle
        self._next_statement_cycle_id += 1
        return statement_cycle

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        data: UpdateStatementCycleData,
    ) -> StatementCycle:
        current = await self.get_statement_cycle(statement_cycle_id)
        updated = StatementCycle(
            id=current.id,
            ledger_account_id=data.ledger_account_id,
            cycle_start=data.cycle_start,
            cycle_end=data.cycle_end,
            closing_date=data.closing_date,
            due_date=data.due_date,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.statement_cycles_by_id[statement_cycle_id] = updated
        return updated

    async def delete_statement_cycle(
        self,
        statement_cycle_id: int,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((statement_cycle_id, hard_delete))
        if statement_cycle_id in self.soft_deleted_statement_cycle_ids:
            if hard_delete:
                self.soft_deleted_statement_cycle_ids.remove(statement_cycle_id)
                self.statement_cycles_by_id.pop(statement_cycle_id, None)
                return
            raise StatementCycleNotFoundError()
        if statement_cycle_id not in self.statement_cycles_by_id:
            raise StatementCycleNotFoundError()
        if hard_delete:
            self.statement_cycles_by_id.pop(statement_cycle_id, None)
            return
        self.soft_deleted_statement_cycle_ids.add(statement_cycle_id)


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


def _create_test_app(
    statement_cycle_input_port: _StatementCycleInputPortStub,
) -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=_ReadyHealthzInputPortStub(),
        ledger_account_input_port=_LedgerAccountInputPortStub(),
        statement_cycle_input_port=statement_cycle_input_port,
        tag_input_port=_TagInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )


@pytest.mark.anyio
async def test_statement_cycle_crud_flow_through_http_app() -> None:
    statement_cycle_input_port_stub = _StatementCycleInputPortStub()
    app = _create_test_app(statement_cycle_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/statement-cycle",
            json={
                "ledger_account_id": 1,
                "cycle_start": "2026-05-01",
                "cycle_end": "2026-05-31",
                "closing_date": "2026-05-28",
                "due_date": "2026-06-05",
            },
        )
        created_id = create_response.json()["id"]
        get_response = await client.get(
            "/statement-cycle",
            params={"id": created_id},
        )
        list_response = await client.get("/statement-cycle/list")
        update_response = await client.put(
            "/statement-cycle",
            params={"id": created_id},
            json={
                "ledger_account_id": 1,
                "cycle_start": "2026-06-01",
                "cycle_end": "2026-06-30",
                "closing_date": "2026-06-28",
                "due_date": "2026-07-05",
            },
        )
        delete_response = await client.delete(
            "/statement-cycle",
            params={"id": created_id},
        )

    assert create_response.status_code == 201
    assert create_response.json()["ledger_account_id"] == 1
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_id
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["cycle_start"] == "2026-06-01"
    assert delete_response.status_code == 204

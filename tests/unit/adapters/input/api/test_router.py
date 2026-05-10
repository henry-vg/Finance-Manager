from datetime import UTC, date, datetime

from fastapi.routing import APIRoute

from src.adapters.input.api.router import create_api_router
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
    UpdateStatementCycleData,
)
from src.core.domain.tag import CreateTagData, Tag, UpdateTagData
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.statement_cycle_input_port import StatementCycleInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.shared import ListQuery, Page


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


class _StatementCycleInputPortStub(StatementCycleInputPort):
    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]:
        return Page[StatementCycle](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle:
        return StatementCycle(
            id=statement_cycle_id,
            ledger_account_id=1,
            cycle_start=date(2026, 5, 1),
            cycle_end=date(2026, 5, 31),
            closing_date=date(2026, 5, 28),
            due_date=date(2026, 6, 5),
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def create_statement_cycle(
        self,
        data: CreateStatementCycleData,
    ) -> StatementCycle:
        return StatementCycle(
            id=1,
            ledger_account_id=data.ledger_account_id,
            cycle_start=data.cycle_start,
            cycle_end=data.cycle_end,
            closing_date=data.closing_date,
            due_date=data.due_date,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=1),
        )

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        data: UpdateStatementCycleData,
    ) -> StatementCycle:
        return StatementCycle(
            id=statement_cycle_id,
            ledger_account_id=data.ledger_account_id,
            cycle_start=data.cycle_start,
            cycle_end=data.cycle_end,
            closing_date=data.closing_date,
            due_date=data.due_date,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def delete_statement_cycle(
        self,
        statement_cycle_id: int,
        hard_delete: bool = False,
    ) -> None:
        del statement_cycle_id
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


def test_create_api_router_mounts_docs_and_healthz_routes():
    router = create_api_router(
        docs_url="/docs",
        docs_title="Docs",
        docs_dark_mode=True,
        openapi_url="/openapi.json",
        pagination_default_limit=50,
        pagination_max_limit=500,
        healthz_input_port=_HealthyHealthzInputPortStub(),
        ledger_account_input_port=_LedgerAccountInputPortStub(),
        statement_cycle_input_port=_StatementCycleInputPortStub(),
        tag_input_port=_TagInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )

    route_paths = {route.path for route in router.routes if isinstance(route, APIRoute)}

    assert "/docs" in route_paths
    assert "/healthz/liveness" in route_paths
    assert "/healthz/readiness" in route_paths
    assert "/ledger-account" in route_paths
    assert "/ledger-account/list" in route_paths
    assert "/statement-cycle" in route_paths
    assert "/statement-cycle/list" in route_paths
    assert "/tag" in route_paths
    assert "/tag/list" in route_paths
    assert "/user" in route_paths
    assert "/user/list" in route_paths

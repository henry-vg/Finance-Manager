from datetime import UTC, date, datetime

from fastapi.routing import APIRoute

from src.adapters.input.api.router import create_api_router
from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    UpdateCurrencyData,
)
from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountInstrumentKind,
    LedgerAccountType,
    UpdateLedgerAccountData,
)
from src.core.domain.tag import CreateTagData, Tag, UpdateTagData
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
)
from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
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


class _CurrencyInputPortStub(CurrencyInputPort):
    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]:
        return Page[Currency](
            items=[],
            offset=list_query.offset,
            limit=list_query.limit,
            total=0,
        )

    async def get_currency(
        self,
        currency_id: int,
    ) -> Currency:
        return Currency(
            id=currency_id,
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def create_currency(
        self,
        data: CreateCurrencyData,
    ) -> Currency:
        return Currency(
            id=1,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=1),
        )

    async def update_currency(
        self,
        currency_id: int,
        data: UpdateCurrencyData,
    ) -> Currency:
        return Currency(
            id=currency_id,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=_build_timestamp(year=2026, month=5, day=1),
            updated_at=_build_timestamp(year=2026, month=5, day=2),
        )

    async def delete_currency(
        self,
        currency_id: int,
        hard_delete: bool = False,
    ) -> None:
        del currency_id
        del hard_delete
        return None


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
            instrument_kind=LedgerAccountInstrumentKind.BANK_ACCOUNT,
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
            instrument_kind=data.instrument_kind,
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
            instrument_kind=data.instrument_kind,
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


def test_create_api_router_mounts_docs_and_healthz_routes():
    router = create_api_router(
        docs_url="/docs",
        docs_title="Docs",
        docs_dark_mode=True,
        openapi_url="/openapi.json",
        pagination_default_limit=50,
        pagination_max_limit=500,
        healthz_input_port=_HealthyHealthzInputPortStub(),
        currency_input_port=_CurrencyInputPortStub(),
        ledger_account_input_port=_LedgerAccountInputPortStub(),
        tag_input_port=_TagInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )

    route_paths = {route.path for route in router.routes if isinstance(route, APIRoute)}

    assert "/docs" in route_paths
    assert "/healthz/liveness" in route_paths
    assert "/healthz/readiness" in route_paths
    assert "/currency" in route_paths
    assert "/currency/list" in route_paths
    assert "/ledger-account" in route_paths
    assert "/ledger-account/list" in route_paths
    assert "/tag" in route_paths
    assert "/tag/list" in route_paths
    assert "/user" in route_paths
    assert "/user/list" in route_paths

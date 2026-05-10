from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel

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


class _Payload(BaseModel):
    value: int


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

    async def get_statement_cycle(self, statement_cycle_id: int) -> StatementCycle:
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


def _create_test_app() -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=_ReadyHealthzInputPortStub(),
        ledger_account_input_port=_LedgerAccountInputPortStub(),
        statement_cycle_input_port=_StatementCycleInputPortStub(),
        tag_input_port=_TagInputPortStub(),
        user_input_port=_UserInputPortStub(),
    )


@pytest.mark.anyio
async def test_docs_endpoint_is_customized_and_returns_html():
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text
    assert 'document.documentElement.classList.add("dark-mode")' in response.text


@pytest.mark.anyio
async def test_openapi_endpoint_exposes_expected_metadata():
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert app.docs_url is None
    assert response.status_code == 200
    openapi_schema = response.json()

    assert openapi_schema["info"]["title"] == app.title
    assert openapi_schema["info"]["version"] == app.version
    assert any(tag["name"] == "HealthZ" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "LedgerAccount" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "StatementCycle" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "Tag" for tag in openapi_schema["tags"])
    assert any(tag["name"] == "User" for tag in openapi_schema["tags"])

    healthz_liveness_path = openapi_schema["paths"]["/healthz/liveness"]
    healthz_readiness_path = openapi_schema["paths"]["/healthz/readiness"]
    ledger_account_collection_path = openapi_schema["paths"]["/ledger-account"]
    ledger_account_list_path = openapi_schema["paths"]["/ledger-account/list"]
    statement_cycle_collection_path = openapi_schema["paths"]["/statement-cycle"]
    statement_cycle_list_path = openapi_schema["paths"]["/statement-cycle/list"]
    tag_collection_path = openapi_schema["paths"]["/tag"]
    tag_list_path = openapi_schema["paths"]["/tag/list"]
    user_collection_path = openapi_schema["paths"]["/user"]
    user_list_path = openapi_schema["paths"]["/user/list"]
    healthz_status_schema = openapi_schema["components"]["schemas"][
        "HealthzStatusResponse"
    ]

    assert "get" in healthz_liveness_path
    assert "get" in healthz_readiness_path
    assert "200" in healthz_liveness_path["get"]["responses"]
    assert "200" in healthz_readiness_path["get"]["responses"]
    assert "503" in healthz_readiness_path["get"]["responses"]
    assert healthz_status_schema["enum"] == ["ok", "not_ok"]

    assert "post" in ledger_account_collection_path
    assert "get" in ledger_account_collection_path
    assert "put" in ledger_account_collection_path
    assert "delete" in ledger_account_collection_path
    assert "id" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["get"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["put"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"]
        for parameter in ledger_account_collection_path["delete"]["parameters"]
    }
    assert "200" in ledger_account_collection_path["get"]["responses"]
    assert "404" in ledger_account_collection_path["get"]["responses"]
    assert "201" in ledger_account_collection_path["post"]["responses"]
    assert "200" in ledger_account_collection_path["put"]["responses"]
    assert "404" in ledger_account_collection_path["put"]["responses"]
    assert "204" in ledger_account_collection_path["delete"]["responses"]
    assert "404" in ledger_account_collection_path["delete"]["responses"]
    assert "get" in ledger_account_list_path
    assert {
        parameter["name"] for parameter in ledger_account_list_path["get"]["parameters"]
    } == {"offset", "limit", "sort"}
    assert "200" in ledger_account_list_path["get"]["responses"]

    assert "post" in statement_cycle_collection_path
    assert "get" in statement_cycle_collection_path
    assert "put" in statement_cycle_collection_path
    assert "delete" in statement_cycle_collection_path
    assert "id" in {
        parameter["name"]
        for parameter in statement_cycle_collection_path["get"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in statement_cycle_collection_path["put"]["parameters"]
    }
    assert "id" in {
        parameter["name"]
        for parameter in statement_cycle_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"]
        for parameter in statement_cycle_collection_path["delete"]["parameters"]
    }
    assert "200" in statement_cycle_collection_path["get"]["responses"]
    assert "404" in statement_cycle_collection_path["get"]["responses"]
    assert "201" in statement_cycle_collection_path["post"]["responses"]
    assert "404" in statement_cycle_collection_path["post"]["responses"]
    assert "409" in statement_cycle_collection_path["post"]["responses"]
    assert "200" in statement_cycle_collection_path["put"]["responses"]
    assert "404" in statement_cycle_collection_path["put"]["responses"]
    assert "409" in statement_cycle_collection_path["put"]["responses"]
    assert "204" in statement_cycle_collection_path["delete"]["responses"]
    assert "404" in statement_cycle_collection_path["delete"]["responses"]
    assert "get" in statement_cycle_list_path
    assert {
        parameter["name"]
        for parameter in statement_cycle_list_path["get"]["parameters"]
    } == {"offset", "limit", "sort"}
    assert "200" in statement_cycle_list_path["get"]["responses"]

    assert "post" in tag_collection_path
    assert "get" in tag_collection_path
    assert "put" in tag_collection_path
    assert "delete" in tag_collection_path
    assert "id" in {
        parameter["name"] for parameter in tag_collection_path["get"]["parameters"]
    }
    assert "id" in {
        parameter["name"] for parameter in tag_collection_path["put"]["parameters"]
    }
    assert "id" in {
        parameter["name"] for parameter in tag_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"] for parameter in tag_collection_path["delete"]["parameters"]
    }
    assert "200" in tag_collection_path["get"]["responses"]
    assert "404" in tag_collection_path["get"]["responses"]
    assert "201" in tag_collection_path["post"]["responses"]
    assert "200" in tag_collection_path["put"]["responses"]
    assert "404" in tag_collection_path["put"]["responses"]
    assert "204" in tag_collection_path["delete"]["responses"]
    assert "404" in tag_collection_path["delete"]["responses"]
    assert "get" in tag_list_path
    assert {parameter["name"] for parameter in tag_list_path["get"]["parameters"]} == {
        "offset",
        "limit",
        "sort",
    }
    assert "200" in tag_list_path["get"]["responses"]

    assert "post" in user_collection_path
    assert "get" in user_collection_path
    assert "put" in user_collection_path
    assert "delete" in user_collection_path
    assert "email" in {
        parameter["name"] for parameter in user_collection_path["get"]["parameters"]
    }
    assert "current_email" in {
        parameter["name"] for parameter in user_collection_path["put"]["parameters"]
    }
    assert "email" in {
        parameter["name"] for parameter in user_collection_path["delete"]["parameters"]
    }
    assert "hard_delete" in {
        parameter["name"] for parameter in user_collection_path["delete"]["parameters"]
    }
    assert "200" in user_collection_path["get"]["responses"]
    assert "404" in user_collection_path["get"]["responses"]
    assert "201" in user_collection_path["post"]["responses"]
    assert "409" in user_collection_path["post"]["responses"]
    assert "200" in user_collection_path["put"]["responses"]
    assert "404" in user_collection_path["put"]["responses"]
    assert "409" in user_collection_path["put"]["responses"]
    assert "204" in user_collection_path["delete"]["responses"]
    assert "404" in user_collection_path["delete"]["responses"]
    assert "get" in user_list_path
    assert {parameter["name"] for parameter in user_list_path["get"]["parameters"]} == {
        "offset",
        "limit",
        "sort",
    }
    assert "200" in user_list_path["get"]["responses"]

    sort_parameter = next(
        parameter
        for parameter in user_list_path["get"]["parameters"]
        if parameter["name"] == "sort"
    )

    assert "+" in sort_parameter["description"]
    assert "-" in sort_parameter["description"]
    assert "created_at" in sort_parameter["description"]
    assert "id" in sort_parameter["description"]
    assert "Default sort: created_at." in sort_parameter["description"]


@pytest.mark.anyio
async def test_middleware_passes_trace_id_through_response():
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/healthz/liveness",
            headers={"X-Trace-Id": "trace-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-123"


@pytest.mark.anyio
async def test_registered_validation_handler_returns_problem_details_for_body_errors():
    app = _create_test_app()

    @app.post("/validation/body")
    async def validate_body(payload: _Payload) -> dict[str, int]:
        return {"value": payload.value}

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/validation/body",
            json={"value": "bad"},
            headers={"X-Trace-Id": "trace-123"},
        )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Validation failed."
    assert response.json()["trace_id"] == "trace-123"


@pytest.mark.anyio
async def test_registered_validation_handler_returns_problem_details_for_query_errors():
    app = _create_test_app()

    @app.get("/validation/query")
    async def validate_query(value: int) -> dict[str, int]:
        return {"value": value}

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/validation/query", params={"value": "bad"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Invalid request."


@pytest.mark.anyio
async def test_registered_generic_exception_handler_returns_problem_details():
    app = _create_test_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom", headers={"X-Trace-Id": "trace-123"})

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "An unexpected error occurred."
    assert response.json()["trace_id"] == "trace-123"

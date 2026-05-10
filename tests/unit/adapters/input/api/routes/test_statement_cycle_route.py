from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.statement_cycle_route import create_router
from src.core.domain.ledger_account import LedgerAccountNotFoundError
from src.core.domain.statement_cycle import (
    CreateStatementCycleData,
    StatementCycle,
    StatementCycleLedgerAccountInvalidError,
    StatementCycleNotFoundError,
    UpdateStatementCycleData,
)
from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class _StatementCycleInputPortStub:
    def __init__(self) -> None:
        self.statement_cycles_by_id: dict[int, StatementCycle] = {}
        self.soft_deleted_statement_cycle_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_statement_cycle_queries: list[ListQuery] = []
        self._next_statement_cycle_id = 1

    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]:
        self.list_statement_cycle_queries.append(list_query)
        active_statement_cycles = [
            statement_cycle
            for statement_cycle_id, statement_cycle in (
                self.statement_cycles_by_id.items()
            )
            if statement_cycle_id not in self.soft_deleted_statement_cycle_ids
        ]
        active_statement_cycles.sort(
            key=lambda statement_cycle: statement_cycle.id,
        )
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
            raise LedgerAccountNotFoundError()
        if data.ledger_account_id == 998:
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

        if data.ledger_account_id == 999:
            raise LedgerAccountNotFoundError()
        if data.ledger_account_id == 998:
            raise StatementCycleLedgerAccountInvalidError()

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


def _create_test_app(
    statement_cycle_input_port: _StatementCycleInputPortStub,
) -> FastAPI:
    app = FastAPI()
    app.include_router(
        create_router(
            statement_cycle_input_port=statement_cycle_input_port,
            pagination_default_limit=50,
            pagination_max_limit=500,
        ),
    )
    return app


@pytest.mark.anyio
async def test_get_statement_cycle_returns_statement_cycle_response() -> None:
    statement_cycle_input_port_stub = _StatementCycleInputPortStub()
    statement_cycle_input_port_stub.statement_cycles_by_id[1] = StatementCycle(
        id=1,
        ledger_account_id=7,
        cycle_start=date(2026, 5, 1),
        cycle_end=date(2026, 5, 31),
        closing_date=date(2026, 5, 28),
        due_date=date(2026, 6, 5),
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(statement_cycle_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/statement-cycle", params={"id": 1})

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "ledger_account_id": 7,
        "cycle_start": "2026-05-01",
        "cycle_end": "2026-05-31",
        "closing_date": "2026-05-28",
        "due_date": "2026-06-05",
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
    }


@pytest.mark.anyio
async def test_list_statement_cycles_returns_paginated_response() -> None:
    statement_cycle_input_port_stub = _StatementCycleInputPortStub()
    statement_cycle_input_port_stub.statement_cycles_by_id[1] = StatementCycle(
        id=1,
        ledger_account_id=7,
        cycle_start=date(2026, 5, 1),
        cycle_end=date(2026, 5, 31),
        closing_date=date(2026, 5, 28),
        due_date=date(2026, 6, 5),
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    statement_cycle_input_port_stub.statement_cycles_by_id[2] = StatementCycle(
        id=2,
        ledger_account_id=7,
        cycle_start=date(2026, 6, 1),
        cycle_end=date(2026, 6, 30),
        closing_date=date(2026, 6, 28),
        due_date=date(2026, 7, 5),
        created_at=_build_timestamp(2),
        updated_at=_build_timestamp(2),
    )
    app = _create_test_app(statement_cycle_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/statement-cycle/list",
            params={"offset": 0, "limit": 10, "sort": "cycle_start"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["cycle_start"] == "2026-05-01"
    assert statement_cycle_input_port_stub.list_statement_cycle_queries == [
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="cycle_start", direction=SortDirection.ASC),),
        ),
    ]


@pytest.mark.anyio
async def test_create_statement_cycle_returns_404_for_missing_ledger_account() -> None:
    app = _create_test_app(_StatementCycleInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/statement-cycle",
            json={
                "ledger_account_id": 999,
                "cycle_start": "2026-05-01",
                "cycle_end": "2026-05-31",
                "closing_date": "2026-05-28",
                "due_date": "2026-06-05",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ledger account not found."


@pytest.mark.anyio
async def test_create_statement_cycle_returns_409_for_invalid_ledger_account() -> None:
    app = _create_test_app(_StatementCycleInputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/statement-cycle",
            json={
                "ledger_account_id": 998,
                "cycle_start": "2026-05-01",
                "cycle_end": "2026-05-31",
                "closing_date": "2026-05-28",
                "due_date": "2026-06-05",
            },
        )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Statement cycle ledger account must be a liability credit card."
    )


@pytest.mark.anyio
async def test_delete_statement_cycle_soft_deletes_by_default() -> None:
    statement_cycle_input_port_stub = _StatementCycleInputPortStub()
    statement_cycle_input_port_stub.statement_cycles_by_id[1] = StatementCycle(
        id=1,
        ledger_account_id=7,
        cycle_start=date(2026, 5, 1),
        cycle_end=date(2026, 5, 31),
        closing_date=date(2026, 5, 28),
        due_date=date(2026, 6, 5),
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    app = _create_test_app(statement_cycle_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/statement-cycle", params={"id": 1})

    assert response.status_code == 204
    assert statement_cycle_input_port_stub.delete_calls == [(1, False)]

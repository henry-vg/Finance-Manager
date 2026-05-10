from typing import Protocol

from src.core.domain.statement_cycle import (
    CreateStatementCycleData,
    StatementCycle,
    UpdateStatementCycleData,
)
from src.core.shared import ListQuery, Page


class StatementCycleInputPort(Protocol):
    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]: ...

    async def get_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle: ...

    async def create_statement_cycle(
        self,
        data: CreateStatementCycleData,
    ) -> StatementCycle: ...

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        data: UpdateStatementCycleData,
    ) -> StatementCycle: ...

    async def delete_statement_cycle(
        self,
        statement_cycle_id: int,
        hard_delete: bool = False,
    ) -> None: ...

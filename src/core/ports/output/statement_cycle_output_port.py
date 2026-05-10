from typing import Protocol

from src.core.domain.statement_cycle import (
    NewStatementCycle,
    StatementCycle,
    StatementCycleChanges,
)
from src.core.shared import ListQuery, Page


class StatementCycleNotFoundOutputPortError(Exception):
    pass


class StatementCycleOutputPort(Protocol):
    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]: ...

    async def get_statement_cycle_by_id(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle | None: ...

    async def get_statement_cycle_by_id_including_deleted(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle | None: ...

    async def create_statement_cycle(
        self,
        new_statement_cycle: NewStatementCycle,
    ) -> StatementCycle: ...

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        changes: StatementCycleChanges,
    ) -> StatementCycle: ...

    async def soft_delete_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> None: ...

    async def hard_delete_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> None: ...

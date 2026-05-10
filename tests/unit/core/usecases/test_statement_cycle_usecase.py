from datetime import UTC, date, datetime

import pytest

from src.core.domain.ledger_account import (
    Currency,
    LedgerAccount,
    LedgerAccountKind,
    LedgerAccountNotFoundError,
    LedgerAccountType,
)
from src.core.domain.statement_cycle import (
    CreateStatementCycleData,
    NewStatementCycle,
    StatementCycle,
    StatementCycleChanges,
    StatementCycleLedgerAccountInvalidError,
    StatementCycleNotFoundError,
    UpdateStatementCycleData,
)
from src.core.ports.output.ledger_account_output_port import LedgerAccountOutputPort
from src.core.ports.output.statement_cycle_output_port import (
    StatementCycleNotFoundOutputPortError,
    StatementCycleOutputPort,
)
from src.core.ports.output.tag_output_port import TagOutputPort
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.ports.output.user_output_port import UserOutputPort
from src.core.shared import ListQuery, Page, SortDirection, SortTerm
from src.core.usecases.statement_cycle_usecase import StatementCycleUseCase


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def _build_create_data(
    *,
    ledger_account_id: int = 1,
) -> CreateStatementCycleData:
    return CreateStatementCycleData(
        ledger_account_id=ledger_account_id,
        cycle_start=date(2026, 5, 1),
        cycle_end=date(2026, 5, 31),
        closing_date=date(2026, 5, 28),
        due_date=date(2026, 6, 5),
    )


def _build_update_data(
    *,
    ledger_account_id: int = 1,
) -> UpdateStatementCycleData:
    return UpdateStatementCycleData(
        ledger_account_id=ledger_account_id,
        cycle_start=date(2026, 6, 1),
        cycle_end=date(2026, 6, 30),
        closing_date=date(2026, 6, 28),
        due_date=date(2026, 7, 5),
    )


def _build_credit_card_ledger_account(
    *,
    ledger_account_id: int = 1,
) -> LedgerAccount:
    return LedgerAccount(
        id=ledger_account_id,
        title="Credit Card",
        type=LedgerAccountType.LIABILITY,
        kind=LedgerAccountKind.CREDIT_CARD,
        currency=Currency.BRL,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )


class _LedgerAccountOutputPortStub(LedgerAccountOutputPort):
    def __init__(self) -> None:
        self.ledger_accounts: dict[int, LedgerAccount] = {}

    async def list_ledger_accounts(self, list_query: ListQuery) -> Page[LedgerAccount]:
        del list_query
        return Page[LedgerAccount](items=[], offset=0, limit=0, total=0)

    async def get_ledger_account_by_id(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        return self.ledger_accounts.get(ledger_account_id)

    async def get_ledger_account_by_id_including_deleted(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        return self.ledger_accounts.get(ledger_account_id)

    async def create_ledger_account(self, new_ledger_account):
        raise RuntimeError("create_ledger_account is unused in statement cycle tests")

    async def update_ledger_account(self, ledger_account_id: int, changes):
        del ledger_account_id
        del changes
        raise RuntimeError("update_ledger_account is unused in statement cycle tests")

    async def soft_delete_ledger_account(self, ledger_account_id: int) -> None:
        del ledger_account_id
        raise RuntimeError(
            "soft_delete_ledger_account is unused in statement cycle tests",
        )

    async def hard_delete_ledger_account(self, ledger_account_id: int) -> None:
        del ledger_account_id
        raise RuntimeError(
            "hard_delete_ledger_account is unused in statement cycle tests",
        )


class _StatementCycleOutputPortStub(StatementCycleOutputPort):
    def __init__(self) -> None:
        self.statement_cycles: dict[int, StatementCycle] = {}
        self.deleted_statement_cycle_ids: set[int] = set()
        self.update_error: Exception | None = None
        self.delete_error: Exception | None = None
        self.created_statement_cycles: list[NewStatementCycle] = []
        self.updated_statement_cycles: list[tuple[int, StatementCycleChanges]] = []
        self.list_queries: list[ListQuery] = []
        self.next_id = 1

    async def list_statement_cycles(
        self,
        list_query: ListQuery,
    ) -> Page[StatementCycle]:
        self.list_queries.append(list_query)
        active_statement_cycles = [
            statement_cycle
            for statement_cycle_id, statement_cycle in self.statement_cycles.items()
            if statement_cycle_id not in self.deleted_statement_cycle_ids
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

    async def get_statement_cycle_by_id(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle | None:
        if statement_cycle_id in self.deleted_statement_cycle_ids:
            return None

        return self.statement_cycles.get(statement_cycle_id)

    async def get_statement_cycle_by_id_including_deleted(
        self,
        statement_cycle_id: int,
    ) -> StatementCycle | None:
        return self.statement_cycles.get(statement_cycle_id)

    async def create_statement_cycle(
        self,
        new_statement_cycle: NewStatementCycle,
    ) -> StatementCycle:
        self.created_statement_cycles.append(new_statement_cycle)
        statement_cycle = StatementCycle(
            id=self.next_id,
            ledger_account_id=new_statement_cycle.ledger_account_id,
            cycle_start=new_statement_cycle.cycle_start,
            cycle_end=new_statement_cycle.cycle_end,
            closing_date=new_statement_cycle.closing_date,
            due_date=new_statement_cycle.due_date,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.statement_cycles[statement_cycle.id] = statement_cycle
        self.next_id += 1
        return statement_cycle

    async def update_statement_cycle(
        self,
        statement_cycle_id: int,
        changes: StatementCycleChanges,
    ) -> StatementCycle:
        if self.update_error is not None:
            raise self.update_error

        current = self.statement_cycles[statement_cycle_id]
        updated = StatementCycle(
            id=current.id,
            ledger_account_id=changes.ledger_account_id,
            cycle_start=changes.cycle_start,
            cycle_end=changes.cycle_end,
            closing_date=changes.closing_date,
            due_date=changes.due_date,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.updated_statement_cycles.append((statement_cycle_id, changes))
        self.statement_cycles[statement_cycle_id] = updated
        return updated

    async def soft_delete_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_statement_cycle_ids.add(statement_cycle_id)

    async def hard_delete_statement_cycle(
        self,
        statement_cycle_id: int,
    ) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_statement_cycle_ids.discard(statement_cycle_id)
        self.statement_cycles.pop(statement_cycle_id, None)


class _UnitOfWorkStub(UnitOfWorkOutputPort):
    def __init__(
        self,
        ledger_accounts: _LedgerAccountOutputPortStub,
        statement_cycles: _StatementCycleOutputPortStub,
    ) -> None:
        self._ledger_accounts = ledger_accounts
        self._statement_cycles = statement_cycles
        self.committed = False

    @property
    def ledger_accounts(self) -> LedgerAccountOutputPort:
        return self._ledger_accounts

    @property
    def statement_cycles(self) -> StatementCycleOutputPort:
        return self._statement_cycles

    @property
    def tags(self) -> TagOutputPort:
        raise RuntimeError("tags output port is unused in statement cycle tests")

    @property
    def users(self) -> UserOutputPort:
        raise RuntimeError("users output port is unused in statement cycle tests")

    async def __aenter__(self) -> "_UnitOfWorkStub":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        del exc_type
        del exc
        del traceback

    async def commit(self) -> None:
        self.committed = True


class _UnitOfWorkFactoryStub(UnitOfWorkOutputPortFactory):
    def __init__(self, unit_of_work: _UnitOfWorkStub) -> None:
        self._unit_of_work = unit_of_work

    def __call__(self) -> UnitOfWorkOutputPort:
        return self._unit_of_work


@pytest.mark.anyio
async def test_create_statement_cycle_returns_created_cycle_and_commits() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = _build_credit_card_ledger_account()
    statement_cycles = _StatementCycleOutputPortStub()
    unit_of_work = _UnitOfWorkStub(ledger_accounts, statement_cycles)
    use_case = StatementCycleUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    result = await use_case.create_statement_cycle(_build_create_data())

    assert result.id == 1
    assert result.ledger_account_id == 1
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_create_statement_cycle_raises_for_missing_ledger_account() -> None:
    unit_of_work = _UnitOfWorkStub(
        _LedgerAccountOutputPortStub(),
        _StatementCycleOutputPortStub(),
    )
    use_case = StatementCycleUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    with pytest.raises(LedgerAccountNotFoundError):
        await use_case.create_statement_cycle(_build_create_data())


@pytest.mark.anyio
async def test_create_statement_cycle_raises_for_invalid_ledger_account() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        kind=LedgerAccountKind.BANK_ACCOUNT,
        currency=Currency.BRL,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    unit_of_work = _UnitOfWorkStub(ledger_accounts, _StatementCycleOutputPortStub())
    use_case = StatementCycleUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    with pytest.raises(StatementCycleLedgerAccountInvalidError):
        await use_case.create_statement_cycle(_build_create_data())


@pytest.mark.anyio
async def test_update_statement_cycle_translates_not_found_output_error() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = _build_credit_card_ledger_account()
    statement_cycles = _StatementCycleOutputPortStub()
    statement_cycles.statement_cycles[1] = StatementCycle(
        id=1,
        ledger_account_id=1,
        cycle_start=date(2026, 5, 1),
        cycle_end=date(2026, 5, 31),
        closing_date=date(2026, 5, 28),
        due_date=date(2026, 6, 5),
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    statement_cycles.update_error = StatementCycleNotFoundOutputPortError()
    use_case = StatementCycleUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(ledger_accounts, statement_cycles)),
    )

    with pytest.raises(StatementCycleNotFoundError):
        await use_case.update_statement_cycle(1, _build_update_data())


@pytest.mark.anyio
async def test_delete_statement_cycle_soft_deletes_by_default() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = _build_credit_card_ledger_account()
    statement_cycles = _StatementCycleOutputPortStub()
    created = await statement_cycles.create_statement_cycle(
        NewStatementCycle(
            ledger_account_id=1,
            cycle_start=date(2026, 5, 1),
            cycle_end=date(2026, 5, 31),
            closing_date=date(2026, 5, 28),
            due_date=date(2026, 6, 5),
        ),
    )
    unit_of_work = _UnitOfWorkStub(ledger_accounts, statement_cycles)
    use_case = StatementCycleUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    await use_case.delete_statement_cycle(created.id)

    assert created.id in statement_cycles.deleted_statement_cycle_ids
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_list_statement_cycles_returns_active_statement_cycles() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = _build_credit_card_ledger_account()
    statement_cycles = _StatementCycleOutputPortStub()
    created = await statement_cycles.create_statement_cycle(
        NewStatementCycle(
            ledger_account_id=1,
            cycle_start=date(2026, 5, 1),
            cycle_end=date(2026, 5, 31),
            closing_date=date(2026, 5, 28),
            due_date=date(2026, 6, 5),
        ),
    )
    await statement_cycles.create_statement_cycle(
        NewStatementCycle(
            ledger_account_id=1,
            cycle_start=date(2026, 6, 1),
            cycle_end=date(2026, 6, 30),
            closing_date=date(2026, 6, 28),
            due_date=date(2026, 7, 5),
        ),
    )
    await statement_cycles.soft_delete_statement_cycle(created.id)
    use_case = StatementCycleUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(ledger_accounts, statement_cycles)),
    )

    page = await use_case.list_statement_cycles(
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="created_at", direction=SortDirection.ASC),),
        ),
    )

    assert [statement_cycle.id for statement_cycle in page.items] == [2]

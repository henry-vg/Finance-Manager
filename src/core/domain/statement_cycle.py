from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum


class StatementCycleSortableField(IntEnum):
    ID = 1
    LEDGER_ACCOUNT_ID = 2
    CYCLE_START = 3
    CYCLE_END = 4
    CLOSING_DATE = 5
    DUE_DATE = 6
    CREATED_AT = 7
    UPDATED_AT = 8


@dataclass(frozen=True)
class StatementCycle:
    id: int
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewStatementCycle:
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date


@dataclass(frozen=True)
class StatementCycleChanges:
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date


@dataclass(frozen=True)
class CreateStatementCycleData:
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date


@dataclass(frozen=True)
class UpdateStatementCycleData:
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date


class StatementCycleNotFoundError(Exception):
    pass


class StatementCycleLedgerAccountInvalidError(Exception):
    pass

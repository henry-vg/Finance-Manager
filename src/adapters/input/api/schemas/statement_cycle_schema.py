from datetime import date, datetime

from .base import ApiSchemaBase


class CreateStatementCycleRequest(ApiSchemaBase):
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date


class UpdateStatementCycleRequest(ApiSchemaBase):
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date


class StatementCycleResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    ledger_account_id: int
    cycle_start: date
    cycle_end: date
    closing_date: date
    due_date: date

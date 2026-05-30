from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from .base import ApiSchemaBase


class LedgerAccountTypeSchema(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    INCOME = "income"
    EXPENSE = "expense"
    EQUITY = "equity"


class LedgerAccountInstrumentKindSchema(StrEnum):
    BANK_ACCOUNT = "bank_account"
    CREDIT_CARD = "credit_card"
    WALLET = "wallet"


class LedgerAccountBalanceResponse(ApiSchemaBase):
    currency_id: int
    current_balance: Decimal
    future_balance: Decimal


class CreateLedgerAccountRequest(ApiSchemaBase):
    title: str
    type: LedgerAccountTypeSchema
    instrument_kind: LedgerAccountInstrumentKindSchema | None = None


class UpdateLedgerAccountRequest(ApiSchemaBase):
    title: str
    type: LedgerAccountTypeSchema
    instrument_kind: LedgerAccountInstrumentKindSchema | None = None


class LedgerAccountResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    type: LedgerAccountTypeSchema
    instrument_kind: LedgerAccountInstrumentKindSchema | None
    balances: tuple[LedgerAccountBalanceResponse, ...] = ()

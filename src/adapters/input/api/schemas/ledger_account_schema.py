from datetime import datetime
from enum import StrEnum

from .base import ApiSchemaBase


class CurrencySchema(StrEnum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"


class LedgerAccountTypeSchema(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    INCOME = "income"
    EXPENSE = "expense"
    EQUITY = "equity"


class LedgerAccountKindSchema(StrEnum):
    BANK_ACCOUNT = "bank_account"
    CREDIT_CARD = "credit_card"
    WALLET = "wallet"
    OTHER = "other"


class CreateLedgerAccountRequest(ApiSchemaBase):
    title: str
    type: LedgerAccountTypeSchema
    kind: LedgerAccountKindSchema
    currency: CurrencySchema


class UpdateLedgerAccountRequest(ApiSchemaBase):
    title: str
    type: LedgerAccountTypeSchema
    kind: LedgerAccountKindSchema
    currency: CurrencySchema


class LedgerAccountResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    type: LedgerAccountTypeSchema
    kind: LedgerAccountKindSchema
    currency: CurrencySchema

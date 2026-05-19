from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import ApiSchemaBase


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
    currency_iso_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")


class UpdateLedgerAccountRequest(ApiSchemaBase):
    title: str
    type: LedgerAccountTypeSchema
    kind: LedgerAccountKindSchema
    currency_iso_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")


class LedgerAccountResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    type: LedgerAccountTypeSchema
    kind: LedgerAccountKindSchema
    currency_iso_code: str

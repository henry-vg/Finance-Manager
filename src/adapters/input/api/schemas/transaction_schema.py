from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field

from .base import ApiSchemaBase


class TransactionStatusSchema(StrEnum):
    PENDING = "pending"
    POSTED = "posted"
    VOIDED = "voided"


class TransactionEntryTagRequest(ApiSchemaBase):
    tag_id: int = Field(ge=1)


class TransactionEntryRequest(ApiSchemaBase):
    ledger_account_id: int = Field(ge=1)
    amount: Decimal
    currency_id: int = Field(ge=1)
    statement_closing_date: date | None = None
    statement_due_date: date | None = None
    entry_tags: tuple[TransactionEntryTagRequest, ...] = ()


class CreateTransactionRequest(ApiSchemaBase):
    effective_at: datetime
    title: str = Field(min_length=1)
    description: str | None = None
    status: TransactionStatusSchema
    entries: tuple[TransactionEntryRequest, ...]


class UpdateTransactionRequest(ApiSchemaBase):
    effective_at: datetime
    title: str = Field(min_length=1)
    description: str | None = None
    entries: tuple[TransactionEntryRequest, ...]


class TransactionEntryTagResponse(ApiSchemaBase):
    entry_id: int
    tag_id: int


class TransactionEntryResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    transaction_id: int
    ledger_account_id: int
    amount_in_dollars: Decimal
    currency_id: int
    planned_exchange_rate_to_dollars: Decimal
    posting_exchange_rate_to_dollars: Decimal | None
    statement_closing_date: date | None
    statement_due_date: date | None


class TransactionEntryWithTagsResponse(ApiSchemaBase):
    entry: TransactionEntryResponse
    entry_tags: tuple[TransactionEntryTagResponse, ...] = ()


class TransactionResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatusSchema
    entries: tuple[TransactionEntryWithTagsResponse, ...] = ()


class TransactionSummaryResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatusSchema

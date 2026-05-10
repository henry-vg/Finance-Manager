from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum


class Currency(IntEnum):
    BRL = 1
    USD = 2
    EUR = 3


class LedgerAccountType(IntEnum):
    ASSET = 1
    LIABILITY = 2
    INCOME = 3
    EXPENSE = 4
    EQUITY = 5


class LedgerAccountKind(IntEnum):
    BANK_ACCOUNT = 1
    CREDIT_CARD = 2
    WALLET = 3
    OTHER = 4


class LedgerAccountSortableField(IntEnum):
    ID = 1
    TITLE = 2
    TYPE = 3
    KIND = 4
    CURRENCY = 5
    CREATED_AT = 6
    UPDATED_AT = 7


@dataclass(frozen=True)
class LedgerAccount:
    id: int
    title: str
    type: LedgerAccountType
    kind: LedgerAccountKind
    currency: Currency
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewLedgerAccount:
    title: str
    type: LedgerAccountType
    kind: LedgerAccountKind
    currency: Currency


@dataclass(frozen=True)
class LedgerAccountChanges:
    title: str
    type: LedgerAccountType
    kind: LedgerAccountKind
    currency: Currency


@dataclass(frozen=True)
class CreateLedgerAccountData:
    title: str
    type: LedgerAccountType
    kind: LedgerAccountKind
    currency: Currency


@dataclass(frozen=True)
class UpdateLedgerAccountData:
    title: str
    type: LedgerAccountType
    kind: LedgerAccountKind
    currency: Currency


class LedgerAccountNotFoundError(Exception):
    pass

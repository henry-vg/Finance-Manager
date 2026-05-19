from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import IntEnum

from src.core.domain.ledger_account import Currency


class TransactionStatus(IntEnum):
    PENDING = 1
    EFFECTIVE = 2
    CANCELED = 3


_ALLOWED_TRANSACTION_STATUS_TRANSITIONS = {
    TransactionStatus.PENDING: frozenset(
        {
            TransactionStatus.EFFECTIVE,
            TransactionStatus.CANCELED,
        },
    ),
    TransactionStatus.EFFECTIVE: frozenset({TransactionStatus.CANCELED}),
    TransactionStatus.CANCELED: frozenset(),
}


def can_transition_transaction_status(
    *,
    current_status: TransactionStatus,
    new_status: TransactionStatus,
) -> bool:
    return new_status in _ALLOWED_TRANSACTION_STATUS_TRANSITIONS[current_status]


@dataclass(frozen=True)
class Transaction:
    id: int
    created_at: datetime
    updated_at: datetime
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatus
    currency: Currency


@dataclass(frozen=True)
class NewEntryTag:
    tag_id: int


@dataclass(frozen=True)
class NewEntry:
    ledger_account_id: int
    amount: Decimal
    statement_closing_date: date | None
    statement_due_date: date | None
    entry_tags: tuple[NewEntryTag, ...] = ()


@dataclass(frozen=True)
class NewTransaction:
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatus
    currency: Currency
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class TransactionChanges:
    effective_at: datetime
    title: str
    description: str | None
    currency: Currency
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class CreateTransactionData:
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatus
    currency: Currency
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class UpdateTransactionData:
    effective_at: datetime
    title: str
    description: str | None
    currency: Currency
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class Entry:
    id: int
    created_at: datetime
    updated_at: datetime
    transaction_id: int
    ledger_account_id: int
    amount: Decimal
    statement_closing_date: date | None
    statement_due_date: date | None


@dataclass(frozen=True)
class EntryTag:
    entry_id: int
    tag_id: int


@dataclass(frozen=True)
class EntryWithTags:
    entry: Entry
    entry_tags: tuple[EntryTag, ...]


@dataclass(frozen=True)
class TransactionWithEntries:
    transaction: Transaction
    entries: tuple[EntryWithTags, ...]


class TransactionNotFoundError(Exception):
    pass


class TransactionMustBePendingError(Exception):
    pass


class TransactionStatusTransitionNotAllowedError(Exception):
    pass


class TransactionMustHaveAtLeastTwoEntriesError(Exception):
    pass


class TransactionEntriesMustBalanceError(Exception):
    pass


class TransactionLedgerAccountNotFoundError(Exception):
    pass


class TransactionLedgerAccountCurrencyMismatchError(Exception):
    pass


class TransactionTagNotFoundError(Exception):
    pass


class TransactionEntryTagsMustBeUniqueError(Exception):
    pass


class TransactionEntryStatementDatesMustBeProvidedTogetherError(Exception):
    pass


class TransactionEntryRequiresCreditCardLedgerAccountError(Exception):
    pass


class TransactionEntryStatementDueDateMustBeAfterClosingDateError(Exception):
    pass

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import IntEnum


class TransactionStatus(IntEnum):
    PENDING = 1
    POSTED = 2
    VOIDED = 3


class TransactionSortableField(IntEnum):
    ID = 1
    CREATED_AT = 2
    UPDATED_AT = 3
    EFFECTIVE_AT = 4
    TITLE = 5
    STATUS = 6


_ALLOWED_TRANSACTION_STATUS_TRANSITIONS = {
    TransactionStatus.PENDING: (
        TransactionStatus.POSTED,
        TransactionStatus.VOIDED,
    ),
    TransactionStatus.POSTED: (),
    TransactionStatus.VOIDED: (),
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


@dataclass(frozen=True)
class NewEntryTag:
    tag_id: int


@dataclass(frozen=True)
class NewEntry:
    ledger_account_id: int
    amount: Decimal
    amount_in_dollars: Decimal | None
    currency_id: int
    statement_closing_date: date | None
    statement_due_date: date | None
    entry_tags: tuple[NewEntryTag, ...] = ()
    planned_exchange_rate_to_dollars: Decimal | None = None
    posting_exchange_rate_to_dollars: Decimal | None = None


@dataclass(frozen=True)
class NewTransaction:
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatus
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class TransactionChanges:
    effective_at: datetime
    title: str
    description: str | None
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class CreateTransactionData:
    effective_at: datetime
    title: str
    description: str | None
    status: TransactionStatus
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class UpdateTransactionData:
    effective_at: datetime
    title: str
    description: str | None
    entries: tuple[NewEntry, ...]


@dataclass(frozen=True)
class Entry:
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


class TransactionEntryCurrencyNotFoundError(Exception):
    pass


class TransactionEntryExchangeRateUnavailableError(Exception):
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

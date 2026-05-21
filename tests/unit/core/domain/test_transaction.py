from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.core.domain.transaction import (
    CreateTransactionData,
    Entry,
    EntryTag,
    EntryWithTags,
    NewEntry,
    NewEntryTag,
    NewTransaction,
    Transaction,
    TransactionChanges,
    TransactionEntriesMustBalanceError,
    TransactionEntryRequiresCreditCardLedgerAccountError,
    TransactionEntryStatementDatesMustBeProvidedTogetherError,
    TransactionEntryStatementDueDateMustBeAfterClosingDateError,
    TransactionEntryTagsMustBeUniqueError,
    TransactionLedgerAccountCurrencyMismatchError,
    TransactionLedgerAccountNotFoundError,
    TransactionMustBePendingError,
    TransactionMustHaveAtLeastTwoEntriesError,
    TransactionNotFoundError,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
    TransactionTagNotFoundError,
    TransactionWithEntries,
    UpdateTransactionData,
    can_transition_transaction_status,
)


def _timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def _new_entry() -> NewEntry:
    return NewEntry(
        ledger_account_id=10,
        amount=Decimal("12.34"),
        statement_closing_date=date(2026, 5, 28),
        statement_due_date=date(2026, 6, 5),
        entry_tags=(NewEntryTag(tag_id=100),),
    )


def test_transaction_status_exposes_all_public_members() -> None:
    assert tuple(TransactionStatus.__members__) == (
        "PENDING",
        "EFFECTIVE",
        "CANCELED",
    )


@pytest.mark.parametrize(
    ("current_status", "new_status", "expected"),
    [
        (TransactionStatus.PENDING, TransactionStatus.PENDING, False),
        (TransactionStatus.PENDING, TransactionStatus.EFFECTIVE, True),
        (TransactionStatus.PENDING, TransactionStatus.CANCELED, True),
        (TransactionStatus.EFFECTIVE, TransactionStatus.PENDING, False),
        (TransactionStatus.EFFECTIVE, TransactionStatus.EFFECTIVE, False),
        (TransactionStatus.EFFECTIVE, TransactionStatus.CANCELED, True),
        (TransactionStatus.CANCELED, TransactionStatus.PENDING, False),
        (TransactionStatus.CANCELED, TransactionStatus.EFFECTIVE, False),
        (TransactionStatus.CANCELED, TransactionStatus.CANCELED, False),
    ],
)
def test_can_transition_transaction_status_matches_transition_matrix(
    current_status: TransactionStatus,
    new_status: TransactionStatus,
    expected: bool,
) -> None:
    assert (
        can_transition_transaction_status(
            current_status=current_status,
            new_status=new_status,
        )
        is expected
    )


def test_transaction_keeps_persisted_fields() -> None:
    transaction = Transaction(
        id=1,
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
        effective_at=_timestamp(3),
        title="Pay credit card",
        description="Monthly statement",
        status=TransactionStatus.PENDING,
        currency="BRL",
    )

    assert transaction.id == 1
    assert transaction.created_at == _timestamp(1)
    assert transaction.updated_at == _timestamp(2)
    assert transaction.effective_at == _timestamp(3)
    assert transaction.title == "Pay credit card"
    assert transaction.description == "Monthly statement"
    assert transaction.status == TransactionStatus.PENDING
    assert transaction.currency == "BRL"


def test_new_entry_keeps_statement_dates_and_tags() -> None:
    entry = _new_entry()

    assert entry.ledger_account_id == 10
    assert entry.amount == Decimal("12.34")
    assert entry.statement_closing_date == date(2026, 5, 28)
    assert entry.statement_due_date == date(2026, 6, 5)
    assert entry.entry_tags == (NewEntryTag(tag_id=100),)


def test_new_transaction_keeps_status_currency_and_entries() -> None:
    entry = _new_entry()
    transaction = NewTransaction(
        effective_at=_timestamp(4),
        title="Groceries",
        description=None,
        status=TransactionStatus.EFFECTIVE,
        currency="USD",
        entries=(entry,),
    )

    assert transaction.effective_at == _timestamp(4)
    assert transaction.title == "Groceries"
    assert transaction.description is None
    assert transaction.status == TransactionStatus.EFFECTIVE
    assert transaction.currency == "USD"
    assert transaction.entries == (entry,)


def test_create_transaction_data_keeps_status_currency_and_entries() -> None:
    entry = _new_entry()
    transaction_data = CreateTransactionData(
        effective_at=_timestamp(5),
        title="Salary",
        description="May payroll",
        status=TransactionStatus.PENDING,
        currency="USD",
        entries=(entry,),
    )

    assert transaction_data.effective_at == _timestamp(5)
    assert transaction_data.title == "Salary"
    assert transaction_data.description == "May payroll"
    assert transaction_data.status == TransactionStatus.PENDING
    assert transaction_data.currency == "USD"
    assert transaction_data.entries == (entry,)


@pytest.mark.parametrize("factory", [TransactionChanges, UpdateTransactionData])
def test_transaction_change_models_keep_currency_and_entries(
    factory: type[TransactionChanges | UpdateTransactionData],
) -> None:
    entry = _new_entry()
    transaction_data = factory(
        effective_at=_timestamp(6),
        title="Updated title",
        description="Updated description",
        currency="EUR",
        entries=(entry,),
    )

    assert transaction_data.effective_at == _timestamp(6)
    assert transaction_data.title == "Updated title"
    assert transaction_data.description == "Updated description"
    assert transaction_data.currency == "EUR"
    assert transaction_data.entries == (entry,)


def test_entry_snapshots_keep_relationship_shape() -> None:
    entry = Entry(
        id=11,
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
        transaction_id=21,
        ledger_account_id=31,
        amount=Decimal("-9.99"),
        statement_closing_date=date(2026, 5, 28),
        statement_due_date=date(2026, 6, 5),
    )
    entry_tag = EntryTag(entry_id=11, tag_id=41)
    entry_with_tags = EntryWithTags(entry=entry, entry_tags=(entry_tag,))
    transaction = Transaction(
        id=21,
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
        effective_at=_timestamp(3),
        title="Trip",
        description=None,
        status=TransactionStatus.EFFECTIVE,
        currency="USD",
    )
    transaction_with_entries = TransactionWithEntries(
        transaction=transaction,
        entries=(entry_with_tags,),
    )

    assert entry.transaction_id == 21
    assert entry.ledger_account_id == 31
    assert entry.amount == Decimal("-9.99")
    assert entry_tag.tag_id == 41
    assert entry_with_tags.entry == entry
    assert entry_with_tags.entry_tags == (entry_tag,)
    assert transaction_with_entries.transaction == transaction
    assert transaction_with_entries.entries == (entry_with_tags,)


@pytest.mark.parametrize(
    "error_type",
    [
        TransactionNotFoundError,
        TransactionMustBePendingError,
        TransactionStatusTransitionNotAllowedError,
        TransactionMustHaveAtLeastTwoEntriesError,
        TransactionEntriesMustBalanceError,
        TransactionLedgerAccountNotFoundError,
        TransactionLedgerAccountCurrencyMismatchError,
        TransactionTagNotFoundError,
        TransactionEntryTagsMustBeUniqueError,
        TransactionEntryStatementDatesMustBeProvidedTogetherError,
        TransactionEntryRequiresCreditCardLedgerAccountError,
        TransactionEntryStatementDueDateMustBeAfterClosingDateError,
    ],
)
def test_transaction_errors_are_domain_exceptions(
    error_type: type[Exception],
) -> None:
    assert isinstance(error_type(), Exception)

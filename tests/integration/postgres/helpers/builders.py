from datetime import UTC, date, datetime
from decimal import Decimal

from src.core.domain.currency import CurrencyChanges, NewCurrency
from src.core.domain.ledger_account import (
    LedgerAccountChanges,
    LedgerAccountInstrumentKind,
    LedgerAccountType,
    NewLedgerAccount,
)
from src.core.domain.tag import NewTag, TagChanges
from src.core.domain.transaction import (
    NewEntry,
    NewEntryTag,
    NewTransaction,
    TransactionChanges,
    TransactionStatus,
)
from src.core.domain.user import NewUser, UserChanges


def build_new_currency(
    *,
    iso_code: str = "USD",
    iso_numeric: str = "840",
    name: str = "US Dollar",
    symbol: str = "$",
    decimal_places: int = 2,
) -> NewCurrency:
    return NewCurrency(
        iso_code=iso_code,
        iso_numeric=iso_numeric,
        name=name,
        symbol=symbol,
        decimal_places=decimal_places,
    )


def build_currency_changes(
    *,
    iso_code: str = "BRL",
    iso_numeric: str = "986",
    name: str = "Brazilian Real",
    symbol: str = "R$",
    decimal_places: int = 2,
) -> CurrencyChanges:
    return CurrencyChanges(
        iso_code=iso_code,
        iso_numeric=iso_numeric,
        name=name,
        symbol=symbol,
        decimal_places=decimal_places,
    )


def build_new_tag(*, title: str = "Food") -> NewTag:
    return NewTag(title=title)


def build_tag_changes(*, title: str = "Utilities") -> TagChanges:
    return TagChanges(title=title)


def build_new_ledger_account(
    *,
    title: str = "Main Account",
    type: LedgerAccountType = LedgerAccountType.ASSET,
    instrument_kind: LedgerAccountInstrumentKind | None = (
        LedgerAccountInstrumentKind.BANK_ACCOUNT
    ),
) -> NewLedgerAccount:
    return NewLedgerAccount(
        title=title,
        type=type,
        instrument_kind=instrument_kind,
    )


def build_ledger_account_changes(
    *,
    title: str = "Credit Card",
    type: LedgerAccountType = LedgerAccountType.LIABILITY,
    instrument_kind: LedgerAccountInstrumentKind | None = (
        LedgerAccountInstrumentKind.CREDIT_CARD
    ),
) -> LedgerAccountChanges:
    return LedgerAccountChanges(
        title=title,
        type=type,
        instrument_kind=instrument_kind,
    )


def build_new_user(
    *,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = "ada@example.com",
    password_hash: str = "hashed::plain-password",
    birth_date: date = date(1815, 12, 10),
) -> NewUser:
    return NewUser(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        birth_date=birth_date,
    )


def build_user_changes(
    *,
    first_name: str = "Grace",
    last_name: str = "Hopper",
    email: str = "grace@example.com",
    password_hash: str = "hashed::new-password",
    birth_date: date = date(1906, 12, 9),
) -> UserChanges:
    return UserChanges(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        birth_date=birth_date,
    )


def build_new_transaction(
    *,
    expense_ledger_account_id: int,
    credit_card_ledger_account_id: int,
    food_tag_id: int,
    travel_tag_id: int,
    status: TransactionStatus = TransactionStatus.PENDING,
    expense_currency_id: int = 1,
    credit_card_currency_id: int = 1,
) -> NewTransaction:
    return NewTransaction(
        effective_at=datetime(2026, 5, 11, 14, 30, tzinfo=UTC),
        title="Airline tickets",
        description="Family vacation purchase",
        status=status,
        entries=(
            NewEntry(
                ledger_account_id=expense_ledger_account_id,
                amount=Decimal("1200.00"),
                currency_id=expense_currency_id,
                statement_closing_date=None,
                statement_due_date=None,
                entry_tags=(
                    NewEntryTag(tag_id=food_tag_id),
                    NewEntryTag(tag_id=travel_tag_id),
                ),
            ),
            NewEntry(
                ledger_account_id=credit_card_ledger_account_id,
                amount=Decimal("-1200.00"),
                currency_id=credit_card_currency_id,
                statement_closing_date=date(2026, 5, 31),
                statement_due_date=date(2026, 6, 10),
            ),
        ),
    )


def build_transaction_changes(
    *,
    expense_ledger_account_id: int,
    credit_card_ledger_account_id: int,
    travel_tag_id: int,
    expense_currency_id: int = 1,
    credit_card_currency_id: int = 1,
) -> TransactionChanges:
    return TransactionChanges(
        effective_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
        title="Hotel reservation",
        description="Updated pending purchase",
        entries=(
            NewEntry(
                ledger_account_id=expense_ledger_account_id,
                amount=Decimal("900.00"),
                currency_id=expense_currency_id,
                statement_closing_date=None,
                statement_due_date=None,
                entry_tags=(NewEntryTag(tag_id=travel_tag_id),),
            ),
            NewEntry(
                ledger_account_id=credit_card_ledger_account_id,
                amount=Decimal("-900.00"),
                currency_id=credit_card_currency_id,
                statement_closing_date=date(2026, 6, 30),
                statement_due_date=date(2026, 7, 10),
            ),
        ),
    )

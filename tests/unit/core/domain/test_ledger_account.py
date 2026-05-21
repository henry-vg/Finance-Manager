from datetime import UTC, datetime

import pytest

from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountChanges,
    LedgerAccountCurrencyISOCodeNotSupportedError,
    LedgerAccountKind,
    LedgerAccountNotFoundError,
    LedgerAccountSortableField,
    LedgerAccountType,
    NewLedgerAccount,
    UpdateLedgerAccountData,
)


def _timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def test_ledger_account_keeps_persisted_fields() -> None:
    ledger_account = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        kind=LedgerAccountKind.BANK_ACCOUNT,
        currency_iso_code="BRL",
        created_at=_timestamp(1),
        updated_at=_timestamp(2),
    )

    assert ledger_account.id == 1
    assert ledger_account.title == "Main Account"
    assert ledger_account.type == LedgerAccountType.ASSET
    assert ledger_account.kind == LedgerAccountKind.BANK_ACCOUNT
    assert ledger_account.currency_iso_code == "BRL"
    assert ledger_account.created_at == _timestamp(1)
    assert ledger_account.updated_at == _timestamp(2)


@pytest.mark.parametrize(
    "factory",
    [
        NewLedgerAccount,
        LedgerAccountChanges,
        CreateLedgerAccountData,
        UpdateLedgerAccountData,
    ],
)
def test_ledger_account_write_models_keep_type_kind_and_currency(
    factory: type[
        NewLedgerAccount
        | LedgerAccountChanges
        | CreateLedgerAccountData
        | UpdateLedgerAccountData
    ],
) -> None:
    ledger_account_data = factory(
        title="Credit Card",
        type=LedgerAccountType.LIABILITY,
        kind=LedgerAccountKind.CREDIT_CARD,
        currency_iso_code="USD",
    )

    assert ledger_account_data.title == "Credit Card"
    assert ledger_account_data.type == LedgerAccountType.LIABILITY
    assert ledger_account_data.kind == LedgerAccountKind.CREDIT_CARD
    assert ledger_account_data.currency_iso_code == "USD"


def test_ledger_account_type_exposes_all_public_members() -> None:
    assert tuple(LedgerAccountType.__members__) == (
        "ASSET",
        "LIABILITY",
        "INCOME",
        "EXPENSE",
        "EQUITY",
    )


def test_ledger_account_kind_exposes_all_public_members() -> None:
    assert tuple(LedgerAccountKind.__members__) == (
        "BANK_ACCOUNT",
        "CREDIT_CARD",
        "WALLET",
        "OTHER",
    )


def test_ledger_account_sortable_field_exposes_all_public_members() -> None:
    assert tuple(LedgerAccountSortableField.__members__) == (
        "ID",
        "CREATED_AT",
        "UPDATED_AT",
        "TITLE",
        "TYPE",
        "KIND",
        "CURRENCY_ISO_CODE",
    )


@pytest.mark.parametrize(
    "error_type",
    [LedgerAccountNotFoundError, LedgerAccountCurrencyISOCodeNotSupportedError],
)
def test_ledger_account_errors_are_domain_exceptions(
    error_type: type[Exception],
) -> None:
    assert isinstance(error_type(), Exception)

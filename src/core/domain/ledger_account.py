from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntEnum


class LedgerAccountType(IntEnum):
    ASSET = 1
    LIABILITY = 2
    INCOME = 3
    EXPENSE = 4
    EQUITY = 5


class LedgerAccountInstrumentKind(IntEnum):
    BANK_ACCOUNT = 1
    CREDIT_CARD = 2
    WALLET = 3


_ALLOWED_LEDGER_ACCOUNT_INSTRUMENT_KINDS = {
    LedgerAccountType.ASSET: (
        None,
        LedgerAccountInstrumentKind.BANK_ACCOUNT,
        LedgerAccountInstrumentKind.WALLET,
    ),
    LedgerAccountType.LIABILITY: (
        None,
        LedgerAccountInstrumentKind.CREDIT_CARD,
    ),
    LedgerAccountType.INCOME: (None,),
    LedgerAccountType.EXPENSE: (None,),
    LedgerAccountType.EQUITY: (None,),
}


def can_assign_ledger_account_instrument_kind(
    *,
    ledger_account_type: LedgerAccountType,
    instrument_kind: LedgerAccountInstrumentKind | None,
) -> bool:
    return (
        instrument_kind in _ALLOWED_LEDGER_ACCOUNT_INSTRUMENT_KINDS[ledger_account_type]
    )


class LedgerAccountSortableField(IntEnum):
    ID = 1
    CREATED_AT = 2
    UPDATED_AT = 3
    TITLE = 4
    TYPE = 5
    INSTRUMENT_KIND = 6


@dataclass(frozen=True)
class LedgerAccountBalance:
    currency_id: int
    current_balance: Decimal
    future_balance: Decimal


@dataclass(frozen=True)
class LedgerAccount:
    id: int
    created_at: datetime
    updated_at: datetime
    title: str
    type: LedgerAccountType
    instrument_kind: LedgerAccountInstrumentKind | None
    balances: tuple[LedgerAccountBalance, ...] = ()


@dataclass(frozen=True)
class NewLedgerAccount:
    title: str
    type: LedgerAccountType
    instrument_kind: LedgerAccountInstrumentKind | None


@dataclass(frozen=True)
class LedgerAccountChanges:
    title: str
    type: LedgerAccountType
    instrument_kind: LedgerAccountInstrumentKind | None


@dataclass(frozen=True)
class CreateLedgerAccountData:
    title: str
    type: LedgerAccountType
    instrument_kind: LedgerAccountInstrumentKind | None


@dataclass(frozen=True)
class UpdateLedgerAccountData:
    title: str
    type: LedgerAccountType
    instrument_kind: LedgerAccountInstrumentKind | None


class LedgerAccountNotFoundError(Exception):
    pass


class LedgerAccountInstrumentKindNotAllowedError(Exception):
    pass

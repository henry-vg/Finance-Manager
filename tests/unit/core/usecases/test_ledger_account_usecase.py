from datetime import UTC, datetime

import pytest

from src.core.domain.currency import Currency
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountChanges,
    LedgerAccountCurrencyISOCodeNotSupportedError,
    LedgerAccountKind,
    LedgerAccountNotFoundError,
    LedgerAccountType,
    NewLedgerAccount,
    UpdateLedgerAccountData,
)
from src.core.ports.output.currency_output_port import CurrencyOutputPort
from src.core.ports.output.ledger_account_output_port import (
    LedgerAccountNotFoundOutputPortError,
    LedgerAccountOutputPort,
)
from src.core.ports.output.tag_output_port import TagOutputPort
from src.core.ports.output.transaction_output_port import TransactionOutputPort
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.ports.output.user_output_port import UserOutputPort
from src.core.shared import ListQuery, Page, SortDirection, SortTerm
from src.core.usecases.ledger_account_usecase import LedgerAccountUseCase


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def _build_create_data() -> CreateLedgerAccountData:
    return CreateLedgerAccountData(
        title="Main Account",
        type=LedgerAccountType.ASSET,
        kind=LedgerAccountKind.BANK_ACCOUNT,
        currency_iso_code="BRL",
    )


def _build_update_data() -> UpdateLedgerAccountData:
    return UpdateLedgerAccountData(
        title="Credit Card",
        type=LedgerAccountType.LIABILITY,
        kind=LedgerAccountKind.CREDIT_CARD,
        currency_iso_code="USD",
    )


def _build_currency(
    *,
    currency_id: int,
    iso_code: str,
) -> Currency:
    return Currency(
        id=currency_id,
        iso_code=iso_code,
        iso_numeric="000",
        name=f"{iso_code} currency",
        symbol="$",
        decimal_places=2,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )


class _LedgerAccountOutputPortStub(LedgerAccountOutputPort):
    def __init__(self) -> None:
        self.ledger_accounts: dict[int, LedgerAccount] = {}
        self.deleted_ledger_account_ids: set[int] = set()
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self.delete_error: Exception | None = None
        self.list_queries: list[ListQuery] = []
        self.created_ledger_accounts: list[NewLedgerAccount] = []
        self.updated_ledger_accounts: list[tuple[int, LedgerAccountChanges]] = []
        self.next_id = 1

    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]:
        self.list_queries.append(list_query)
        active_ledger_accounts = [
            ledger_account
            for ledger_account_id, ledger_account in self.ledger_accounts.items()
            if ledger_account_id not in self.deleted_ledger_account_ids
        ]
        active_ledger_accounts.sort(key=lambda ledger_account: ledger_account.id)

        return Page[LedgerAccount](
            items=active_ledger_accounts[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_ledger_accounts),
        )

    async def get_ledger_account_by_id(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        if ledger_account_id in self.deleted_ledger_account_ids:
            return None

        return self.ledger_accounts.get(ledger_account_id)

    async def get_ledger_account_by_id_including_deleted(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        return self.ledger_accounts.get(ledger_account_id)

    async def create_ledger_account(
        self,
        new_ledger_account: NewLedgerAccount,
    ) -> LedgerAccount:
        if self.create_error is not None:
            raise self.create_error

        self.created_ledger_accounts.append(new_ledger_account)
        ledger_account = LedgerAccount(
            id=self.next_id,
            title=new_ledger_account.title,
            type=new_ledger_account.type,
            kind=new_ledger_account.kind,
            currency_iso_code=new_ledger_account.currency_iso_code,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.ledger_accounts[ledger_account.id] = ledger_account
        self.next_id += 1
        return ledger_account

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        changes: LedgerAccountChanges,
    ) -> LedgerAccount:
        if self.update_error is not None:
            raise self.update_error

        current = self.ledger_accounts[ledger_account_id]
        updated = LedgerAccount(
            id=current.id,
            title=changes.title,
            type=changes.type,
            kind=changes.kind,
            currency_iso_code=changes.currency_iso_code,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.updated_ledger_accounts.append((ledger_account_id, changes))
        self.ledger_accounts[ledger_account_id] = updated
        return updated

    async def soft_delete_ledger_account(
        self,
        ledger_account_id: int,
    ) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_ledger_account_ids.add(ledger_account_id)

    async def hard_delete_ledger_account(
        self,
        ledger_account_id: int,
    ) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_ledger_account_ids.discard(ledger_account_id)
        self.ledger_accounts.pop(ledger_account_id, None)


class _CurrencyOutputPortStub(CurrencyOutputPort):
    def __init__(self) -> None:
        self.currencies_by_iso_code = {
            "BRL": _build_currency(currency_id=1, iso_code="BRL"),
            "USD": _build_currency(currency_id=2, iso_code="USD"),
        }
        self.queried_iso_codes: list[str] = []

    async def get_currency_by_iso_code(self, iso_code: str) -> Currency | None:
        self.queried_iso_codes.append(iso_code)
        return self.currencies_by_iso_code.get(iso_code)


class _UnitOfWorkStub(UnitOfWorkOutputPort):
    def __init__(
        self,
        ledger_accounts: _LedgerAccountOutputPortStub,
        currencies: _CurrencyOutputPortStub | None = None,
    ) -> None:
        self._ledger_accounts = ledger_accounts
        self._currencies = currencies or _CurrencyOutputPortStub()
        self.committed = False

    @property
    def currencies(self) -> CurrencyOutputPort:
        return self._currencies

    @property
    def ledger_accounts(self) -> LedgerAccountOutputPort:
        return self._ledger_accounts

    @property
    def tags(self) -> TagOutputPort:
        raise RuntimeError("tags output port is unused in ledger account tests")

    @property
    def transactions(self) -> TransactionOutputPort:
        raise RuntimeError(
            "transactions output port is unused in ledger account tests",
        )

    @property
    def users(self) -> UserOutputPort:
        raise RuntimeError("users output port is unused in ledger account tests")

    async def __aenter__(self) -> "_UnitOfWorkStub":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        del exc_type
        del exc
        del traceback

    async def commit(self) -> None:
        self.committed = True


class _UnitOfWorkFactoryStub(UnitOfWorkOutputPortFactory):
    def __init__(self, unit_of_work: _UnitOfWorkStub) -> None:
        self._unit_of_work = unit_of_work

    def __call__(self) -> UnitOfWorkOutputPort:
        return self._unit_of_work


@pytest.mark.anyio
async def test_create_ledger_account_returns_created_account_and_commits() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    unit_of_work = _UnitOfWorkStub(ledger_accounts)
    use_case = LedgerAccountUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    result = await use_case.create_ledger_account(_build_create_data())

    assert result.id == 1
    assert result.title == "Main Account"
    assert result.type == LedgerAccountType.ASSET
    assert result.kind == LedgerAccountKind.BANK_ACCOUNT
    assert result.currency_iso_code == "BRL"
    assert unit_of_work.currencies.queried_iso_codes == ["BRL"]
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_create_ledger_account_raises_for_unsupported_currency_iso_code() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    unit_of_work = _UnitOfWorkStub(ledger_accounts)
    use_case = LedgerAccountUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    with pytest.raises(LedgerAccountCurrencyISOCodeNotSupportedError):
        await use_case.create_ledger_account(
            CreateLedgerAccountData(
                title="Main Account",
                type=LedgerAccountType.ASSET,
                kind=LedgerAccountKind.BANK_ACCOUNT,
                currency_iso_code="JPY",
            ),
        )

    assert unit_of_work.committed is False


@pytest.mark.anyio
async def test_get_ledger_account_raises_for_missing_account() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    use_case = LedgerAccountUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(ledger_accounts)),
    )

    with pytest.raises(LedgerAccountNotFoundError):
        await use_case.get_ledger_account(999)


@pytest.mark.anyio
async def test_update_ledger_account_raises_when_account_does_not_exist() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    use_case = LedgerAccountUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(ledger_accounts)),
    )

    with pytest.raises(LedgerAccountNotFoundError):
        await use_case.update_ledger_account(999, _build_update_data())


@pytest.mark.anyio
async def test_update_ledger_account_translates_not_found_output_error() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = LedgerAccount(
        id=1,
        title="Main Account",
        type=LedgerAccountType.ASSET,
        kind=LedgerAccountKind.BANK_ACCOUNT,
        currency_iso_code="BRL",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    ledger_accounts.update_error = LedgerAccountNotFoundOutputPortError()
    use_case = LedgerAccountUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(ledger_accounts)),
    )

    with pytest.raises(LedgerAccountNotFoundError):
        await use_case.update_ledger_account(1, _build_update_data())


@pytest.mark.anyio
async def test_delete_ledger_account_soft_deletes_by_default() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    created = await ledger_accounts.create_ledger_account(
        NewLedgerAccount(
            title="Main Account",
            type=LedgerAccountType.ASSET,
            kind=LedgerAccountKind.BANK_ACCOUNT,
            currency_iso_code="BRL",
        ),
    )
    unit_of_work = _UnitOfWorkStub(ledger_accounts)
    use_case = LedgerAccountUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    await use_case.delete_ledger_account(created.id)

    assert created.id in ledger_accounts.deleted_ledger_account_ids
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_list_ledger_accounts_returns_active_accounts() -> None:
    ledger_accounts = _LedgerAccountOutputPortStub()
    created = await ledger_accounts.create_ledger_account(
        NewLedgerAccount(
            title="Main Account",
            type=LedgerAccountType.ASSET,
            kind=LedgerAccountKind.BANK_ACCOUNT,
            currency_iso_code="BRL",
        ),
    )
    await ledger_accounts.create_ledger_account(
        NewLedgerAccount(
            title="Credit Card",
            type=LedgerAccountType.LIABILITY,
            kind=LedgerAccountKind.CREDIT_CARD,
            currency_iso_code="USD",
        ),
    )
    await ledger_accounts.soft_delete_ledger_account(created.id)
    use_case = LedgerAccountUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(ledger_accounts)),
    )

    page = await use_case.list_ledger_accounts(
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="created_at", direction=SortDirection.ASC),),
        ),
    )

    assert [ledger_account.title for ledger_account in page.items] == ["Credit Card"]

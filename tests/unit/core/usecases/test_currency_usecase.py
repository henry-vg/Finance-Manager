from datetime import UTC, datetime

import pytest

from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    CurrencyChanges,
    CurrencyDataValidationError,
    CurrencyISOCodeConflictError,
    CurrencyNotFoundError,
    NewCurrency,
    UpdateCurrencyData,
)
from src.core.ports.output.currency_output_port import (
    CurrencyISOCodeConflictOutputPortError,
    CurrencyNotFoundOutputPortError,
    CurrencyOutputPort,
)
from src.core.ports.output.ledger_account_output_port import LedgerAccountOutputPort
from src.core.ports.output.tag_output_port import TagOutputPort
from src.core.ports.output.transaction_output_port import TransactionOutputPort
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.ports.output.user_output_port import UserOutputPort
from src.core.shared import ListQuery, Page, SortDirection, SortTerm
from src.core.usecases.currency_usecase import CurrencyUseCase


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class _CurrencyOutputPortStub(CurrencyOutputPort):
    def __init__(self) -> None:
        self.currencies: dict[int, Currency] = {}
        self.deleted_currency_ids: set[int] = set()
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self.delete_error: Exception | None = None
        self.next_id = 1

    async def list_currencies(self, list_query: ListQuery) -> Page[Currency]:
        active_currencies = [
            currency
            for currency_id, currency in self.currencies.items()
            if currency_id not in self.deleted_currency_ids
        ]
        active_currencies.sort(key=lambda currency: currency.id)
        return Page[Currency](
            items=(
                active_currencies[
                    list_query.offset : list_query.offset + list_query.limit
                ]
            ),
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_currencies),
        )

    async def get_currency_by_id(self, currency_id: int) -> Currency | None:
        if currency_id in self.deleted_currency_ids:
            return None

        return self.currencies.get(currency_id)

    async def get_currency_by_id_including_deleted(
        self,
        currency_id: int,
    ) -> Currency | None:
        return self.currencies.get(currency_id)

    async def get_currency_by_iso_code(self, iso_code: str) -> Currency | None:
        for currency_id, currency in self.currencies.items():
            if currency_id in self.deleted_currency_ids:
                continue

            if currency.iso_code == iso_code:
                return currency

        return None

    async def create_currency(self, new_currency: NewCurrency) -> Currency:
        if self.create_error is not None:
            raise self.create_error

        currency = Currency(
            id=self.next_id,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
            iso_code=new_currency.iso_code,
            iso_numeric=new_currency.iso_numeric,
            name=new_currency.name,
            symbol=new_currency.symbol,
            decimal_places=new_currency.decimal_places,
        )
        self.currencies[currency.id] = currency
        self.next_id += 1
        return currency

    async def update_currency(
        self,
        currency_id: int,
        changes: CurrencyChanges,
    ) -> Currency:
        if self.update_error is not None:
            raise self.update_error

        current = self.currencies[currency_id]
        updated = Currency(
            id=current.id,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
            iso_code=changes.iso_code,
            iso_numeric=changes.iso_numeric,
            name=changes.name,
            symbol=changes.symbol,
            decimal_places=changes.decimal_places,
        )
        self.currencies[currency_id] = updated
        return updated

    async def soft_delete_currency(self, currency_id: int) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_currency_ids.add(currency_id)

    async def hard_delete_currency(self, currency_id: int) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_currency_ids.discard(currency_id)
        self.currencies.pop(currency_id, None)


class _UnitOfWorkStub(UnitOfWorkOutputPort):
    def __init__(self, currencies: _CurrencyOutputPortStub) -> None:
        self._currencies = currencies
        self.committed = False

    @property
    def currencies(self) -> CurrencyOutputPort:
        return self._currencies

    @property
    def ledger_accounts(self) -> LedgerAccountOutputPort:
        raise RuntimeError("ledger_accounts output port is unused in currency tests")

    @property
    def tags(self) -> TagOutputPort:
        raise RuntimeError("tags output port is unused in currency tests")

    @property
    def transactions(self) -> TransactionOutputPort:
        raise RuntimeError("transactions output port is unused in currency tests")

    @property
    def users(self) -> UserOutputPort:
        raise RuntimeError("users output port is unused in currency tests")

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
async def test_create_currency_normalizes_iso_code_and_commits() -> None:
    currencies = _CurrencyOutputPortStub()
    unit_of_work = _UnitOfWorkStub(currencies)
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    result = await use_case.create_currency(
        CreateCurrencyData(
            iso_code=" brl ",
            iso_numeric="986",
            name="Brazilian Real",
            symbol="R$",
            decimal_places=2,
        ),
    )

    assert result.iso_code == "BRL"
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_create_currency_translates_iso_code_conflict_output_port_error() -> None:
    currencies = _CurrencyOutputPortStub()
    currencies.create_error = CurrencyISOCodeConflictOutputPortError()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyISOCodeConflictError):
        await use_case.create_currency(
            CreateCurrencyData(
                iso_code="USD",
                iso_numeric="840",
                name="US Dollar",
                symbol="$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_create_currency_raises_for_blank_name() -> None:
    currencies = _CurrencyOutputPortStub()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyDataValidationError):
        await use_case.create_currency(
            CreateCurrencyData(
                iso_code="USD",
                iso_numeric="840",
                name="   ",
                symbol="$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_get_currency_raises_when_currency_does_not_exist() -> None:
    currencies = _CurrencyOutputPortStub()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyNotFoundError):
        await use_case.get_currency(999)


@pytest.mark.anyio
async def test_update_currency_raises_when_currency_does_not_exist() -> None:
    currencies = _CurrencyOutputPortStub()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyNotFoundError):
        await use_case.update_currency(
            999,
            UpdateCurrencyData(
                iso_code="USD",
                iso_numeric="840",
                name="US Dollar",
                symbol="$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_update_currency_translates_iso_code_conflict_output_port_error() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    currencies.update_error = CurrencyISOCodeConflictOutputPortError()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyISOCodeConflictError):
        await use_case.update_currency(
            created.id,
            UpdateCurrencyData(
                iso_code="BRL",
                iso_numeric="986",
                name="Brazilian Real",
                symbol="R$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_update_currency_raises_for_blank_name() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyDataValidationError):
        await use_case.update_currency(
            created.id,
            UpdateCurrencyData(
                iso_code="BRL",
                iso_numeric="986",
                name="   ",
                symbol="R$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_delete_currency_soft_deletes_by_default() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    unit_of_work = _UnitOfWorkStub(currencies)
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    await use_case.delete_currency(created.id)

    assert created.id in currencies.deleted_currency_ids
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_list_currencies_returns_active_currencies() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    await currencies.create_currency(
        NewCurrency(
            iso_code="EUR",
            iso_numeric="978",
            name="Euro",
            symbol="EUR",
            decimal_places=2,
        ),
    )
    await currencies.soft_delete_currency(created.id)
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    page = await use_case.list_currencies(
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="created_at", direction=SortDirection.ASC),),
        ),
    )

    assert [currency.iso_code for currency in page.items] == ["EUR"]


@pytest.mark.anyio
async def test_get_currency_returns_existing_currency() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    result = await use_case.get_currency(created.id)

    assert result == created


@pytest.mark.anyio
async def test_update_currency_replaces_fields_and_commits() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    unit_of_work = _UnitOfWorkStub(currencies)
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    result = await use_case.update_currency(
        created.id,
        UpdateCurrencyData(
            iso_code=" brl ",
            iso_numeric="986 ",
            name=" Brazilian Real ",
            symbol=" R$ ",
            decimal_places=2,
        ),
    )

    assert result.iso_code == "BRL"
    assert result.iso_numeric == "986"
    assert result.name == "Brazilian Real"
    assert result.symbol == "R$"
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_update_currency_translates_output_port_not_found() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    currencies.update_error = CurrencyNotFoundOutputPortError()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyNotFoundError):
        await use_case.update_currency(
            created.id,
            UpdateCurrencyData(
                iso_code="BRL",
                iso_numeric="986",
                name="Brazilian Real",
                symbol="R$",
                decimal_places=2,
            ),
        )


@pytest.mark.anyio
async def test_delete_currency_hard_deletes_when_requested() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    await currencies.soft_delete_currency(created.id)
    unit_of_work = _UnitOfWorkStub(currencies)
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    await use_case.delete_currency(created.id, hard_delete=True)

    assert created.id not in currencies.currencies
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_delete_currency_translates_output_port_not_found() -> None:
    currencies = _CurrencyOutputPortStub()
    created = await currencies.create_currency(
        NewCurrency(
            iso_code="USD",
            iso_numeric="840",
            name="US Dollar",
            symbol="$",
            decimal_places=2,
        ),
    )
    currencies.delete_error = CurrencyNotFoundOutputPortError()
    use_case = CurrencyUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(currencies)))

    with pytest.raises(CurrencyNotFoundError):
        await use_case.delete_currency(created.id)


@pytest.mark.anyio
async def test_delete_currency_raises_when_currency_does_not_exist() -> None:
    use_case = CurrencyUseCase(
        _UnitOfWorkFactoryStub(_UnitOfWorkStub(_CurrencyOutputPortStub())),
    )

    with pytest.raises(CurrencyNotFoundError):
        await use_case.delete_currency(999)

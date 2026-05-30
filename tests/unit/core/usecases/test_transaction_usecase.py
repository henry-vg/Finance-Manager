from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.core.domain.currency import Currency
from src.core.domain.ledger_account import (
    LedgerAccount,
    LedgerAccountInstrumentKind,
    LedgerAccountType,
)
from src.core.domain.tag import Tag
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
    TransactionEntryCurrencyNotFoundError,
    TransactionEntryRequiresCreditCardLedgerAccountError,
    TransactionEntryStatementDatesMustBeProvidedTogetherError,
    TransactionEntryStatementDueDateMustBeAfterClosingDateError,
    TransactionEntryTagsMustBeUniqueError,
    TransactionLedgerAccountNotFoundError,
    TransactionMustBePendingError,
    TransactionMustHaveAtLeastTwoEntriesError,
    TransactionNotFoundError,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
    TransactionTagNotFoundError,
    TransactionWithEntries,
    UpdateTransactionData,
)
from src.core.ports.output.currency_output_port import CurrencyOutputPort
from src.core.ports.output.ledger_account_output_port import LedgerAccountOutputPort
from src.core.ports.output.tag_output_port import TagOutputPort
from src.core.ports.output.transaction_output_port import (
    TransactionNotFoundOutputPortError,
    TransactionOutputPort,
)
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.ports.output.user_output_port import UserOutputPort
from src.core.usecases.transaction_usecase import TransactionUseCase


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


def _build_currency(*, currency_id: int, iso_code: str) -> Currency:
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


def _build_transaction_data(
    *,
    expense_ledger_account_id: int = 1,
    credit_card_ledger_account_id: int = 2,
    food_tag_id: int = 10,
    travel_tag_id: int = 11,
    status: TransactionStatus = TransactionStatus.PENDING,
    expense_currency_id: int = 1,
    credit_card_currency_id: int = 1,
) -> CreateTransactionData:
    return CreateTransactionData(
        effective_at=_build_timestamp(11),
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


def _build_update_data(
    *,
    expense_ledger_account_id: int = 1,
    credit_card_ledger_account_id: int = 2,
    food_tag_id: int = 10,
    travel_tag_id: int = 11,
) -> UpdateTransactionData:
    create_data = _build_transaction_data(
        expense_ledger_account_id=expense_ledger_account_id,
        credit_card_ledger_account_id=credit_card_ledger_account_id,
        food_tag_id=food_tag_id,
        travel_tag_id=travel_tag_id,
    )
    return UpdateTransactionData(
        effective_at=create_data.effective_at,
        title=create_data.title,
        description=create_data.description,
        entries=create_data.entries,
    )


def _build_ledger_account(
    *,
    ledger_account_id: int,
    type: LedgerAccountType,
    instrument_kind: LedgerAccountInstrumentKind | None,
) -> LedgerAccount:
    return LedgerAccount(
        id=ledger_account_id,
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
        title=f"Ledger Account {ledger_account_id}",
        type=type,
        instrument_kind=instrument_kind,
    )


def _build_transaction_with_entries(
    *,
    transaction_id: int = 1,
    status: TransactionStatus = TransactionStatus.PENDING,
) -> TransactionWithEntries:
    return TransactionWithEntries(
        transaction=Transaction(
            id=transaction_id,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
            effective_at=_build_timestamp(11),
            title="Airline tickets",
            description="Family vacation purchase",
            status=status,
        ),
        entries=(
            EntryWithTags(
                entry=Entry(
                    id=100,
                    created_at=_build_timestamp(1),
                    updated_at=_build_timestamp(1),
                    transaction_id=transaction_id,
                    ledger_account_id=1,
                    amount=Decimal("1200.00"),
                    currency_id=1,
                    statement_closing_date=None,
                    statement_due_date=None,
                ),
                entry_tags=(EntryTag(entry_id=100, tag_id=10),),
            ),
            EntryWithTags(
                entry=Entry(
                    id=101,
                    created_at=_build_timestamp(1),
                    updated_at=_build_timestamp(1),
                    transaction_id=transaction_id,
                    ledger_account_id=2,
                    amount=Decimal("-1200.00"),
                    currency_id=1,
                    statement_closing_date=date(2026, 5, 31),
                    statement_due_date=date(2026, 6, 10),
                ),
                entry_tags=(),
            ),
        ),
    )


class _TransactionOutputPortStub(TransactionOutputPort):
    def __init__(self) -> None:
        self.transactions: dict[int, TransactionWithEntries] = {}
        self.created_transactions: list[NewTransaction] = []
        self.updated_transactions: list[tuple[int, TransactionChanges]] = []
        self.posted_transactions: list[int] = []
        self.voided_transactions: list[int] = []
        self.update_error: Exception | None = None
        self.post_error: Exception | None = None
        self.void_error: Exception | None = None
        self.next_id = 1

    async def get_transaction_by_id(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries | None:
        return self.transactions.get(transaction_id)

    async def create_transaction(
        self,
        new_transaction: NewTransaction,
    ) -> TransactionWithEntries:
        self.created_transactions.append(new_transaction)
        created_transaction = _build_transaction_with_entries(
            transaction_id=self.next_id,
            status=new_transaction.status,
        )
        self.transactions[self.next_id] = created_transaction
        self.next_id += 1
        return created_transaction

    async def update_transaction(
        self,
        transaction_id: int,
        changes: TransactionChanges,
    ) -> TransactionWithEntries:
        if self.update_error is not None:
            raise self.update_error

        current_transaction = self.transactions.get(transaction_id)

        if current_transaction is None:
            raise TransactionNotFoundOutputPortError()

        updated_transaction = _build_transaction_with_entries(
            transaction_id=transaction_id,
            status=current_transaction.transaction.status,
        )
        self.updated_transactions.append((transaction_id, changes))
        self.transactions[transaction_id] = updated_transaction
        return updated_transaction

    async def post_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        if self.post_error is not None:
            raise self.post_error

        if transaction_id not in self.transactions:
            raise TransactionNotFoundOutputPortError()

        transitioned_transaction = _build_transaction_with_entries(
            transaction_id=transaction_id,
            status=TransactionStatus.POSTED,
        )
        self.posted_transactions.append(transaction_id)
        self.transactions[transaction_id] = transitioned_transaction
        return transitioned_transaction

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        if self.void_error is not None:
            raise self.void_error

        if transaction_id not in self.transactions:
            raise TransactionNotFoundOutputPortError()

        transitioned_transaction = _build_transaction_with_entries(
            transaction_id=transaction_id,
            status=TransactionStatus.VOIDED,
        )
        self.voided_transactions.append(transaction_id)
        self.transactions[transaction_id] = transitioned_transaction
        return transitioned_transaction


class _CurrencyOutputPortStub(CurrencyOutputPort):
    def __init__(self) -> None:
        self.currencies_by_id = {
            1: _build_currency(currency_id=1, iso_code="BRL"),
            2: _build_currency(currency_id=2, iso_code="USD"),
        }
        self.queried_currency_ids: list[int] = []

    async def get_currency_by_id(self, currency_id: int) -> Currency | None:
        self.queried_currency_ids.append(currency_id)
        return self.currencies_by_id.get(currency_id)


class _LedgerAccountOutputPortStub(LedgerAccountOutputPort):
    def __init__(self) -> None:
        self.ledger_accounts: dict[int, LedgerAccount] = {}

    async def list_ledger_accounts(self, list_query):
        raise RuntimeError("list_ledger_accounts is unused in transaction tests")

    async def get_ledger_account_by_id(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        return self.ledger_accounts.get(ledger_account_id)

    async def get_ledger_account_by_id_including_deleted(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None:
        return self.ledger_accounts.get(ledger_account_id)

    async def create_ledger_account(self, new_ledger_account):
        raise RuntimeError("create_ledger_account is unused in transaction tests")

    async def update_ledger_account(self, ledger_account_id, changes):
        raise RuntimeError("update_ledger_account is unused in transaction tests")

    async def soft_delete_ledger_account(self, ledger_account_id):
        raise RuntimeError("soft_delete_ledger_account is unused in transaction tests")

    async def hard_delete_ledger_account(self, ledger_account_id):
        raise RuntimeError("hard_delete_ledger_account is unused in transaction tests")


class _TagOutputPortStub(TagOutputPort):
    def __init__(self) -> None:
        self.tags: dict[int, Tag] = {}

    async def list_tags(self, list_query):
        raise RuntimeError("list_tags is unused in transaction tests")

    async def get_tag_by_id(self, tag_id: int) -> Tag | None:
        return self.tags.get(tag_id)

    async def get_tag_by_id_including_deleted(self, tag_id: int) -> Tag | None:
        return self.tags.get(tag_id)

    async def create_tag(self, new_tag):
        raise RuntimeError("create_tag is unused in transaction tests")

    async def update_tag(self, tag_id, changes):
        raise RuntimeError("update_tag is unused in transaction tests")

    async def soft_delete_tag(self, tag_id):
        raise RuntimeError("soft_delete_tag is unused in transaction tests")

    async def hard_delete_tag(self, tag_id):
        raise RuntimeError("hard_delete_tag is unused in transaction tests")


class _UnitOfWorkStub(UnitOfWorkOutputPort):
    def __init__(
        self,
        *,
        transactions: _TransactionOutputPortStub,
        ledger_accounts: _LedgerAccountOutputPortStub,
        tags: _TagOutputPortStub,
        currencies: _CurrencyOutputPortStub | None = None,
    ) -> None:
        self._transactions = transactions
        self._ledger_accounts = ledger_accounts
        self._tags = tags
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
        return self._tags

    @property
    def transactions(self) -> TransactionOutputPort:
        return self._transactions

    @property
    def users(self) -> UserOutputPort:
        raise RuntimeError("users output port is unused in transaction tests")

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


def _build_tag(*, tag_id: int) -> Tag:
    return Tag(
        id=tag_id,
        title=f"Tag {tag_id}",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )


def _build_use_case() -> tuple[
    TransactionUseCase,
    _TransactionOutputPortStub,
    _LedgerAccountOutputPortStub,
    _TagOutputPortStub,
    _UnitOfWorkStub,
]:
    transactions = _TransactionOutputPortStub()
    ledger_accounts = _LedgerAccountOutputPortStub()
    ledger_accounts.ledger_accounts[1] = _build_ledger_account(
        ledger_account_id=1,
        type=LedgerAccountType.EXPENSE,
        instrument_kind=None,
    )
    ledger_accounts.ledger_accounts[2] = _build_ledger_account(
        ledger_account_id=2,
        type=LedgerAccountType.LIABILITY,
        instrument_kind=LedgerAccountInstrumentKind.CREDIT_CARD,
    )
    tags = _TagOutputPortStub()
    tags.tags[10] = _build_tag(tag_id=10)
    tags.tags[11] = _build_tag(tag_id=11)
    unit_of_work = _UnitOfWorkStub(
        transactions=transactions,
        ledger_accounts=ledger_accounts,
        tags=tags,
    )
    return (
        TransactionUseCase(_UnitOfWorkFactoryStub(unit_of_work)),
        transactions,
        ledger_accounts,
        tags,
        unit_of_work,
    )


@pytest.mark.anyio
async def test_create_transaction_returns_created_transaction_and_commits() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()

    result = await use_case.create_transaction(_build_transaction_data())

    assert result.transaction.id == 1
    assert transactions.created_transactions[0].status == TransactionStatus.PENDING
    assert transactions.created_transactions[0].entries[0].currency_id == 1
    assert len(transactions.created_transactions[0].entries) == 2
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_create_transaction_allows_posted_historical_transaction() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()

    result = await use_case.create_transaction(
        _build_transaction_data(status=TransactionStatus.POSTED),
    )

    assert transactions.created_transactions[0].status == TransactionStatus.POSTED
    assert result.transaction.status == TransactionStatus.POSTED
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_create_transaction_allows_voided_historical_transaction() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()

    result = await use_case.create_transaction(
        _build_transaction_data(status=TransactionStatus.VOIDED),
    )

    assert transactions.created_transactions[0].status == TransactionStatus.VOIDED
    assert result.transaction.status == TransactionStatus.VOIDED
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_create_transaction_queries_entry_currencies_by_id() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()

    await use_case.create_transaction(
        _build_transaction_data(
            expense_currency_id=1,
            credit_card_currency_id=2,
        ),
    )

    assert transactions.created_transactions[0].entries[0].currency_id == 1
    assert set(unit_of_work.currencies.queried_currency_ids) == {1, 2}


@pytest.mark.anyio
async def test_create_transaction_requires_at_least_two_entries() -> None:
    use_case, _, _, _, unit_of_work = _build_use_case()
    data = _build_transaction_data()
    single_entry_data = CreateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        status=data.status,
        entries=(data.entries[0],),
    )

    with pytest.raises(TransactionMustHaveAtLeastTwoEntriesError):
        await use_case.create_transaction(single_entry_data)

    assert unit_of_work.committed is False


@pytest.mark.anyio
async def test_create_transaction_requires_balanced_entries() -> None:
    use_case, _, _, _, unit_of_work = _build_use_case()
    data = _build_transaction_data()
    unbalanced_data = CreateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        status=data.status,
        entries=(
            data.entries[0],
            NewEntry(
                ledger_account_id=data.entries[1].ledger_account_id,
                amount=Decimal("-1199.99"),
                currency_id=data.entries[1].currency_id,
                statement_closing_date=data.entries[1].statement_closing_date,
                statement_due_date=data.entries[1].statement_due_date,
            ),
        ),
    )

    with pytest.raises(TransactionEntriesMustBalanceError):
        await use_case.create_transaction(unbalanced_data)

    assert unit_of_work.committed is False


@pytest.mark.anyio
async def test_create_transaction_requires_existing_ledger_accounts() -> None:
    use_case, _, ledger_accounts, _, _ = _build_use_case()
    ledger_accounts.ledger_accounts.pop(2)

    with pytest.raises(TransactionLedgerAccountNotFoundError):
        await use_case.create_transaction(_build_transaction_data())


@pytest.mark.anyio
async def test_create_transaction_requires_existing_entry_currency() -> None:
    use_case, _, _, _, _ = _build_use_case()

    with pytest.raises(TransactionEntryCurrencyNotFoundError):
        await use_case.create_transaction(
            _build_transaction_data(credit_card_currency_id=999),
        )


@pytest.mark.anyio
async def test_create_transaction_requires_existing_tags() -> None:
    use_case, _, _, tags, _ = _build_use_case()
    tags.tags.pop(11)

    with pytest.raises(TransactionTagNotFoundError):
        await use_case.create_transaction(_build_transaction_data())


@pytest.mark.anyio
async def test_create_transaction_rejects_duplicate_tags_in_the_same_entry() -> None:
    use_case, _, _, _, _ = _build_use_case()
    data = _build_transaction_data()
    duplicated_tags_data = CreateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        status=data.status,
        entries=(
            NewEntry(
                ledger_account_id=data.entries[0].ledger_account_id,
                amount=data.entries[0].amount,
                currency_id=data.entries[0].currency_id,
                statement_closing_date=data.entries[0].statement_closing_date,
                statement_due_date=data.entries[0].statement_due_date,
                entry_tags=(
                    NewEntryTag(tag_id=10),
                    NewEntryTag(tag_id=10),
                ),
            ),
            data.entries[1],
        ),
    )

    with pytest.raises(TransactionEntryTagsMustBeUniqueError):
        await use_case.create_transaction(duplicated_tags_data)


@pytest.mark.anyio
async def test_create_transaction_requires_statement_dates_together() -> None:
    use_case, _, _, _, _ = _build_use_case()
    data = _build_transaction_data()
    invalid_dates_data = CreateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        status=data.status,
        entries=(
            data.entries[0],
            NewEntry(
                ledger_account_id=data.entries[1].ledger_account_id,
                amount=data.entries[1].amount,
                currency_id=data.entries[1].currency_id,
                statement_closing_date=data.entries[1].statement_closing_date,
                statement_due_date=None,
            ),
        ),
    )

    with pytest.raises(TransactionEntryStatementDatesMustBeProvidedTogetherError):
        await use_case.create_transaction(invalid_dates_data)


@pytest.mark.anyio
async def test_create_transaction_requires_credit_card_for_statement_dates() -> None:
    use_case, _, _, _, _ = _build_use_case()
    data = _build_transaction_data(credit_card_ledger_account_id=1)

    with pytest.raises(TransactionEntryRequiresCreditCardLedgerAccountError):
        await use_case.create_transaction(data)


@pytest.mark.anyio
async def test_create_transaction_requires_due_date_after_closing_date() -> None:
    use_case, _, _, _, _ = _build_use_case()
    data = _build_transaction_data()
    invalid_order_data = CreateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        status=data.status,
        entries=(
            data.entries[0],
            NewEntry(
                ledger_account_id=data.entries[1].ledger_account_id,
                amount=data.entries[1].amount,
                currency_id=data.entries[1].currency_id,
                statement_closing_date=date(2026, 5, 31),
                statement_due_date=date(2026, 5, 31),
            ),
        ),
    )

    with pytest.raises(TransactionEntryStatementDueDateMustBeAfterClosingDateError):
        await use_case.create_transaction(invalid_order_data)


@pytest.mark.anyio
async def test_get_transaction_raises_when_transaction_does_not_exist() -> None:
    use_case, _, _, _, _ = _build_use_case()

    with pytest.raises(TransactionNotFoundError):
        await use_case.get_transaction(999)


@pytest.mark.anyio
async def test_update_transaction_requires_existing_transaction() -> None:
    use_case, _, _, _, _ = _build_use_case()

    with pytest.raises(TransactionNotFoundError):
        await use_case.update_transaction(999, _build_update_data())


@pytest.mark.anyio
async def test_update_transaction_requires_current_transaction_to_be_pending() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(
        transaction_id=1,
        status=TransactionStatus.POSTED,
    )

    with pytest.raises(TransactionMustBePendingError):
        await use_case.update_transaction(1, _build_update_data())


@pytest.mark.anyio
async def test_update_transaction_requires_at_least_two_entries() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    data = _build_update_data()
    single_entry_data = UpdateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        entries=(data.entries[0],),
    )

    with pytest.raises(TransactionMustHaveAtLeastTwoEntriesError):
        await use_case.update_transaction(1, single_entry_data)

    assert unit_of_work.committed is False


@pytest.mark.anyio
async def test_update_transaction_requires_balanced_entries() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    data = _build_update_data()
    unbalanced_data = UpdateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        entries=(
            data.entries[0],
            NewEntry(
                ledger_account_id=data.entries[1].ledger_account_id,
                amount=Decimal("-1199.99"),
                currency_id=data.entries[1].currency_id,
                statement_closing_date=data.entries[1].statement_closing_date,
                statement_due_date=data.entries[1].statement_due_date,
            ),
        ),
    )

    with pytest.raises(TransactionEntriesMustBalanceError):
        await use_case.update_transaction(1, unbalanced_data)

    assert unit_of_work.committed is False


@pytest.mark.anyio
async def test_update_transaction_rejects_duplicate_tags_in_the_same_entry() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    data = _build_update_data()
    duplicated_tags_data = UpdateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        entries=(
            NewEntry(
                ledger_account_id=data.entries[0].ledger_account_id,
                amount=data.entries[0].amount,
                currency_id=data.entries[0].currency_id,
                statement_closing_date=data.entries[0].statement_closing_date,
                statement_due_date=data.entries[0].statement_due_date,
                entry_tags=(
                    NewEntryTag(tag_id=10),
                    NewEntryTag(tag_id=10),
                ),
            ),
            data.entries[1],
        ),
    )

    with pytest.raises(TransactionEntryTagsMustBeUniqueError):
        await use_case.update_transaction(1, duplicated_tags_data)


@pytest.mark.anyio
async def test_update_transaction_requires_statement_dates_together() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    data = _build_update_data()
    invalid_dates_data = UpdateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        entries=(
            data.entries[0],
            NewEntry(
                ledger_account_id=data.entries[1].ledger_account_id,
                amount=data.entries[1].amount,
                currency_id=data.entries[1].currency_id,
                statement_closing_date=data.entries[1].statement_closing_date,
                statement_due_date=None,
            ),
        ),
    )

    with pytest.raises(TransactionEntryStatementDatesMustBeProvidedTogetherError):
        await use_case.update_transaction(1, invalid_dates_data)


@pytest.mark.anyio
async def test_update_transaction_requires_credit_card_for_statement_dates() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    data = _build_update_data(credit_card_ledger_account_id=1)

    with pytest.raises(TransactionEntryRequiresCreditCardLedgerAccountError):
        await use_case.update_transaction(1, data)


@pytest.mark.anyio
async def test_update_transaction_requires_due_date_after_closing_date() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    data = _build_update_data()
    invalid_order_data = UpdateTransactionData(
        effective_at=data.effective_at,
        title=data.title,
        description=data.description,
        entries=(
            data.entries[0],
            NewEntry(
                ledger_account_id=data.entries[1].ledger_account_id,
                amount=data.entries[1].amount,
                currency_id=data.entries[1].currency_id,
                statement_closing_date=date(2026, 5, 31),
                statement_due_date=date(2026, 5, 31),
            ),
        ),
    )

    with pytest.raises(TransactionEntryStatementDueDateMustBeAfterClosingDateError):
        await use_case.update_transaction(1, invalid_order_data)


@pytest.mark.anyio
async def test_update_transaction_translates_not_found_output_error() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    transactions.update_error = TransactionNotFoundOutputPortError()

    with pytest.raises(TransactionNotFoundError):
        await use_case.update_transaction(1, _build_update_data())


@pytest.mark.anyio
async def test_update_transaction_returns_updated_transaction_and_commits() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)

    result = await use_case.update_transaction(1, _build_update_data())

    assert result.transaction.id == 1
    assert result.transaction.status == TransactionStatus.PENDING
    assert transactions.updated_transactions[0][0] == 1
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_post_transaction_requires_existing_transaction() -> None:
    use_case, _, _, _, _ = _build_use_case()

    with pytest.raises(TransactionNotFoundError):
        await use_case.post_transaction(999)


@pytest.mark.anyio
async def test_post_transaction_rejects_invalid_transition() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(
        transaction_id=1,
        status=TransactionStatus.POSTED,
    )

    with pytest.raises(TransactionStatusTransitionNotAllowedError):
        await use_case.post_transaction(1)


@pytest.mark.anyio
async def test_post_transaction_translates_not_found_output_error() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)
    transactions.post_error = TransactionNotFoundOutputPortError()

    with pytest.raises(TransactionNotFoundError):
        await use_case.post_transaction(1)


@pytest.mark.anyio
async def test_post_transaction_returns_transitioned_transaction_and_commits() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)

    result = await use_case.post_transaction(1)

    assert result.transaction.status == TransactionStatus.POSTED
    assert transactions.posted_transactions == [1]
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_void_transaction_requires_existing_transaction() -> None:
    use_case, _, _, _, _ = _build_use_case()

    with pytest.raises(TransactionNotFoundError):
        await use_case.void_transaction(999)


@pytest.mark.anyio
async def test_void_transaction_rejects_terminal_voided_transaction() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(
        transaction_id=1,
        status=TransactionStatus.VOIDED,
    )

    with pytest.raises(TransactionStatusTransitionNotAllowedError):
        await use_case.void_transaction(1)


@pytest.mark.anyio
async def test_void_transaction_returns_transitioned_transaction_and_commits() -> None:
    use_case, transactions, _, _, unit_of_work = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)

    result = await use_case.void_transaction(1)

    assert result.transaction.status == TransactionStatus.VOIDED
    assert transactions.voided_transactions == [1]
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_void_transaction_rejects_posted_transaction() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(
        transaction_id=1,
        status=TransactionStatus.POSTED,
    )

    with pytest.raises(TransactionStatusTransitionNotAllowedError):
        await use_case.void_transaction(1)


@pytest.mark.anyio
async def test_get_transaction_returns_existing_transaction() -> None:
    use_case, transactions, _, _, _ = _build_use_case()
    transactions.transactions[1] = _build_transaction_with_entries(transaction_id=1)

    result = await use_case.get_transaction(1)

    assert result.transaction.id == 1
    assert len(result.entries) == 2

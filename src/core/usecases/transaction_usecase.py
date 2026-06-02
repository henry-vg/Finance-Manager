from dataclasses import replace
from decimal import Decimal

from src.core.domain.currency import DOLLAR_ISO_CODE, Currency
from src.core.domain.ledger_account import (
    LedgerAccount,
    LedgerAccountInstrumentKind,
    LedgerAccountType,
)
from src.core.domain.transaction import (
    CreateTransactionData,
    EntryWithTags,
    NewEntry,
    NewEntryTag,
    NewTransaction,
    Transaction,
    TransactionChanges,
    TransactionEntriesMustBalanceError,
    TransactionEntryCurrencyNotFoundError,
    TransactionEntryExchangeRateUnavailableError,
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
    can_transition_transaction_status,
)
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.ports.output.exchange_rate_output_port import ExchangeRateOutputPort
from src.core.ports.output.transaction_output_port import (
    TransactionNotFoundOutputPortError,
)
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.shared import ListQuery, Page


class TransactionUseCase(TransactionInputPort):
    _DOLLAR_QUANTIZER = Decimal("0.01")

    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
        exchange_rate_output_port: ExchangeRateOutputPort,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory
        self._exchange_rate_output_port = exchange_rate_output_port

    @classmethod
    def _to_dollar_amount(
        cls,
        *,
        amount: Decimal,
        rate_to_dollars: Decimal,
    ) -> Decimal:
        return (amount * rate_to_dollars).quantize(cls._DOLLAR_QUANTIZER)

    @staticmethod
    def _to_new_transaction(
        data: CreateTransactionData,
        entries: tuple[NewEntry, ...],
    ) -> NewTransaction:
        return NewTransaction(
            effective_at=data.effective_at,
            title=data.title,
            description=data.description,
            status=data.status,
            entries=entries,
        )

    @staticmethod
    def _to_transaction_changes(
        data: UpdateTransactionData,
        entries: tuple[NewEntry, ...],
    ) -> TransactionChanges:
        return TransactionChanges(
            effective_at=data.effective_at,
            title=data.title,
            description=data.description,
            entries=entries,
        )

    @staticmethod
    def _to_entry_for_posting(
        entry_with_tags: EntryWithTags,
    ) -> NewEntry:
        entry = entry_with_tags.entry
        planned_rate_to_dollars = entry.planned_exchange_rate_to_dollars

        return NewEntry(
            ledger_account_id=entry.ledger_account_id,
            amount=(
                entry.amount_in_dollars / planned_rate_to_dollars
                if planned_rate_to_dollars != Decimal("0")
                else Decimal("0")
            ),
            amount_in_dollars=entry.amount_in_dollars,
            currency_id=entry.currency_id,
            statement_closing_date=entry.statement_closing_date,
            statement_due_date=entry.statement_due_date,
            entry_tags=tuple(
                NewEntryTag(tag_id=entry_tag.tag_id)
                for entry_tag in entry_with_tags.entry_tags
            ),
            planned_exchange_rate_to_dollars=entry.planned_exchange_rate_to_dollars,
            posting_exchange_rate_to_dollars=entry.posting_exchange_rate_to_dollars,
        )

    @staticmethod
    def _ensure_entries_balance_in_dollars(
        entries: tuple[NewEntry, ...],
    ) -> None:
        total = sum(
            (entry.amount_in_dollars for entry in entries),
            start=Decimal("0"),
        )

        if total != Decimal("0"):
            raise TransactionEntriesMustBalanceError()

    async def _transition_transaction_status(
        self,
        *,
        transaction_id: int,
        new_status: TransactionStatus,
    ) -> TransactionWithEntries:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_transaction = await unit_of_work.transactions.get_transaction_by_id(
                transaction_id=transaction_id,
            )

            if current_transaction is None:
                raise TransactionNotFoundError()

            if not can_transition_transaction_status(
                current_status=current_transaction.transaction.status,
                new_status=new_status,
            ):
                raise TransactionStatusTransitionNotAllowedError()

            try:
                if new_status == TransactionStatus.POSTED:
                    posting_entries = tuple(
                        self._to_entry_for_posting(entry_with_tags)
                        for entry_with_tags in current_transaction.entries
                    )
                    currencies = await self._load_currencies(
                        unit_of_work=unit_of_work,
                        entries=posting_entries,
                    )
                    posted_entries = await self._apply_posting_exchange_rates(
                        entries=posting_entries,
                        currencies_by_id=currencies,
                    )
                    self._ensure_entries_balance_in_dollars(posted_entries)
                    transitioned_transaction = (
                        await unit_of_work.transactions.post_transaction(
                            transaction_id=transaction_id,
                            entries=posted_entries,
                        )
                    )
                else:
                    transitioned_transaction = (
                        await unit_of_work.transactions.void_transaction(
                            transaction_id=transaction_id,
                        )
                    )
            except TransactionNotFoundOutputPortError as exc:
                raise TransactionNotFoundError() from exc

            await unit_of_work.commit()

            return transitioned_transaction

    async def _load_currencies(
        self,
        *,
        unit_of_work: UnitOfWorkOutputPort,
        entries: tuple[NewEntry, ...],
    ) -> dict[int, Currency]:
        currencies: dict[int, Currency] = {}

        for currency_id in {entry.currency_id for entry in entries}:
            currency = await unit_of_work.currencies.get_currency_by_id(
                currency_id=currency_id,
            )

            if currency is None:
                raise TransactionEntryCurrencyNotFoundError()

            currencies[currency_id] = currency

        return currencies

    async def _get_exchange_rate_to_dollars(
        self,
        *,
        currency: Currency,
    ) -> Decimal:
        if currency.iso_code == DOLLAR_ISO_CODE:
            return Decimal("1")

        try:
            quote = await self._exchange_rate_output_port.get_exchange_rate_to_dollars(
                currency.iso_code,
            )
        except NotImplementedError as exc:
            raise TransactionEntryExchangeRateUnavailableError() from exc

        return quote.rate_to_dollars

    async def _apply_planned_exchange_rates(
        self,
        *,
        entries: tuple[NewEntry, ...],
        currencies_by_id: dict[int, Currency],
    ) -> tuple[NewEntry, ...]:
        enriched_entries: list[NewEntry] = []

        for entry in entries:
            rate_to_dollars = await self._get_exchange_rate_to_dollars(
                currency=currencies_by_id[entry.currency_id],
            )
            enriched_entries.append(
                replace(
                    entry,
                    amount_in_dollars=self._to_dollar_amount(
                        amount=entry.amount,
                        rate_to_dollars=rate_to_dollars,
                    ),
                    planned_exchange_rate_to_dollars=rate_to_dollars,
                    posting_exchange_rate_to_dollars=None,
                ),
            )

        return tuple(enriched_entries)

    async def _apply_posting_exchange_rates(
        self,
        *,
        entries: tuple[NewEntry, ...],
        currencies_by_id: dict[int, Currency],
    ) -> tuple[NewEntry, ...]:
        enriched_entries: list[NewEntry] = []

        for entry in entries:
            rate_to_dollars = await self._get_exchange_rate_to_dollars(
                currency=currencies_by_id[entry.currency_id],
            )
            enriched_entries.append(
                replace(
                    entry,
                    amount_in_dollars=self._to_dollar_amount(
                        amount=entry.amount,
                        rate_to_dollars=rate_to_dollars,
                    ),
                    posting_exchange_rate_to_dollars=rate_to_dollars,
                ),
            )

        return tuple(enriched_entries)

    async def _load_ledger_accounts(
        self,
        *,
        unit_of_work: UnitOfWorkOutputPort,
        entries: tuple[NewEntry, ...],
    ) -> dict[int, LedgerAccount]:
        ledger_accounts: dict[int, LedgerAccount] = {}

        for ledger_account_id in {entry.ledger_account_id for entry in entries}:
            ledger_account = (
                await unit_of_work.ledger_accounts.get_ledger_account_by_id(
                    ledger_account_id=ledger_account_id,
                )
            )

            if ledger_account is None:
                raise TransactionLedgerAccountNotFoundError()

            ledger_accounts[ledger_account_id] = ledger_account

        return ledger_accounts

    async def _ensure_tags_exist(
        self,
        *,
        unit_of_work: UnitOfWorkOutputPort,
        entries: tuple[NewEntry, ...],
    ) -> None:
        tag_ids = {
            entry_tag.tag_id for entry in entries for entry_tag in entry.entry_tags
        }

        for tag_id in tag_ids:
            tag = await unit_of_work.tags.get_tag_by_id(tag_id=tag_id)

            if tag is None:
                raise TransactionTagNotFoundError()

    async def _validate_entries(
        self,
        *,
        unit_of_work: UnitOfWorkOutputPort,
        entries: tuple[NewEntry, ...],
    ) -> dict[int, Currency]:
        if len(entries) < 2:
            raise TransactionMustHaveAtLeastTwoEntriesError()

        ledger_accounts = await self._load_ledger_accounts(
            unit_of_work=unit_of_work,
            entries=entries,
        )
        currencies = await self._load_currencies(
            unit_of_work=unit_of_work,
            entries=entries,
        )
        await self._ensure_tags_exist(
            unit_of_work=unit_of_work,
            entries=entries,
        )

        for entry in entries:
            if len({entry_tag.tag_id for entry_tag in entry.entry_tags}) != len(
                entry.entry_tags,
            ):
                raise TransactionEntryTagsMustBeUniqueError()

            ledger_account = ledger_accounts[entry.ledger_account_id]

            closing_date = entry.statement_closing_date
            due_date = entry.statement_due_date

            if (closing_date is None) != (due_date is None):
                raise TransactionEntryStatementDatesMustBeProvidedTogetherError()

            if closing_date is None or due_date is None:
                continue

            if not (
                ledger_account.type == LedgerAccountType.LIABILITY
                and ledger_account.instrument_kind
                == LedgerAccountInstrumentKind.CREDIT_CARD
            ):
                raise TransactionEntryRequiresCreditCardLedgerAccountError()

            if due_date <= closing_date:
                raise TransactionEntryStatementDueDateMustBeAfterClosingDateError()

        return currencies

    async def list_transactions(
        self,
        list_query: ListQuery,
    ) -> Page[Transaction]:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            return await unit_of_work.transactions.list_transactions(
                list_query=list_query,
            )

    async def get_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            transaction = await unit_of_work.transactions.get_transaction_by_id(
                transaction_id=transaction_id,
            )

            if transaction is None:
                raise TransactionNotFoundError()

            return transaction

    async def create_transaction(
        self,
        data: CreateTransactionData,
    ) -> TransactionWithEntries:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            currencies = await self._validate_entries(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )
            planned_entries = await self._apply_planned_exchange_rates(
                entries=data.entries,
                currencies_by_id=currencies,
            )
            self._ensure_entries_balance_in_dollars(planned_entries)

            entries_to_persist = planned_entries

            if data.status == TransactionStatus.POSTED:
                entries_to_persist = await self._apply_posting_exchange_rates(
                    entries=planned_entries,
                    currencies_by_id=currencies,
                )
                self._ensure_entries_balance_in_dollars(entries_to_persist)

            new_transaction = self._to_new_transaction(
                data,
                entries_to_persist,
            )

            created_transaction = await unit_of_work.transactions.create_transaction(
                new_transaction=new_transaction,
            )

            await unit_of_work.commit()

            return created_transaction

    async def update_transaction(
        self,
        transaction_id: int,
        data: UpdateTransactionData,
    ) -> TransactionWithEntries:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_transaction = await unit_of_work.transactions.get_transaction_by_id(
                transaction_id=transaction_id,
            )

            if current_transaction is None:
                raise TransactionNotFoundError()

            if current_transaction.transaction.status != TransactionStatus.PENDING:
                raise TransactionMustBePendingError()

            currencies = await self._validate_entries(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )
            planned_entries = await self._apply_planned_exchange_rates(
                entries=data.entries,
                currencies_by_id=currencies,
            )
            self._ensure_entries_balance_in_dollars(planned_entries)
            changes = self._to_transaction_changes(
                data,
                planned_entries,
            )

            try:
                updated_transaction = (
                    await unit_of_work.transactions.update_transaction(
                        transaction_id=transaction_id,
                        changes=changes,
                    )
                )
            except TransactionNotFoundOutputPortError as exc:
                raise TransactionNotFoundError() from exc

            await unit_of_work.commit()

            return updated_transaction

    async def post_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        return await self._transition_transaction_status(
            transaction_id=transaction_id,
            new_status=TransactionStatus.POSTED,
        )

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        return await self._transition_transaction_status(
            transaction_id=transaction_id,
            new_status=TransactionStatus.VOIDED,
        )

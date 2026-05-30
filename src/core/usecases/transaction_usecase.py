from decimal import Decimal

from src.core.domain.ledger_account import (
    LedgerAccount,
    LedgerAccountInstrumentKind,
    LedgerAccountType,
)
from src.core.domain.transaction import (
    CreateTransactionData,
    NewEntry,
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
    can_transition_transaction_status,
)
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.ports.output.transaction_output_port import (
    TransactionNotFoundOutputPortError,
)
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.shared import ListQuery, Page


class TransactionUseCase(TransactionInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory

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
                    transitioned_transaction = (
                        await unit_of_work.transactions.post_transaction(
                            transaction_id=transaction_id,
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

    async def _ensure_entry_currencies_exist(
        self,
        *,
        unit_of_work: UnitOfWorkOutputPort,
        entries: tuple[NewEntry, ...],
    ) -> None:
        for currency_id in {entry.currency_id for entry in entries}:
            currency = await unit_of_work.currencies.get_currency_by_id(
                currency_id=currency_id,
            )

            if currency is None:
                raise TransactionEntryCurrencyNotFoundError()

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
            if len(data.entries) < 2:
                raise TransactionMustHaveAtLeastTwoEntriesError()

            if sum(
                (entry.amount for entry in data.entries),
                start=Decimal("0"),
            ) != Decimal(
                "0",
            ):
                raise TransactionEntriesMustBalanceError()

            ledger_accounts = await self._load_ledger_accounts(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )
            await self._ensure_tags_exist(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )
            await self._ensure_entry_currencies_exist(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )

            for entry in data.entries:
                if len({entry_tag.tag_id for entry_tag in entry.entry_tags}) != len(
                    entry.entry_tags,
                ):
                    raise TransactionEntryTagsMustBeUniqueError()

                ledger_account = ledger_accounts[entry.ledger_account_id]

                has_closing_date = entry.statement_closing_date is not None
                has_due_date = entry.statement_due_date is not None

                if has_closing_date != has_due_date:
                    raise TransactionEntryStatementDatesMustBeProvidedTogetherError()

                if not has_closing_date:
                    continue

                if not (
                    ledger_account.type == LedgerAccountType.LIABILITY
                    and ledger_account.instrument_kind
                    == LedgerAccountInstrumentKind.CREDIT_CARD
                ):
                    raise TransactionEntryRequiresCreditCardLedgerAccountError()

                if entry.statement_due_date <= entry.statement_closing_date:
                    raise TransactionEntryStatementDueDateMustBeAfterClosingDateError()

            created_transaction = await unit_of_work.transactions.create_transaction(
                new_transaction=NewTransaction(
                    effective_at=data.effective_at,
                    title=data.title,
                    description=data.description,
                    status=data.status,
                    entries=data.entries,
                ),
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

            if len(data.entries) < 2:
                raise TransactionMustHaveAtLeastTwoEntriesError()

            if sum(
                (entry.amount for entry in data.entries),
                start=Decimal("0"),
            ) != Decimal(
                "0",
            ):
                raise TransactionEntriesMustBalanceError()

            ledger_accounts = await self._load_ledger_accounts(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )
            await self._ensure_tags_exist(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )
            await self._ensure_entry_currencies_exist(
                unit_of_work=unit_of_work,
                entries=data.entries,
            )

            for entry in data.entries:
                if len({entry_tag.tag_id for entry_tag in entry.entry_tags}) != len(
                    entry.entry_tags,
                ):
                    raise TransactionEntryTagsMustBeUniqueError()

                ledger_account = ledger_accounts[entry.ledger_account_id]

                has_closing_date = entry.statement_closing_date is not None
                has_due_date = entry.statement_due_date is not None

                if has_closing_date != has_due_date:
                    raise TransactionEntryStatementDatesMustBeProvidedTogetherError()

                if not has_closing_date:
                    continue

                if not (
                    ledger_account.type == LedgerAccountType.LIABILITY
                    and ledger_account.instrument_kind
                    == LedgerAccountInstrumentKind.CREDIT_CARD
                ):
                    raise TransactionEntryRequiresCreditCardLedgerAccountError()

                if entry.statement_due_date <= entry.statement_closing_date:
                    raise TransactionEntryStatementDueDateMustBeAfterClosingDateError()

            try:
                updated_transaction = (
                    await unit_of_work.transactions.update_transaction(
                        transaction_id=transaction_id,
                        changes=TransactionChanges(
                            effective_at=data.effective_at,
                            title=data.title,
                            description=data.description,
                            entries=data.entries,
                        ),
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

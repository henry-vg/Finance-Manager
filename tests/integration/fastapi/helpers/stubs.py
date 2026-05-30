from datetime import UTC, datetime

from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    CurrencyNotFoundError,
    UpdateCurrencyData,
)
from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    LedgerAccountNotFoundError,
    UpdateLedgerAccountData,
)
from src.core.domain.tag import CreateTagData, Tag, TagNotFoundError, UpdateTagData
from src.core.domain.transaction import (
    CreateTransactionData,
    Entry,
    EntryTag,
    EntryWithTags,
    NewEntry,
    Transaction,
    TransactionMustBePendingError,
    TransactionNotFoundError,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
    TransactionWithEntries,
    UpdateTransactionData,
)
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.shared import ListQuery, Page, SortDirection, SortTerm


def build_timestamp(
    day: int,
    *,
    year: int = 2026,
    month: int = 5,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        tzinfo=UTC,
    )


class CurrencyInputPortStub(CurrencyInputPort):
    def __init__(self) -> None:
        self.currencies_by_id: dict[int, Currency] = {}
        self.soft_deleted_currency_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_currency_queries: list[ListQuery] = []
        self._next_currency_id = 1

    async def list_currencies(
        self,
        list_query: ListQuery,
    ) -> Page[Currency]:
        self.list_currency_queries.append(list_query)
        active_currencies = [
            currency
            for currency_id, currency in self.currencies_by_id.items()
            if currency_id not in self.soft_deleted_currency_ids
        ]
        active_currencies.sort(key=lambda currency: currency.id)

        return Page[Currency](
            items=active_currencies[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_currencies),
        )

    async def get_currency(
        self,
        currency_id: int,
    ) -> Currency:
        if (
            currency_id in self.soft_deleted_currency_ids
            or currency_id not in self.currencies_by_id
        ):
            raise CurrencyNotFoundError()

        return self.currencies_by_id[currency_id]

    async def create_currency(
        self,
        data: CreateCurrencyData,
    ) -> Currency:
        currency = Currency(
            id=self._next_currency_id,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=build_timestamp(1),
            updated_at=build_timestamp(1),
        )
        self.currencies_by_id[currency.id] = currency
        self._next_currency_id += 1
        return currency

    async def update_currency(
        self,
        currency_id: int,
        data: UpdateCurrencyData,
    ) -> Currency:
        current = await self.get_currency(currency_id)
        updated = Currency(
            id=current.id,
            iso_code=data.iso_code,
            iso_numeric=data.iso_numeric,
            name=data.name,
            symbol=data.symbol,
            decimal_places=data.decimal_places,
            created_at=current.created_at,
            updated_at=build_timestamp(2),
        )
        self.currencies_by_id[currency_id] = updated
        return updated

    async def delete_currency(
        self,
        currency_id: int,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((currency_id, hard_delete))
        if currency_id in self.soft_deleted_currency_ids:
            if hard_delete:
                self.soft_deleted_currency_ids.remove(currency_id)
                self.currencies_by_id.pop(currency_id, None)
                return
            raise CurrencyNotFoundError()
        if currency_id not in self.currencies_by_id:
            raise CurrencyNotFoundError()
        if hard_delete:
            self.currencies_by_id.pop(currency_id, None)
            return
        self.soft_deleted_currency_ids.add(currency_id)


class ReadyHealthzInputPortStub(HealthzInputPort):
    async def get_healthz_liveness(self) -> HealthzLiveness:
        return HealthzLiveness(status=HealthzStatus.OK)

    async def get_healthz_readiness(self) -> HealthzReadiness:
        return HealthzReadiness(
            status=HealthzStatus.OK,
            dependencies=HealthzReadinessDependencies(
                api=HealthzStatus.OK,
                database=HealthzStatus.OK,
            ),
        )


class HealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.OK


class UnhealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.NOT_OK


class LedgerAccountInputPortStub(LedgerAccountInputPort):
    def __init__(self) -> None:
        self.ledger_accounts_by_id: dict[int, LedgerAccount] = {}
        self.soft_deleted_ledger_account_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_ledger_account_queries: list[ListQuery] = []
        self._next_ledger_account_id = 1

    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]:
        self.list_ledger_account_queries.append(list_query)
        active_ledger_accounts = [
            ledger_account
            for ledger_account_id, ledger_account in self.ledger_accounts_by_id.items()
            if ledger_account_id not in self.soft_deleted_ledger_account_ids
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

    async def get_ledger_account(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount:
        if (
            ledger_account_id in self.soft_deleted_ledger_account_ids
            or ledger_account_id not in self.ledger_accounts_by_id
        ):
            raise LedgerAccountNotFoundError()
        return self.ledger_accounts_by_id[ledger_account_id]

    async def create_ledger_account(
        self,
        data: CreateLedgerAccountData,
    ) -> LedgerAccount:
        ledger_account = LedgerAccount(
            id=self._next_ledger_account_id,
            title=data.title,
            type=data.type,
            instrument_kind=data.instrument_kind,
            created_at=build_timestamp(1),
            updated_at=build_timestamp(1),
        )
        self.ledger_accounts_by_id[ledger_account.id] = ledger_account
        self._next_ledger_account_id += 1
        return ledger_account

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount:
        current = await self.get_ledger_account(ledger_account_id)
        updated = LedgerAccount(
            id=current.id,
            title=data.title,
            type=data.type,
            instrument_kind=data.instrument_kind,
            created_at=current.created_at,
            updated_at=build_timestamp(2),
        )
        self.ledger_accounts_by_id[ledger_account_id] = updated
        return updated

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((ledger_account_id, hard_delete))
        if ledger_account_id in self.soft_deleted_ledger_account_ids:
            if hard_delete:
                self.soft_deleted_ledger_account_ids.remove(ledger_account_id)
                self.ledger_accounts_by_id.pop(ledger_account_id, None)
                return
            raise LedgerAccountNotFoundError()
        if ledger_account_id not in self.ledger_accounts_by_id:
            raise LedgerAccountNotFoundError()
        if hard_delete:
            self.ledger_accounts_by_id.pop(ledger_account_id, None)
            return
        self.soft_deleted_ledger_account_ids.add(ledger_account_id)


class TagInputPortStub(TagInputPort):
    def __init__(self) -> None:
        self.tags_by_id: dict[int, Tag] = {}
        self.soft_deleted_tag_ids: set[int] = set()
        self.delete_calls: list[tuple[int, bool]] = []
        self.list_tag_queries: list[ListQuery] = []
        self._next_tag_id = 1

    async def list_tags(self, list_query: ListQuery) -> Page[Tag]:
        self.list_tag_queries.append(list_query)
        active_tags = [
            tag
            for tag_id, tag in self.tags_by_id.items()
            if tag_id not in self.soft_deleted_tag_ids
        ]
        active_tags.sort(key=lambda tag: tag.id)
        return Page[Tag](
            items=active_tags[list_query.offset : list_query.offset + list_query.limit],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_tags),
        )

    async def get_tag(self, tag_id: int) -> Tag:
        if tag_id in self.soft_deleted_tag_ids or tag_id not in self.tags_by_id:
            raise TagNotFoundError()
        return self.tags_by_id[tag_id]

    async def create_tag(self, data: CreateTagData) -> Tag:
        tag = Tag(
            id=self._next_tag_id,
            title=data.title,
            created_at=build_timestamp(1),
            updated_at=build_timestamp(1),
        )
        self.tags_by_id[tag.id] = tag
        self._next_tag_id += 1
        return tag

    async def update_tag(self, tag_id: int, data: UpdateTagData) -> Tag:
        current = await self.get_tag(tag_id)
        updated = Tag(
            id=current.id,
            title=data.title,
            created_at=current.created_at,
            updated_at=build_timestamp(2),
        )
        self.tags_by_id[tag_id] = updated
        return updated

    async def delete_tag(self, tag_id: int, hard_delete: bool = False) -> None:
        self.delete_calls.append((tag_id, hard_delete))
        if tag_id in self.soft_deleted_tag_ids:
            if hard_delete:
                self.soft_deleted_tag_ids.remove(tag_id)
                self.tags_by_id.pop(tag_id, None)
                return
            raise TagNotFoundError()
        if tag_id not in self.tags_by_id:
            raise TagNotFoundError()
        if hard_delete:
            self.tags_by_id.pop(tag_id, None)
            return
        self.soft_deleted_tag_ids.add(tag_id)


class TransactionInputPortStub(TransactionInputPort):
    def __init__(self) -> None:
        self.list_transaction_queries: list[ListQuery] = []
        self.transactions_by_id: dict[int, TransactionWithEntries] = {}
        self.post_calls: list[int] = []
        self.void_calls: list[int] = []
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self.post_error: Exception | None = None
        self.void_error: Exception | None = None
        self._next_transaction_id = 1
        self._next_entry_id = 100

    async def list_transactions(
        self,
        list_query: ListQuery,
    ) -> Page[Transaction]:
        self.list_transaction_queries.append(list_query)
        transactions = [
            transaction_with_entries.transaction
            for transaction_with_entries in self.transactions_by_id.values()
        ]
        transactions.sort(key=lambda transaction: transaction.id)

        return Page[Transaction](
            items=transactions[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(transactions),
        )

    def _build_entry_with_tags(
        self,
        *,
        transaction_id: int,
        entry: NewEntry,
        entry_id: int,
        created_at: datetime,
        updated_at: datetime,
    ) -> EntryWithTags:
        return EntryWithTags(
            entry=Entry(
                id=entry_id,
                created_at=created_at,
                updated_at=updated_at,
                transaction_id=transaction_id,
                ledger_account_id=entry.ledger_account_id,
                amount=entry.amount,
                currency_id=entry.currency_id,
                statement_closing_date=entry.statement_closing_date,
                statement_due_date=entry.statement_due_date,
            ),
            entry_tags=tuple(
                EntryTag(entry_id=entry_id, tag_id=entry_tag.tag_id)
                for entry_tag in entry.entry_tags
            ),
        )

    def _build_transaction_with_entries(
        self,
        *,
        transaction_id: int,
        effective_at: datetime,
        title: str,
        description: str | None,
        status: TransactionStatus,
        entries: tuple[NewEntry, ...],
        created_at: datetime,
        updated_at: datetime,
        existing_entry_ids: tuple[int, ...] = (),
        existing_entry_created_ats: tuple[datetime, ...] = (),
    ) -> TransactionWithEntries:
        entry_items: list[EntryWithTags] = []

        for index, entry in enumerate(entries):
            if index < len(existing_entry_ids):
                entry_id = existing_entry_ids[index]
                entry_created_at = existing_entry_created_ats[index]
            else:
                entry_id = self._next_entry_id
                self._next_entry_id += 1
                entry_created_at = created_at

            entry_items.append(
                self._build_entry_with_tags(
                    transaction_id=transaction_id,
                    entry=entry,
                    entry_id=entry_id,
                    created_at=entry_created_at,
                    updated_at=updated_at,
                ),
            )

        return TransactionWithEntries(
            transaction=Transaction(
                id=transaction_id,
                created_at=created_at,
                updated_at=updated_at,
                effective_at=effective_at,
                title=title,
                description=description,
                status=status,
            ),
            entries=tuple(entry_items),
        )

    async def get_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        transaction = self.transactions_by_id.get(transaction_id)

        if transaction is None:
            raise TransactionNotFoundError()

        return transaction

    async def create_transaction(
        self,
        data: CreateTransactionData,
    ) -> TransactionWithEntries:
        if self.create_error is not None:
            raise self.create_error

        transaction = self._build_transaction_with_entries(
            transaction_id=self._next_transaction_id,
            effective_at=data.effective_at,
            title=data.title,
            description=data.description,
            status=data.status,
            entries=data.entries,
            created_at=build_timestamp(1),
            updated_at=build_timestamp(1),
        )
        self.transactions_by_id[transaction.transaction.id] = transaction
        self._next_transaction_id += 1
        return transaction

    async def update_transaction(
        self,
        transaction_id: int,
        data: UpdateTransactionData,
    ) -> TransactionWithEntries:
        if self.update_error is not None:
            raise self.update_error

        current = await self.get_transaction(transaction_id)

        if current.transaction.status != TransactionStatus.PENDING:
            raise TransactionMustBePendingError()

        updated = self._build_transaction_with_entries(
            transaction_id=transaction_id,
            effective_at=data.effective_at,
            title=data.title,
            description=data.description,
            status=current.transaction.status,
            entries=data.entries,
            created_at=current.transaction.created_at,
            updated_at=build_timestamp(2),
            existing_entry_ids=tuple(entry.entry.id for entry in current.entries),
            existing_entry_created_ats=tuple(
                entry.entry.created_at for entry in current.entries
            ),
        )
        self.transactions_by_id[transaction_id] = updated
        return updated

    async def post_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        if self.post_error is not None:
            raise self.post_error

        current = await self.get_transaction(transaction_id)

        if current.transaction.status != TransactionStatus.PENDING:
            raise TransactionStatusTransitionNotAllowedError()

        posted = TransactionWithEntries(
            transaction=Transaction(
                id=current.transaction.id,
                created_at=current.transaction.created_at,
                updated_at=build_timestamp(2),
                effective_at=current.transaction.effective_at,
                title=current.transaction.title,
                description=current.transaction.description,
                status=TransactionStatus.POSTED,
            ),
            entries=current.entries,
        )
        self.transactions_by_id[transaction_id] = posted
        self.post_calls.append(transaction_id)
        return posted

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries:
        if self.void_error is not None:
            raise self.void_error

        current = await self.get_transaction(transaction_id)

        if current.transaction.status != TransactionStatus.PENDING:
            raise TransactionStatusTransitionNotAllowedError()

        voided = TransactionWithEntries(
            transaction=Transaction(
                id=current.transaction.id,
                created_at=current.transaction.created_at,
                updated_at=build_timestamp(2),
                effective_at=current.transaction.effective_at,
                title=current.transaction.title,
                description=current.transaction.description,
                status=TransactionStatus.VOIDED,
            ),
            entries=current.entries,
        )
        self.transactions_by_id[transaction_id] = voided
        self.void_calls.append(transaction_id)
        return voided


def _sort_users(
    users: list[User],
    sort_terms: tuple[SortTerm, ...],
) -> list[User]:
    sorted_users = list(users)
    effective_sort_terms = sort_terms or (
        SortTerm(
            field="created_at",
            direction=SortDirection.DESC,
        ),
    )
    sort_chain = (
        *effective_sort_terms,
        SortTerm(
            field="id",
            direction=SortDirection.DESC,
        ),
    )

    for sort_term in reversed(sort_chain):
        sorted_users.sort(
            key=lambda user: getattr(user, sort_term.field),
            reverse=sort_term.direction == SortDirection.DESC,
        )

    return sorted_users


class UserInputPortStub(UserInputPort):
    def __init__(self) -> None:
        self.users_by_email: dict[str, User] = {}
        self.soft_deleted_emails: set[str] = set()
        self.delete_calls: list[tuple[str, bool]] = []
        self.list_user_queries: list[ListQuery] = []
        self._next_user_id = 1

    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]:
        self.list_user_queries.append(list_query)
        active_users = _sort_users(
            [
                user
                for user in self.users_by_email.values()
                if user.email not in self.soft_deleted_emails
            ],
            list_query.sort,
        )

        return Page[User](
            items=active_users[
                list_query.offset : list_query.offset + list_query.limit
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_users),
        )

    async def get_user(
        self,
        email: str,
    ) -> User:
        if email in self.soft_deleted_emails:
            raise UserNotFoundError()

        user = self.users_by_email.get(email)

        if user is None:
            raise UserNotFoundError()

        return user

    async def create_user(
        self,
        data: CreateUserData,
    ) -> User:
        if any(
            existing_user.email == data.email
            for existing_user in self.users_by_email.values()
        ):
            raise UserEmailConflictError()

        user = User(
            id=self._next_user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::plain-password",
            birth_date=data.birth_date,
            created_at=build_timestamp(
                day=3,
                year=2026,
                month=5,
                hour=12,
                minute=30,
                second=15,
                microsecond=123000,
            ),
            updated_at=build_timestamp(
                day=3,
                year=2026,
                month=5,
                hour=12,
                minute=30,
                second=15,
                microsecond=123000,
            ),
        )
        self.users_by_email[user.email] = user
        self._next_user_id += 1

        return user

    async def update_user(
        self,
        current_email: str,
        data: UpdateUserData,
    ) -> User:
        if current_email in self.soft_deleted_emails:
            raise UserNotFoundError()

        current_user = self.users_by_email.get(current_email)

        if current_user is None:
            raise UserNotFoundError()

        for existing_user in self.users_by_email.values():
            if (
                existing_user.id != current_user.id
                and existing_user.email == data.email
            ):
                raise UserEmailConflictError()

        user = User(
            id=current_user.id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash="hashed::new-password",
            birth_date=data.birth_date,
            created_at=current_user.created_at,
            updated_at=build_timestamp(
                day=3,
                year=2026,
                month=5,
                hour=13,
                minute=45,
                second=30,
                microsecond=456000,
            ),
        )
        del self.users_by_email[current_email]
        self.users_by_email[user.email] = user

        return user

    async def delete_user(
        self,
        email: str,
        hard_delete: bool = False,
    ) -> None:
        self.delete_calls.append((email, hard_delete))

        if email in self.soft_deleted_emails:
            if hard_delete:
                self.soft_deleted_emails.remove(email)
                self.users_by_email.pop(email, None)
                return

            raise UserNotFoundError()

        if email not in self.users_by_email:
            raise UserNotFoundError()

        if hard_delete:
            del self.users_by_email[email]
            return

        self.soft_deleted_emails.add(email)

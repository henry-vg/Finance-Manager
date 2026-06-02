from typing import Protocol

from src.core.domain.transaction import (
    NewEntry,
    NewTransaction,
    Transaction,
    TransactionChanges,
    TransactionWithEntries,
)
from src.core.shared import ListQuery, Page


class TransactionNotFoundOutputPortError(Exception):
    pass


class TransactionOutputPort(Protocol):  # pragma: no cover
    async def list_transactions(
        self,
        list_query: ListQuery,
    ) -> Page[Transaction]: ...

    async def get_transaction_by_id(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries | None: ...

    async def create_transaction(
        self,
        new_transaction: NewTransaction,
    ) -> TransactionWithEntries: ...

    async def update_transaction(
        self,
        transaction_id: int,
        changes: TransactionChanges,
    ) -> TransactionWithEntries: ...

    async def post_transaction(
        self,
        transaction_id: int,
        entries: tuple[NewEntry, ...],
    ) -> TransactionWithEntries: ...

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries: ...

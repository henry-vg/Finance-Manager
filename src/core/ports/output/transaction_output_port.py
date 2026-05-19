from typing import Protocol

from src.core.domain.transaction import (
    NewTransaction,
    TransactionChanges,
    TransactionWithEntries,
)


class TransactionNotFoundOutputPortError(Exception):
    pass


class TransactionOutputPort(Protocol):
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

    async def mark_transaction_effective(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries: ...

    async def cancel_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries: ...

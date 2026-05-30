from typing import Protocol

from src.core.domain.transaction import (
    CreateTransactionData,
    TransactionWithEntries,
    UpdateTransactionData,
)


class TransactionInputPort(Protocol):
    async def get_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries: ...

    async def create_transaction(
        self,
        data: CreateTransactionData,
    ) -> TransactionWithEntries: ...

    async def update_transaction(
        self,
        transaction_id: int,
        data: UpdateTransactionData,
    ) -> TransactionWithEntries: ...

    async def post_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries: ...

    async def void_transaction(
        self,
        transaction_id: int,
    ) -> TransactionWithEntries: ...

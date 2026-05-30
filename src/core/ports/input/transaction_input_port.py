from typing import Protocol

from src.core.domain.transaction import (
    CreateTransactionData,
    Transaction,
    TransactionWithEntries,
    UpdateTransactionData,
)
from src.core.shared import ListQuery, Page


class TransactionInputPort(Protocol):  # pragma: no cover
    async def list_transactions(
        self,
        list_query: ListQuery,
    ) -> Page[Transaction]: ...

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

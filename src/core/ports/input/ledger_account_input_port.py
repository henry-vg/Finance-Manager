from typing import Protocol

from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    LedgerAccount,
    UpdateLedgerAccountData,
)
from src.core.shared import ListQuery, Page


class LedgerAccountInputPort(Protocol):
    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]: ...

    async def get_ledger_account(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount: ...

    async def create_ledger_account(
        self,
        data: CreateLedgerAccountData,
    ) -> LedgerAccount: ...

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        data: UpdateLedgerAccountData,
    ) -> LedgerAccount: ...

    async def delete_ledger_account(
        self,
        ledger_account_id: int,
        hard_delete: bool = False,
    ) -> None: ...

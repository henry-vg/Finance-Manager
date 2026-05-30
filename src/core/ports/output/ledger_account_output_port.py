from typing import Protocol

from src.core.domain.ledger_account import (
    LedgerAccount,
    LedgerAccountChanges,
    NewLedgerAccount,
)
from src.core.shared import ListQuery, Page


class LedgerAccountNotFoundOutputPortError(Exception):
    pass


class LedgerAccountOutputPort(Protocol):  # pragma: no cover
    async def list_ledger_accounts(
        self,
        list_query: ListQuery,
    ) -> Page[LedgerAccount]: ...

    async def get_ledger_account_by_id(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None: ...

    async def get_ledger_account_by_id_including_deleted(
        self,
        ledger_account_id: int,
    ) -> LedgerAccount | None: ...

    async def create_ledger_account(
        self,
        new_ledger_account: NewLedgerAccount,
    ) -> LedgerAccount: ...

    async def update_ledger_account(
        self,
        ledger_account_id: int,
        changes: LedgerAccountChanges,
    ) -> LedgerAccount: ...

    async def soft_delete_ledger_account(
        self,
        ledger_account_id: int,
    ) -> None: ...

    async def hard_delete_ledger_account(
        self,
        ledger_account_id: int,
    ) -> None: ...

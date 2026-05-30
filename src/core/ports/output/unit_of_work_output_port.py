from typing import Protocol, Self

from .currency_output_port import CurrencyOutputPort
from .ledger_account_output_port import LedgerAccountOutputPort
from .tag_output_port import TagOutputPort
from .transaction_output_port import TransactionOutputPort
from .user_output_port import UserOutputPort


class UnitOfWorkOutputPort(Protocol):  # pragma: no cover
    @property
    def currencies(self) -> CurrencyOutputPort: ...

    @property
    def ledger_accounts(self) -> LedgerAccountOutputPort: ...

    @property
    def tags(self) -> TagOutputPort: ...

    @property
    def transactions(self) -> TransactionOutputPort: ...

    @property
    def users(self) -> UserOutputPort: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None: ...

    async def commit(self) -> None: ...


class UnitOfWorkOutputPortFactory(Protocol):  # pragma: no cover
    def __call__(self) -> UnitOfWorkOutputPort: ...

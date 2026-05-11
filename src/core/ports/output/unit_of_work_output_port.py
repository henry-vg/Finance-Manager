from typing import Protocol, Self

from .ledger_account_output_port import LedgerAccountOutputPort
from .tag_output_port import TagOutputPort
from .user_output_port import UserOutputPort


class UnitOfWorkOutputPort(Protocol):
    @property
    def ledger_accounts(self) -> LedgerAccountOutputPort: ...

    @property
    def tags(self) -> TagOutputPort: ...

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


class UnitOfWorkOutputPortFactory(Protocol):
    def __call__(self) -> UnitOfWorkOutputPort: ...

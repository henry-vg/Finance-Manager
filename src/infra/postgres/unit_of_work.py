from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.ports.output import UnitOfWorkOutputPort
from src.core.ports.output.tag_output_port import TagOutputPort
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.ports.output.user_output_port import UserOutputPort
from src.infra.postgres.aggregates.tag import SQLAlchemyTagOutputAdapter
from src.infra.postgres.aggregates.user import SQLAlchemyUserOutputAdapter


class UnitOfWorkHasNotBeenEnteredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Unit of work has not been entered")


class UnitOfWorkIsAlreadyActiveError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Unit of work is already active")


class UnitOfWorkCannotBeReusedAfterExitError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Unit of work cannot be reused after exit")


class SQLAlchemyPostgresUnitOfWork(UnitOfWorkOutputPort):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._tags: TagOutputPort | None = None
        self._users: UserOutputPort | None = None
        self._is_closed = False

    @property
    def tags(self) -> TagOutputPort:
        if self._tags is None:
            raise UnitOfWorkHasNotBeenEnteredError()

        return self._tags

    @property
    def users(self) -> UserOutputPort:
        if self._users is None:
            raise UnitOfWorkHasNotBeenEnteredError()

        return self._users

    async def __aenter__(self) -> "SQLAlchemyPostgresUnitOfWork":
        if self._session is not None:
            raise UnitOfWorkIsAlreadyActiveError()

        if self._is_closed:
            raise UnitOfWorkCannotBeReusedAfterExitError()

        self._session = self._session_factory()
        self._tags = SQLAlchemyTagOutputAdapter(self._session)
        self._users = SQLAlchemyUserOutputAdapter(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc
        del traceback

        session = self._session

        if session is None:
            return

        try:
            if session.in_transaction():
                await session.rollback()
        finally:
            try:
                await session.close()
            finally:
                self._session = None
                self._tags = None
                self._users = None
                self._is_closed = True

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise UnitOfWorkHasNotBeenEnteredError()

        return self._session

    async def commit(self) -> None:
        session = self._require_session()

        await session.commit()


class SQLAlchemyPostgresUnitOfWorkFactory(UnitOfWorkOutputPortFactory):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyPostgresUnitOfWork:
        return SQLAlchemyPostgresUnitOfWork(self._session_factory)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.ports.output import UnitOfWorkOutputPort
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.ports.output.user_output_port import UserOutputPort
from src.infra.postgres.aggregates.user import SQLAlchemyUserOutputAdapter


class SQLAlchemyPostgresUnitOfWork(UnitOfWorkOutputPort):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._users: UserOutputPort | None = None
        self._is_closed = False

    @property
    def users(self) -> UserOutputPort:
        if self._users is None:
            raise RuntimeError("Unit of work has not been entered")

        return self._users

    async def __aenter__(self) -> "SQLAlchemyPostgresUnitOfWork":
        if self._session is not None:
            raise RuntimeError("Unit of work is already active")

        if self._is_closed:
            raise RuntimeError("Unit of work cannot be reused after exit")

        self._session = self._session_factory()
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
                self._users = None
                self._is_closed = True

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered")

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

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.domain.user import (
    NewUser,
    User,
    UserChanges,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.output.user_output_port import UserOutputPort

from .model import UserRecord


def _to_domain_user(
    user_record: UserRecord,
) -> User:
    return User(
        id=user_record.id,
        first_name=user_record.first_name,
        last_name=user_record.last_name,
        email=user_record.email,
        password_hash=user_record.password_hash,
        birth_date=user_record.birth_date,
        created_at=user_record.created_at,
        updated_at=user_record.updated_at,
    )


class SQLAlchemyUserOutputAdapter(UserOutputPort):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_user_by_email(
        self,
        email,
    ) -> User | None:
        async with self._session_factory() as session:
            user_record = await session.scalar(
                select(UserRecord).where(UserRecord.email == email),
            )

        if user_record is None:
            return None

        return _to_domain_user(
            user_record=user_record,
        )

    async def create_user(
        self,
        new_user: NewUser,
    ) -> User:
        user_record = UserRecord()
        user_record.first_name = new_user.first_name
        user_record.last_name = new_user.last_name
        user_record.email = new_user.email
        user_record.password_hash = new_user.password_hash
        user_record.birth_date = new_user.birth_date

        async with self._session_factory() as session:
            session.add(user_record)

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise UserEmailConflictError() from exc

            await session.refresh(user_record)

        return _to_domain_user(
            user_record=user_record,
        )

    async def update_user(
        self,
        user_id: int,
        changes: UserChanges,
    ) -> User:
        async with self._session_factory() as session:
            user_record = await session.get(
                UserRecord,
                user_id,
            )

            if user_record is None:
                raise UserNotFoundError()

            user_record.first_name = changes.first_name
            user_record.last_name = changes.last_name
            user_record.email = changes.email
            user_record.password_hash = changes.password_hash
            user_record.birth_date = changes.birth_date

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise UserEmailConflictError() from exc

            await session.refresh(user_record)

        return _to_domain_user(
            user_record=user_record,
        )

    async def delete_user(
        self,
        user_id,
    ) -> None:
        async with self._session_factory() as session:
            user_record = await session.get(
                UserRecord,
                user_id,
            )

            if user_record is None:
                raise UserNotFoundError()

            await session.delete(user_record)
            await session.commit()

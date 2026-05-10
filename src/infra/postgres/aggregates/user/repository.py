from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.user import (
    NewUser,
    User,
    UserChanges,
    UserNotFoundError,
    UserSortableField,
)
from src.core.ports.output.user_output_port import (
    UserEmailConflictOutputPortError,
    UserOutputPort,
)
from src.core.shared import ListQuery, Page, SortDirection

from ...integrity import is_unique_violation
from ...listing import build_order_clauses
from .models import USER_EMAIL_UNIQUE_CONSTRAINT_NAME, UserRecord

_USER_LIST_SORT_COLUMNS: dict[UserSortableField, Any] = {
    UserSortableField.ID: UserRecord.id,
    UserSortableField.FIRST_NAME: UserRecord.first_name,
    UserSortableField.LAST_NAME: UserRecord.last_name,
    UserSortableField.EMAIL: UserRecord.email,
    UserSortableField.BIRTH_DATE: UserRecord.birth_date,
    UserSortableField.CREATED_AT: UserRecord.created_at,
    UserSortableField.UPDATED_AT: UserRecord.updated_at,
}


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
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]:
        statement = (
            select(UserRecord)
            .where(UserRecord.is_deleted.is_(False))
            .order_by(
                *build_order_clauses(
                    sort_terms=list_query.sort,
                    sort_field_enum=UserSortableField,
                    sort_columns=_USER_LIST_SORT_COLUMNS,
                    tie_break_field=UserSortableField.ID,
                    tie_break_direction=SortDirection.DESC,
                ),
            )
            .offset(list_query.offset)
            .limit(list_query.limit)
        )
        total_statement = (
            select(func.count())
            .select_from(UserRecord)
            .where(
                UserRecord.is_deleted.is_(False),
            )
        )

        user_records = cast(
            list[UserRecord],
            list((await self._session.scalars(statement)).all()),
        )
        total = cast(int, await self._session.scalar(total_statement))

        return Page[User](
            items=[
                _to_domain_user(
                    user_record=user_record,
                )
                for user_record in user_records
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=total,
        )

    async def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        user_record = await self._get_user_record_by_email(
            email=email,
        )

        if user_record is None:
            return None

        return _to_domain_user(
            user_record=user_record,
        )

    async def get_user_by_email_including_deleted(
        self,
        email: str,
    ) -> User | None:
        user_record = await self._get_user_record_by_email(
            email=email,
            include_deleted=True,
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

        self._session.add(user_record)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            if is_unique_violation(
                exc,
                constraint_name=USER_EMAIL_UNIQUE_CONSTRAINT_NAME,
            ):
                raise UserEmailConflictOutputPortError() from exc

            raise

        await self._session.refresh(user_record)

        return _to_domain_user(
            user_record=user_record,
        )

    async def update_user(
        self,
        user_id: int,
        changes: UserChanges,
    ) -> User:
        user_record = await self._get_user_record_by_id(
            user_id=user_id,
        )

        if user_record is None:
            raise UserNotFoundError()

        user_record.first_name = changes.first_name
        user_record.last_name = changes.last_name
        user_record.email = changes.email
        user_record.password_hash = changes.password_hash
        user_record.birth_date = changes.birth_date

        try:
            await self._session.flush()
        except IntegrityError as exc:
            if is_unique_violation(
                exc,
                constraint_name=USER_EMAIL_UNIQUE_CONSTRAINT_NAME,
            ):
                raise UserEmailConflictOutputPortError() from exc

            raise

        await self._session.refresh(user_record)

        return _to_domain_user(
            user_record=user_record,
        )

    async def soft_delete_user(
        self,
        user_id: int,
    ) -> None:
        user_record = await self._get_user_record_by_id(
            user_id=user_id,
        )

        if user_record is None:
            raise UserNotFoundError()

        user_record.is_deleted = True

        await self._session.flush()

    async def hard_delete_user(
        self,
        user_id: int,
    ) -> None:
        user_record = await self._get_user_record_by_id(
            user_id=user_id,
            include_deleted=True,
        )

        if user_record is None:
            raise UserNotFoundError()

        await self._session.delete(user_record)
        await self._session.flush()

    async def _get_user_record_by_email(
        self,
        *,
        email: str,
        include_deleted: bool = False,
    ) -> UserRecord | None:
        statement = select(UserRecord).where(UserRecord.email == email)

        if not include_deleted:
            statement = statement.where(UserRecord.is_deleted.is_(False))

        return cast(UserRecord | None, await self._session.scalar(statement))

    async def _get_user_record_by_id(
        self,
        *,
        user_id: int,
        include_deleted: bool = False,
    ) -> UserRecord | None:
        statement = select(UserRecord).where(UserRecord.id == user_id)

        if not include_deleted:
            statement = statement.where(UserRecord.is_deleted.is_(False))

        return cast(UserRecord | None, await self._session.scalar(statement))

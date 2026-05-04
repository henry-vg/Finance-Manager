from typing import Protocol

from src.core.domain.user import NewUser, User, UserChanges


class UserOutputPort(Protocol):
    async def get_user_by_email(
        self,
        email: str,
    ) -> User | None: ...

    async def create_user(
        self,
        new_user: NewUser,
    ) -> User: ...

    async def update_user(
        self,
        user_id: int,
        changes: UserChanges,
    ) -> User: ...

    async def delete_user(
        self,
        user_id: int,
    ) -> None: ...

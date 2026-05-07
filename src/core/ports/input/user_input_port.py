from typing import Protocol

from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
)
from src.core.shared import ListQuery, Page


class UserInputPort(Protocol):
    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]: ...

    async def get_user(
        self,
        email: str,
    ) -> User: ...

    async def create_user(
        self,
        data: CreateUserData,
    ) -> User: ...

    async def update_user(
        self,
        current_email: str,
        data: UpdateUserData,
    ) -> User: ...

    async def delete_user(
        self,
        email: str,
        hard_delete: bool = False,
    ) -> None: ...

from typing import Protocol

from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
)


class UserInputPort(Protocol):
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
    ) -> None: ...

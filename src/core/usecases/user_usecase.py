from src.core.domain.user import (
    CreateUserData,
    NewUser,
    UpdateUserData,
    User,
    UserChanges,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.input.user_input_port import UserInputPort
from src.core.ports.output.password_hasher_output_port import PasswordHasherOutputPort
from src.core.ports.output.user_output_port import UserOutputPort


class UserUseCase(UserInputPort):
    def __init__(
        self,
        user_output_port: UserOutputPort,
        password_hasher_output_port: PasswordHasherOutputPort,
    ) -> None:
        self._user_output_port = user_output_port
        self._password_hasher_output_port = password_hasher_output_port

    async def get_user(
        self,
        email: str,
    ) -> User:
        user = await self._user_output_port.get_user_by_email(
            email=email,
        )

        if user is None:
            raise UserNotFoundError()

        return user

    async def create_user(
        self,
        data: CreateUserData,
    ) -> User:
        existing_user = await self._user_output_port.get_user_by_email(
            email=data.email,
        )

        if existing_user is not None:
            raise UserEmailConflictError()

        new_user = NewUser(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash=self._password_hasher_output_port.hash_password(
                password=data.password,
            ),
            birth_date=data.birth_date,
        )

        return await self._user_output_port.create_user(
            new_user=new_user,
        )

    async def update_user(
        self,
        current_email: str,
        data: UpdateUserData,
    ) -> User:
        current_user = await self._user_output_port.get_user_by_email(
            email=current_email,
        )

        if current_user is None:
            raise UserNotFoundError()

        existing_user = await self._user_output_port.get_user_by_email(
            email=data.email,
        )

        if existing_user is not None and existing_user.id != current_user.id:
            raise UserEmailConflictError()

        changes = UserChanges(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash=self._password_hasher_output_port.hash_password(
                password=data.password,
            ),
            birth_date=data.birth_date,
        )

        return await self._user_output_port.update_user(
            user_id=current_user.id,
            changes=changes,
        )

    async def delete_user(
        self,
        email: str,
    ) -> None:
        current_user = await self._user_output_port.get_user_by_email(
            email=email,
        )

        if current_user is None:
            raise UserNotFoundError()

        await self._user_output_port.delete_user(
            user_id=current_user.id,
        )

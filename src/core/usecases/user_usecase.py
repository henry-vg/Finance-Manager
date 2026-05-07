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
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.ports.output.user_output_port import UserEmailConflictOutputPortError
from src.core.shared import ListQuery, Page


class UserUseCase(UserInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
        password_hasher_output_port: PasswordHasherOutputPort,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory
        self._password_hasher_output_port = password_hasher_output_port

    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            return await unit_of_work.users.list_users(
                list_query=list_query,
            )

    async def get_user(
        self,
        email: str,
    ) -> User:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            user = await unit_of_work.users.get_user_by_email(
                email=email,
            )

            if user is None:
                raise UserNotFoundError()

            return user

    async def create_user(
        self,
        data: CreateUserData,
    ) -> User:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            existing_user = await unit_of_work.users.get_user_by_email(
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

            try:
                created_user = await unit_of_work.users.create_user(
                    new_user=new_user,
                )
            except UserEmailConflictOutputPortError as exc:
                raise UserEmailConflictError() from exc

            await unit_of_work.commit()

            return created_user

    async def update_user(
        self,
        current_email: str,
        data: UpdateUserData,
    ) -> User:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_user = await unit_of_work.users.get_user_by_email(
                email=current_email,
            )

            if current_user is None:
                raise UserNotFoundError()

            existing_user = await unit_of_work.users.get_user_by_email(
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

            try:
                updated_user = await unit_of_work.users.update_user(
                    user_id=current_user.id,
                    changes=changes,
                )
            except UserEmailConflictOutputPortError as exc:
                raise UserEmailConflictError() from exc

            await unit_of_work.commit()

            return updated_user

    async def delete_user(
        self,
        email: str,
        hard_delete: bool = False,
    ) -> None:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            if hard_delete:
                current_user = (
                    await unit_of_work.users.get_user_by_email_including_deleted(
                        email=email,
                    )
                )
            else:
                current_user = await unit_of_work.users.get_user_by_email(
                    email=email,
                )

            if current_user is None:
                raise UserNotFoundError()

            if hard_delete:
                await unit_of_work.users.hard_delete_user(
                    user_id=current_user.id,
                )
            else:
                await unit_of_work.users.soft_delete_user(
                    user_id=current_user.id,
                )

            await unit_of_work.commit()

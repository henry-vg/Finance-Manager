from datetime import UTC, date, datetime

import pytest

from src.core.domain.user import (
    CreateUserData,
    NewUser,
    UpdateUserData,
    User,
    UserChanges,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.output.password_hasher_output_port import PasswordHasherOutputPort
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.ports.output.user_output_port import (
    UserEmailConflictOutputPortError,
    UserOutputPort,
)
from src.core.shared import ListQuery, Page
from src.core.usecases.user_usecase import UserUseCase


def _build_timestamp(
    *,
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        tzinfo=UTC,
    )


def _build_create_user_data() -> CreateUserData:
    return CreateUserData(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password="plain-password",
        birth_date=date(1815, 12, 10),
    )


def _build_update_user_data() -> UpdateUserData:
    return UpdateUserData(
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password="new-password",
        birth_date=date(1906, 12, 9),
    )


class _PasswordHasherOutputPortStub(PasswordHasherOutputPort):
    def hash_password(
        self,
        password: str,
    ) -> str:
        return f"hashed::{password}"

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return password_hash == f"hashed::{password}"


class _UserOutputPortStub(UserOutputPort):
    def __init__(
        self,
    ) -> None:
        self.users_by_id: dict[int, User] = {}
        self.soft_deleted_user_ids: list[int] = []
        self.hard_deleted_user_ids: list[int] = []
        self.created_users: list[NewUser] = []
        self.list_user_queries: list[ListQuery] = []
        self.updated_users: list[tuple[int, UserChanges]] = []
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self._next_user_id = 1

    async def list_users(
        self,
        list_query: ListQuery,
    ) -> Page[User]:
        self.list_user_queries.append(list_query)

        active_users = [
            user
            for user_id, user in sorted(self.users_by_id.items())
            if user_id not in self.soft_deleted_user_ids
        ]
        page_items = active_users[
            list_query.offset : list_query.offset + list_query.limit
        ]

        return Page[User](
            items=page_items,
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_users),
        )

    async def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        for user_id, user in self.users_by_id.items():
            if user_id in self.soft_deleted_user_ids:
                continue

            if user.email == email:
                return user

        return None

    async def get_user_by_email_including_deleted(
        self,
        email: str,
    ) -> User | None:
        for user in self.users_by_id.values():
            if user.email == email:
                return user

        return None

    async def create_user(
        self,
        new_user: NewUser,
    ) -> User:
        if self.create_error is not None:
            raise self.create_error

        self.created_users.append(new_user)

        created_user = User(
            id=self._next_user_id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
            password_hash=new_user.password_hash,
            birth_date=new_user.birth_date,
            created_at=_build_timestamp(
                year=2026,
                month=5,
                day=3,
                hour=12,
                minute=30,
                second=15,
                microsecond=123000,
            ),
            updated_at=_build_timestamp(
                year=2026,
                month=5,
                day=3,
                hour=12,
                minute=30,
                second=15,
                microsecond=123000,
            ),
        )
        self.users_by_id[self._next_user_id] = created_user
        self._next_user_id += 1
        return created_user

    async def update_user(
        self,
        user_id: int,
        changes: UserChanges,
    ) -> User:
        if self.update_error is not None:
            raise self.update_error

        current_user = self.users_by_id.get(user_id)

        if current_user is None:
            raise UserNotFoundError()

        self.updated_users.append((user_id, changes))

        updated_user = User(
            id=user_id,
            first_name=changes.first_name,
            last_name=changes.last_name,
            email=changes.email,
            password_hash=changes.password_hash,
            birth_date=changes.birth_date,
            created_at=current_user.created_at,
            updated_at=_build_timestamp(
                year=2026,
                month=5,
                day=3,
                hour=14,
                minute=45,
                second=30,
                microsecond=789000,
            ),
        )
        self.users_by_id[user_id] = updated_user
        return updated_user

    async def soft_delete_user(
        self,
        user_id: int,
    ) -> None:
        if user_id not in self.users_by_id:
            raise UserNotFoundError()

        self.soft_deleted_user_ids.append(user_id)

    async def hard_delete_user(
        self,
        user_id: int,
    ) -> None:
        if user_id not in self.users_by_id:
            raise UserNotFoundError()

        self.hard_deleted_user_ids.append(user_id)
        while user_id in self.soft_deleted_user_ids:
            self.soft_deleted_user_ids.remove(user_id)
        self.users_by_id.pop(user_id, None)


class _UnitOfWorkOutputPortStub(UnitOfWorkOutputPort):
    def __init__(
        self,
        user_output_port: _UserOutputPortStub,
    ) -> None:
        self._user_output_port = user_output_port
        self.commit_calls = 0
        self.rollback_calls = 0

    @property
    def users(self) -> UserOutputPort:
        return self._user_output_port

    async def __aenter__(self) -> "_UnitOfWorkOutputPortStub":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc
        del traceback

        if exc_type is not None:
            self.rollback_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1


class _UnitOfWorkOutputPortFactoryStub(UnitOfWorkOutputPortFactory):
    def __init__(
        self,
        user_output_port: _UserOutputPortStub,
    ) -> None:
        self._user_output_port = user_output_port
        self.created_unit_of_work_output_ports: list[_UnitOfWorkOutputPortStub] = []

    def __call__(self) -> _UnitOfWorkOutputPortStub:
        unit_of_work_output_port = _UnitOfWorkOutputPortStub(
            self._user_output_port,
        )
        self.created_unit_of_work_output_ports.append(unit_of_work_output_port)
        return unit_of_work_output_port


def _build_user_usecase(
    user_output_port: _UserOutputPortStub,
) -> tuple[UserUseCase, _UnitOfWorkOutputPortFactoryStub]:
    unit_of_work_output_port_factory = _UnitOfWorkOutputPortFactoryStub(
        user_output_port,
    )

    return UserUseCase(
        unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        password_hasher_output_port=_PasswordHasherOutputPortStub(),
    ), unit_of_work_output_port_factory


def _get_created_unit_of_work_output_port(
    unit_of_work_output_port_factory: _UnitOfWorkOutputPortFactoryStub,
) -> _UnitOfWorkOutputPortStub:
    return unit_of_work_output_port_factory.created_unit_of_work_output_ports[0]


@pytest.mark.anyio
async def test_get_user_returns_existing_user() -> None:
    existing_user = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=3),
        updated_at=_build_timestamp(year=2026, month=5, day=3),
    )
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = existing_user

    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    result = await use_case.get_user(
        email="ada@example.com",
    )

    assert result == existing_user
    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 0


@pytest.mark.anyio
async def test_list_users_returns_paginated_active_users_without_commit() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=1),
    )
    user_output_port_stub.users_by_id[2] = User(
        id=2,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1906, 12, 9),
        created_at=_build_timestamp(year=2026, month=5, day=2),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    user_output_port_stub.users_by_id[3] = User(
        id=3,
        first_name="Katherine",
        last_name="Johnson",
        email="katherine@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1918, 8, 26),
        created_at=_build_timestamp(year=2026, month=5, day=3),
        updated_at=_build_timestamp(year=2026, month=5, day=3),
    )
    user_output_port_stub.soft_deleted_user_ids.append(2)
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    list_query = ListQuery(
        offset=0,
        limit=2,
    )

    result = await use_case.list_users(
        list_query=list_query,
    )

    assert result == Page[User](
        items=[
            user_output_port_stub.users_by_id[1],
            user_output_port_stub.users_by_id[3],
        ],
        offset=0,
        limit=2,
        total=2,
    )
    assert user_output_port_stub.list_user_queries == [list_query]
    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 0


@pytest.mark.anyio
async def test_get_user_raises_when_user_does_not_exist() -> None:
    user_output_port_stub = _UserOutputPortStub()
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    with pytest.raises(UserNotFoundError):
        await use_case.get_user(
            email="missing@example.com",
        )

    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.rollback_calls == 1


@pytest.mark.anyio
async def test_create_user_hashes_password_and_persists_user() -> None:
    user_output_port_stub = _UserOutputPortStub()
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    result = await use_case.create_user(
        data=_build_create_user_data(),
    )

    assert result.first_name == "Ada"
    assert result.last_name == "Lovelace"
    assert result.email == "ada@example.com"
    assert result.id == 1
    assert result.password_hash == "hashed::plain-password"
    assert result.birth_date == date(1815, 12, 10)
    assert result.created_at == _build_timestamp(
        year=2026,
        month=5,
        day=3,
        hour=12,
        minute=30,
        second=15,
        microsecond=123000,
    )
    assert result.updated_at == _build_timestamp(
        year=2026,
        month=5,
        day=3,
        hour=12,
        minute=30,
        second=15,
        microsecond=123000,
    )
    assert user_output_port_stub.created_users == [
        NewUser(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            password_hash="hashed::plain-password",
            birth_date=date(1815, 12, 10),
        ),
    ]
    assert user_output_port_stub.users_by_id[1] == result
    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 1


@pytest.mark.anyio
async def test_create_user_raises_when_email_is_already_in_use() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Existing",
        last_name="User",
        email="ada@example.com",
        password_hash="hashed::another-password",
        birth_date=date(2000, 1, 1),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    with pytest.raises(UserEmailConflictError):
        await use_case.create_user(
            data=_build_create_user_data(),
        )

    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 0
    assert unit_of_work_output_port.rollback_calls == 1


@pytest.mark.anyio
async def test_create_user_translates_output_port_conflict_to_domain_error() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.create_error = UserEmailConflictOutputPortError()
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    with pytest.raises(UserEmailConflictError):
        await use_case.create_user(
            data=_build_create_user_data(),
        )

    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 0
    assert unit_of_work_output_port.rollback_calls == 1


@pytest.mark.anyio
async def test_update_user_replaces_all_fields_and_rehashes_password() -> None:
    created_at = _build_timestamp(year=2026, month=5, day=1)
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::old-password",
        birth_date=date(1815, 12, 10),
        created_at=created_at,
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    result = await use_case.update_user(
        current_email="ada@example.com",
        data=_build_update_user_data(),
    )

    assert result == User(
        id=1,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password_hash="hashed::new-password",
        birth_date=date(1906, 12, 9),
        created_at=created_at,
        updated_at=_build_timestamp(
            year=2026,
            month=5,
            day=3,
            hour=14,
            minute=45,
            second=30,
            microsecond=789000,
        ),
    )
    assert user_output_port_stub.updated_users == [
        (
            1,
            UserChanges(
                first_name="Grace",
                last_name="Hopper",
                email="grace@example.com",
                password_hash="hashed::new-password",
                birth_date=date(1906, 12, 9),
            ),
        ),
    ]
    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 1


@pytest.mark.anyio
async def test_update_user_raises_when_email_belongs_to_another_user() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::old-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    user_output_port_stub.users_by_id[2] = User(
        id=2,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        password_hash="hashed::another-password",
        birth_date=date(1906, 12, 9),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    with pytest.raises(UserEmailConflictError):
        await use_case.update_user(
            current_email="ada@example.com",
            data=UpdateUserData(
                first_name="Ada",
                last_name="Lovelace",
                email="grace@example.com",
                password="new-password",
                birth_date=date(1815, 12, 10),
            ),
        )

    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 0
    assert unit_of_work_output_port.rollback_calls == 1


@pytest.mark.anyio
async def test_update_user_translates_output_port_conflict_to_domain_error() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::old-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    user_output_port_stub.update_error = UserEmailConflictOutputPortError()
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    with pytest.raises(UserEmailConflictError):
        await use_case.update_user(
            current_email="ada@example.com",
            data=_build_update_user_data(),
        )

    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 0
    assert unit_of_work_output_port.rollback_calls == 1


@pytest.mark.anyio
async def test_delete_user_soft_deletes_existing_user_by_default() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    await use_case.delete_user(
        email="ada@example.com",
    )

    assert user_output_port_stub.soft_deleted_user_ids == [1]
    assert user_output_port_stub.hard_deleted_user_ids == []
    assert 1 in user_output_port_stub.users_by_id
    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 1


@pytest.mark.anyio
async def test_delete_user_raises_when_user_does_not_exist() -> None:
    user_output_port_stub = _UserOutputPortStub()
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    with pytest.raises(UserNotFoundError):
        await use_case.delete_user(
            email="missing@example.com",
        )

    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.rollback_calls == 1


@pytest.mark.anyio
async def test_delete_user_hard_deletes_soft_deleted_user_when_requested() -> None:
    user_output_port_stub = _UserOutputPortStub()
    user_output_port_stub.users_by_id[1] = User(
        id=1,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password_hash="hashed::plain-password",
        birth_date=date(1815, 12, 10),
        created_at=_build_timestamp(year=2026, month=5, day=1),
        updated_at=_build_timestamp(year=2026, month=5, day=2),
    )
    user_output_port_stub.soft_deleted_user_ids.append(1)
    use_case, unit_of_work_output_port_factory = _build_user_usecase(
        user_output_port_stub,
    )

    await use_case.delete_user(
        email="ada@example.com",
        hard_delete=True,
    )

    assert user_output_port_stub.soft_deleted_user_ids == []
    assert user_output_port_stub.hard_deleted_user_ids == [1]
    assert 1 not in user_output_port_stub.users_by_id
    unit_of_work_output_port = _get_created_unit_of_work_output_port(
        unit_of_work_output_port_factory,
    )
    assert unit_of_work_output_port.commit_calls == 1

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum


class UserSortableField(IntEnum):
    ID = 1
    FIRST_NAME = 2
    LAST_NAME = 3
    EMAIL = 4
    BIRTH_DATE = 5
    CREATED_AT = 6
    UPDATED_AT = 7


@dataclass(frozen=True)
class User:
    id: int
    first_name: str
    last_name: str
    email: str
    password_hash: str
    birth_date: date
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewUser:
    first_name: str
    last_name: str
    email: str
    password_hash: str
    birth_date: date


@dataclass(frozen=True)
class UserChanges:
    first_name: str
    last_name: str
    email: str
    password_hash: str
    birth_date: date


@dataclass(frozen=True)
class CreateUserData:
    first_name: str
    last_name: str
    email: str
    password: str
    birth_date: date


@dataclass(frozen=True)
class UpdateUserData:
    first_name: str
    last_name: str
    email: str
    password: str
    birth_date: date


class UserNotFoundError(Exception):
    pass


class UserEmailConflictError(Exception):
    pass

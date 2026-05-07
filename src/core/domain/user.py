from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class UserSortableField(StrEnum):
    ID = "id"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    EMAIL = "email"
    BIRTH_DATE = "birth_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


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

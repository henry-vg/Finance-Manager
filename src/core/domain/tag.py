from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum


class TagSortableField(IntEnum):
    ID = 1
    CREATED_AT = 2
    UPDATED_AT = 3
    TITLE = 4


@dataclass(frozen=True)
class Tag:
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewTag:
    title: str


@dataclass(frozen=True)
class TagChanges:
    title: str


@dataclass(frozen=True)
class CreateTagData:
    title: str


@dataclass(frozen=True)
class UpdateTagData:
    title: str


class TagNotFoundError(Exception):
    pass

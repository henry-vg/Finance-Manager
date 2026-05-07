from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class SortTerm(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    field: str = Field(min_length=1)
    direction: SortDirection


class ListQuery(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    sort: tuple[SortTerm, ...] = Field(default_factory=tuple)


class Page[ItemT](BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    items: list[ItemT]
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    total: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_items_length(self) -> Self:
        if len(self.items) > self.limit:
            raise ValueError("items length cannot be greater than limit")

        return self

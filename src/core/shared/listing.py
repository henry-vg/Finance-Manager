from pydantic import BaseModel, ConfigDict, Field


class ListQuery(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    offset: int = Field(ge=0)
    limit: int = Field(gt=0)


class Page[ItemT](BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    items: list[ItemT]
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    total: int = Field(ge=0)

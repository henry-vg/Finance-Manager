from datetime import datetime

from pydantic import Field

from .base import ApiSchemaBase


class CreateTagRequest(ApiSchemaBase):
    title: str = Field(min_length=1)


class UpdateTagRequest(ApiSchemaBase):
    title: str = Field(min_length=1)


class TagResponse(ApiSchemaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    title: str

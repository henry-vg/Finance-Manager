from datetime import datetime

from .base import ApiSchemaBase


class CreateTagRequest(ApiSchemaBase):
    title: str


class UpdateTagRequest(ApiSchemaBase):
    title: str


class TagResponse(ApiSchemaBase):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

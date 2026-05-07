from .base import ApiSchemaBase


class PageResponse[ItemSchemaT](ApiSchemaBase):
    items: list[ItemSchemaT]
    offset: int
    limit: int
    total: int

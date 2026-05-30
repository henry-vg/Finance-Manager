from typing import Protocol

from src.core.domain.tag import CreateTagData, Tag, UpdateTagData
from src.core.shared import ListQuery, Page


class TagInputPort(Protocol):  # pragma: no cover
    async def list_tags(
        self,
        list_query: ListQuery,
    ) -> Page[Tag]: ...

    async def get_tag(
        self,
        tag_id: int,
    ) -> Tag: ...

    async def create_tag(
        self,
        data: CreateTagData,
    ) -> Tag: ...

    async def update_tag(
        self,
        tag_id: int,
        data: UpdateTagData,
    ) -> Tag: ...

    async def delete_tag(
        self,
        tag_id: int,
        hard_delete: bool = False,
    ) -> None: ...

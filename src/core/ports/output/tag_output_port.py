from typing import Protocol

from src.core.domain.tag import NewTag, Tag, TagChanges
from src.core.shared import ListQuery, Page


class TagOutputPort(Protocol):
    async def list_tags(
        self,
        list_query: ListQuery,
    ) -> Page[Tag]: ...

    async def get_tag_by_id(
        self,
        tag_id: int,
    ) -> Tag | None: ...

    async def get_tag_by_id_including_deleted(
        self,
        tag_id: int,
    ) -> Tag | None: ...

    async def create_tag(
        self,
        new_tag: NewTag,
    ) -> Tag: ...

    async def update_tag(
        self,
        tag_id: int,
        changes: TagChanges,
    ) -> Tag: ...

    async def soft_delete_tag(
        self,
        tag_id: int,
    ) -> None: ...

    async def hard_delete_tag(
        self,
        tag_id: int,
    ) -> None: ...

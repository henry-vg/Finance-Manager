from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.tag import NewTag, Tag, TagChanges, TagSortableField
from src.core.ports.output.tag_output_port import (
    TagNotFoundOutputPortError,
    TagOutputPort,
)
from src.core.shared import ListQuery, Page, SortDirection

from ...listing import build_order_clauses
from .models import TagRecord

_TAG_LIST_SORT_COLUMNS: dict[TagSortableField, Any] = {
    TagSortableField.ID: TagRecord.id,
    TagSortableField.TITLE: TagRecord.title,
    TagSortableField.CREATED_AT: TagRecord.created_at,
    TagSortableField.UPDATED_AT: TagRecord.updated_at,
}


def _to_domain_tag(
    tag_record: TagRecord,
) -> Tag:
    return Tag(
        id=tag_record.id,
        title=tag_record.title,
        created_at=tag_record.created_at,
        updated_at=tag_record.updated_at,
    )


class SQLAlchemyTagOutputAdapter(TagOutputPort):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def list_tags(
        self,
        list_query: ListQuery,
    ) -> Page[Tag]:
        statement = (
            select(TagRecord)
            .where(TagRecord.is_deleted.is_(False))
            .order_by(
                *build_order_clauses(
                    sort_terms=list_query.sort,
                    sort_field_enum=TagSortableField,
                    sort_columns=_TAG_LIST_SORT_COLUMNS,
                    tie_break_field=TagSortableField.ID,
                    tie_break_direction=SortDirection.DESC,
                ),
            )
            .offset(list_query.offset)
            .limit(list_query.limit)
        )
        total_statement = (
            select(func.count())
            .select_from(TagRecord)
            .where(
                TagRecord.is_deleted.is_(False),
            )
        )

        tag_records = cast(
            list[TagRecord],
            list((await self._session.scalars(statement)).all()),
        )
        total = cast(int, await self._session.scalar(total_statement))

        return Page[Tag](
            items=[
                _to_domain_tag(
                    tag_record=tag_record,
                )
                for tag_record in tag_records
            ],
            offset=list_query.offset,
            limit=list_query.limit,
            total=total,
        )

    async def get_tag_by_id(
        self,
        tag_id: int,
    ) -> Tag | None:
        tag_record = await self._get_tag_record_by_id(tag_id=tag_id)

        if tag_record is None:
            return None

        return _to_domain_tag(tag_record=tag_record)

    async def get_tag_by_id_including_deleted(
        self,
        tag_id: int,
    ) -> Tag | None:
        tag_record = await self._get_tag_record_by_id(
            tag_id=tag_id,
            include_deleted=True,
        )

        if tag_record is None:
            return None

        return _to_domain_tag(tag_record=tag_record)

    async def create_tag(
        self,
        new_tag: NewTag,
    ) -> Tag:
        tag_record = TagRecord()
        tag_record.title = new_tag.title

        self._session.add(tag_record)
        await self._session.flush()
        await self._session.refresh(tag_record)

        return _to_domain_tag(tag_record=tag_record)

    async def update_tag(
        self,
        tag_id: int,
        changes: TagChanges,
    ) -> Tag:
        tag_record = await self._get_tag_record_by_id(tag_id=tag_id)

        if tag_record is None:
            raise TagNotFoundOutputPortError()

        tag_record.title = changes.title
        await self._session.flush()
        await self._session.refresh(tag_record)

        return _to_domain_tag(tag_record=tag_record)

    async def soft_delete_tag(
        self,
        tag_id: int,
    ) -> None:
        tag_record = await self._get_tag_record_by_id(tag_id=tag_id)

        if tag_record is None:
            raise TagNotFoundOutputPortError()

        tag_record.is_deleted = True
        await self._session.flush()

    async def hard_delete_tag(
        self,
        tag_id: int,
    ) -> None:
        tag_record = await self._get_tag_record_by_id(
            tag_id=tag_id,
            include_deleted=True,
        )

        if tag_record is None:
            raise TagNotFoundOutputPortError()

        await self._session.delete(tag_record)
        await self._session.flush()

    async def _get_tag_record_by_id(
        self,
        *,
        tag_id: int,
        include_deleted: bool = False,
    ) -> TagRecord | None:
        statement = select(TagRecord).where(TagRecord.id == tag_id)

        if not include_deleted:
            statement = statement.where(TagRecord.is_deleted.is_(False))

        return cast(TagRecord | None, await self._session.scalar(statement))

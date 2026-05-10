from src.core.domain.tag import (
    CreateTagData,
    NewTag,
    Tag,
    TagChanges,
    TagNotFoundError,
    UpdateTagData,
)
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.shared import ListQuery, Page


class TagUseCase(TagInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory

    async def list_tags(
        self,
        list_query: ListQuery,
    ) -> Page[Tag]:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            return await unit_of_work.tags.list_tags(
                list_query=list_query,
            )

    async def get_tag(
        self,
        tag_id: int,
    ) -> Tag:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            tag = await unit_of_work.tags.get_tag_by_id(
                tag_id=tag_id,
            )

            if tag is None:
                raise TagNotFoundError()

            return tag

    async def create_tag(
        self,
        data: CreateTagData,
    ) -> Tag:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            created_tag = await unit_of_work.tags.create_tag(
                new_tag=NewTag(
                    title=data.title,
                ),
            )

            await unit_of_work.commit()

            return created_tag

    async def update_tag(
        self,
        tag_id: int,
        data: UpdateTagData,
    ) -> Tag:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_tag = await unit_of_work.tags.get_tag_by_id(
                tag_id=tag_id,
            )

            if current_tag is None:
                raise TagNotFoundError()

            updated_tag = await unit_of_work.tags.update_tag(
                tag_id=tag_id,
                changes=TagChanges(
                    title=data.title,
                ),
            )

            await unit_of_work.commit()

            return updated_tag

    async def delete_tag(
        self,
        tag_id: int,
        hard_delete: bool = False,
    ) -> None:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            if hard_delete:
                current_tag = await unit_of_work.tags.get_tag_by_id_including_deleted(
                    tag_id=tag_id,
                )
            else:
                current_tag = await unit_of_work.tags.get_tag_by_id(
                    tag_id=tag_id,
                )

            if current_tag is None:
                raise TagNotFoundError()

            if hard_delete:
                await unit_of_work.tags.hard_delete_tag(
                    tag_id=tag_id,
                )
            else:
                await unit_of_work.tags.soft_delete_tag(
                    tag_id=tag_id,
                )

            await unit_of_work.commit()

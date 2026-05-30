from src.core.domain.tag import (
    CreateTagData,
    NewTag,
    Tag,
    TagChanges,
    TagNotFoundError,
    UpdateTagData,
)
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.output.tag_output_port import TagNotFoundOutputPortError
from src.core.ports.output.unit_of_work_output_port import UnitOfWorkOutputPortFactory
from src.core.shared import ListQuery, Page


class TagUseCase(TagInputPort):
    def __init__(
        self,
        unit_of_work_output_port_factory: UnitOfWorkOutputPortFactory,
    ) -> None:
        self._unit_of_work_output_port_factory = unit_of_work_output_port_factory

    @staticmethod
    def _to_new_tag(
        data: CreateTagData,
    ) -> NewTag:
        return NewTag(
            title=data.title,
        )

    @staticmethod
    def _to_tag_changes(
        data: UpdateTagData,
    ) -> TagChanges:
        return TagChanges(
            title=data.title,
        )

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
        new_tag = self._to_new_tag(data)

        async with self._unit_of_work_output_port_factory() as unit_of_work:
            created_tag = await unit_of_work.tags.create_tag(
                new_tag=new_tag,
            )

            await unit_of_work.commit()

            return created_tag

    async def update_tag(
        self,
        tag_id: int,
        data: UpdateTagData,
    ) -> Tag:
        changes = self._to_tag_changes(data)

        async with self._unit_of_work_output_port_factory() as unit_of_work:
            current_tag = await unit_of_work.tags.get_tag_by_id(
                tag_id=tag_id,
            )

            if current_tag is None:
                raise TagNotFoundError()

            try:
                updated_tag = await unit_of_work.tags.update_tag(
                    tag_id=tag_id,
                    changes=changes,
                )
            except TagNotFoundOutputPortError as exc:
                raise TagNotFoundError() from exc

            await unit_of_work.commit()

            return updated_tag

    async def delete_tag(
        self,
        tag_id: int,
        hard_delete: bool = False,
    ) -> None:
        async with self._unit_of_work_output_port_factory() as unit_of_work:
            tags = unit_of_work.tags
            get_tag = (
                tags.get_tag_by_id_including_deleted
                if hard_delete
                else tags.get_tag_by_id
            )
            current_tag = await get_tag(tag_id=tag_id)

            if current_tag is None:
                raise TagNotFoundError()

            try:
                if hard_delete:
                    await tags.hard_delete_tag(
                        tag_id=tag_id,
                    )
                else:
                    await tags.soft_delete_tag(
                        tag_id=tag_id,
                    )
            except TagNotFoundOutputPortError as exc:
                raise TagNotFoundError() from exc

            await unit_of_work.commit()

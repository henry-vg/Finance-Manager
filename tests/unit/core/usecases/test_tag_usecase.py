from datetime import UTC, datetime

import pytest

from src.core.domain.tag import (
    CreateTagData,
    NewTag,
    Tag,
    TagChanges,
    TagNotFoundError,
    UpdateTagData,
)
from src.core.ports.output.currency_output_port import CurrencyOutputPort
from src.core.ports.output.ledger_account_output_port import LedgerAccountOutputPort
from src.core.ports.output.tag_output_port import (
    TagNotFoundOutputPortError,
    TagOutputPort,
)
from src.core.ports.output.transaction_output_port import TransactionOutputPort
from src.core.ports.output.unit_of_work_output_port import (
    UnitOfWorkOutputPort,
    UnitOfWorkOutputPortFactory,
)
from src.core.ports.output.user_output_port import UserOutputPort
from src.core.shared import ListQuery, Page, SortDirection, SortTerm
from src.core.usecases.tag_usecase import TagUseCase


def _build_timestamp(day: int) -> datetime:
    return datetime(2026, 5, day, tzinfo=UTC)


class _TagOutputPortStub(TagOutputPort):
    def __init__(self) -> None:
        self.tags: dict[int, Tag] = {}
        self.deleted_tag_ids: set[int] = set()
        self.delete_error: Exception | None = None
        self.update_error: Exception | None = None
        self.next_id = 1

    async def list_tags(self, list_query: ListQuery) -> Page[Tag]:
        active_tags = [
            tag
            for tag_id, tag in self.tags.items()
            if tag_id not in self.deleted_tag_ids
        ]
        active_tags.sort(key=lambda tag: tag.id)
        return Page[Tag](
            items=active_tags[list_query.offset : list_query.offset + list_query.limit],
            offset=list_query.offset,
            limit=list_query.limit,
            total=len(active_tags),
        )

    async def get_tag_by_id(self, tag_id: int) -> Tag | None:
        if tag_id in self.deleted_tag_ids:
            return None
        return self.tags.get(tag_id)

    async def get_tag_by_id_including_deleted(self, tag_id: int) -> Tag | None:
        return self.tags.get(tag_id)

    async def create_tag(self, new_tag: NewTag) -> Tag:
        tag = Tag(
            id=self.next_id,
            title=new_tag.title,
            created_at=_build_timestamp(1),
            updated_at=_build_timestamp(1),
        )
        self.tags[tag.id] = tag
        self.next_id += 1
        return tag

    async def update_tag(self, tag_id: int, changes: TagChanges) -> Tag:
        if self.update_error is not None:
            raise self.update_error

        current = self.tags[tag_id]
        updated = Tag(
            id=current.id,
            title=changes.title,
            created_at=current.created_at,
            updated_at=_build_timestamp(2),
        )
        self.tags[tag_id] = updated
        return updated

    async def soft_delete_tag(self, tag_id: int) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_tag_ids.add(tag_id)

    async def hard_delete_tag(self, tag_id: int) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_tag_ids.discard(tag_id)
        self.tags.pop(tag_id, None)


class _UnitOfWorkStub(UnitOfWorkOutputPort):
    def __init__(self, tags: _TagOutputPortStub) -> None:
        self._tags = tags
        self.committed = False

    @property
    def tags(self) -> TagOutputPort:
        return self._tags

    @property
    def currencies(self) -> CurrencyOutputPort:
        raise RuntimeError("currencies output port is unused in tag tests")

    @property
    def ledger_accounts(self) -> LedgerAccountOutputPort:
        raise RuntimeError("ledger_accounts output port is unused in tag tests")

    @property
    def transactions(self) -> TransactionOutputPort:
        raise RuntimeError("transactions output port is unused in tag tests")

    @property
    def users(self) -> UserOutputPort:
        raise RuntimeError("users output port is unused in tag use case tests")

    async def __aenter__(self) -> "_UnitOfWorkStub":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        del exc_type
        del exc
        del traceback

    async def commit(self) -> None:
        self.committed = True


class _UnitOfWorkFactoryStub(UnitOfWorkOutputPortFactory):
    def __init__(self, unit_of_work: _UnitOfWorkStub) -> None:
        self._unit_of_work = unit_of_work

    def __call__(self) -> UnitOfWorkOutputPort:
        return self._unit_of_work


@pytest.mark.anyio
async def test_create_tag_returns_created_tag_and_commits() -> None:
    tags = _TagOutputPortStub()
    unit_of_work = _UnitOfWorkStub(tags)
    use_case = TagUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    result = await use_case.create_tag(CreateTagData(title="Food"))

    assert result.id == 1
    assert result.title == "Food"
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_get_tag_raises_when_tag_does_not_exist() -> None:
    tags = _TagOutputPortStub()
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    with pytest.raises(TagNotFoundError):
        await use_case.get_tag(999)


@pytest.mark.anyio
async def test_update_tag_raises_when_tag_does_not_exist() -> None:
    tags = _TagOutputPortStub()
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    with pytest.raises(TagNotFoundError):
        await use_case.update_tag(999, UpdateTagData(title="Utilities"))


@pytest.mark.anyio
async def test_update_tag_translates_output_port_not_found_to_domain_error() -> None:
    tags = _TagOutputPortStub()
    tags.tags[1] = Tag(
        id=1,
        title="Food",
        created_at=_build_timestamp(1),
        updated_at=_build_timestamp(1),
    )
    tags.update_error = TagNotFoundOutputPortError()
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    with pytest.raises(TagNotFoundError):
        await use_case.update_tag(1, UpdateTagData(title="Utilities"))


@pytest.mark.anyio
async def test_delete_tag_soft_deletes_by_default() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    unit_of_work = _UnitOfWorkStub(tags)
    use_case = TagUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    await use_case.delete_tag(created.id)

    assert created.id in tags.deleted_tag_ids
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_delete_tag_translates_output_port_not_found_to_domain_error() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    tags.delete_error = TagNotFoundOutputPortError()
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    with pytest.raises(TagNotFoundError):
        await use_case.delete_tag(created.id)


@pytest.mark.anyio
async def test_list_tags_returns_active_tags() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    await tags.create_tag(NewTag(title="Travel"))
    await tags.soft_delete_tag(created.id)
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    page = await use_case.list_tags(
        ListQuery(
            offset=0,
            limit=10,
            sort=(SortTerm(field="created_at", direction=SortDirection.ASC),),
        ),
    )

    assert [tag.title for tag in page.items] == ["Travel"]


@pytest.mark.anyio
async def test_get_tag_returns_existing_tag() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    result = await use_case.get_tag(created.id)

    assert result == created


@pytest.mark.anyio
async def test_update_tag_replaces_fields_and_commits() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    unit_of_work = _UnitOfWorkStub(tags)
    use_case = TagUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    result = await use_case.update_tag(created.id, UpdateTagData(title="Utilities"))

    assert result.title == "Utilities"
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_delete_tag_hard_deletes_when_requested() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    await tags.soft_delete_tag(created.id)
    unit_of_work = _UnitOfWorkStub(tags)
    use_case = TagUseCase(_UnitOfWorkFactoryStub(unit_of_work))

    await use_case.delete_tag(created.id, hard_delete=True)

    assert created.id not in tags.tags
    assert unit_of_work.committed is True


@pytest.mark.anyio
async def test_delete_tag_translates_output_port_not_found_on_hard_delete() -> None:
    tags = _TagOutputPortStub()
    created = await tags.create_tag(NewTag(title="Food"))
    tags.delete_error = TagNotFoundOutputPortError()
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(tags)))

    with pytest.raises(TagNotFoundError):
        await use_case.delete_tag(created.id, hard_delete=True)


@pytest.mark.anyio
async def test_delete_tag_raises_when_tag_does_not_exist() -> None:
    use_case = TagUseCase(_UnitOfWorkFactoryStub(_UnitOfWorkStub(_TagOutputPortStub())))

    with pytest.raises(TagNotFoundError):
        await use_case.delete_tag(999)

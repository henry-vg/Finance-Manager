from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.input.api.exception_translation import (
    HTTPExceptionTranslation,
    translate_exceptions_to_http,
)
from src.adapters.input.api.pagination import (
    EndpointSortField,
    ListQuerySortConfig,
    create_list_query_dependency,
)
from src.core.domain.tag import (
    CreateTagData,
    Tag,
    TagNotFoundError,
    TagSortableField,
    UpdateTagData,
)
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.shared import ListQuery, Page

from ..schemas import PageResponse
from ..schemas.tag_schema import CreateTagRequest, TagResponse, UpdateTagRequest


class TagListSortField(StrEnum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"


def _to_tag_response(
    tag: Tag,
) -> TagResponse:
    return TagResponse(
        id=tag.id,
        title=tag.title,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )


def _to_tag_page_response(
    page: Page[Tag],
) -> PageResponse[TagResponse]:
    return PageResponse[TagResponse](
        items=[
            _to_tag_response(
                tag=tag,
            )
            for tag in page.items
        ],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
    )


def create_router(
    tag_input_port: TagInputPort,
    pagination_default_limit: int,
    pagination_max_limit: int,
) -> APIRouter:
    tag_not_found_translation = HTTPExceptionTranslation(
        exception_type=TagNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Tag not found.",
    )
    list_sort_config = ListQuerySortConfig(
        fields=tuple(
            EndpointSortField(
                query_name=sort_field.value,
                item_field_name=TagSortableField[sort_field.name].name.lower(),
            )
            for sort_field in TagListSortField
        ),
        default_sort=(TagListSortField.CREATED_AT.value,),
    )
    router = APIRouter(
        prefix="/tag",
        tags=["Tag"],
    )

    @router.get(
        path="/list",
        response_model=PageResponse[TagResponse],
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to list persisted active tags with offset/limit "
            "pagination and optional sort expressions such as `title` or "
            "`-created_at`."
        ),
        responses={
            200: {
                "description": (
                    "The paginated tag collection was returned successfully."
                ),
            },
            400: {
                "description": "The pagination query parameters failed validation.",
            },
        },
        summary="List Tags",
    )
    async def list_tags(
        list_query: Annotated[
            ListQuery,
            Depends(
                create_list_query_dependency(
                    default_limit=pagination_default_limit,
                    max_limit=pagination_max_limit,
                    sort_config=list_sort_config,
                ),
            ),
        ],
    ) -> PageResponse[TagResponse]:
        page = await tag_input_port.list_tags(
            list_query=list_query,
        )

        return _to_tag_page_response(
            page=page,
        )

    @router.get(
        path="",
        response_model=TagResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to retrieve a single tag by its id.",
        responses={
            200: {
                "description": "The tag was found and returned successfully.",
            },
            404: {
                "description": "No tag exists for the provided id.",
            },
            422: {
                "description": "The required id query parameter failed validation.",
            },
        },
        summary="Get Tag",
    )
    async def get_tag(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the tag to retrieve.",
        ),
    ) -> TagResponse:
        with translate_exceptions_to_http(tag_not_found_translation):
            tag = await tag_input_port.get_tag(
                tag_id=id,
            )

        return _to_tag_response(
            tag=tag,
        )

    @router.post(
        path="",
        response_model=TagResponse,
        status_code=status.HTTP_201_CREATED,
        description="Endpoint used to create a new tag.",
        responses={
            201: {
                "description": "The tag was created successfully.",
            },
            422: {
                "description": "The request body failed validation.",
            },
        },
        summary="Create Tag",
    )
    async def create_tag(
        payload: CreateTagRequest,
    ) -> TagResponse:
        tag = await tag_input_port.create_tag(
            data=CreateTagData(
                title=payload.title,
            ),
        )

        return _to_tag_response(
            tag=tag,
        )

    @router.put(
        path="",
        response_model=TagResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to fully replace an existing tag by its id.",
        responses={
            200: {
                "description": "The tag was updated successfully.",
            },
            404: {
                "description": "No tag exists for the provided id.",
            },
            422: {
                "description": (
                    "The request payload or query parameters failed validation."
                ),
            },
        },
        summary="Update Tag",
    )
    async def update_tag(
        payload: UpdateTagRequest,
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the tag to update.",
        ),
    ) -> TagResponse:
        with translate_exceptions_to_http(tag_not_found_translation):
            tag = await tag_input_port.update_tag(
                tag_id=id,
                data=UpdateTagData(
                    title=payload.title,
                ),
            )

        return _to_tag_response(tag=tag)

    @router.delete(
        path="",
        status_code=status.HTTP_204_NO_CONTENT,
        description="Endpoint used to delete an existing tag by its id.",
        responses={
            204: {
                "description": "The tag was deleted successfully.",
            },
            404: {
                "description": "No tag exists for the provided id.",
            },
            422: {
                "description": "The query parameters failed validation.",
            },
        },
        summary="Delete Tag",
    )
    async def delete_tag(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the tag to delete.",
        ),
        hard_delete: bool = Query(
            False,
            description=(
                "When true, permanently deletes the tag instead of soft deleting it."
            ),
        ),
    ) -> None:
        with translate_exceptions_to_http(tag_not_found_translation):
            await tag_input_port.delete_tag(
                tag_id=id,
                hard_delete=hard_delete,
            )

    return router

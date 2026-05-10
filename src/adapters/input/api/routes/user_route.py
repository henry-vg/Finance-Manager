from enum import StrEnum
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)

from src.adapters.input.api.exception_translation import (
    HTTPExceptionTranslation,
    translate_exceptions_to_http,
)
from src.adapters.input.api.pagination import (
    EndpointSortField,
    ListQuerySortConfig,
    create_list_query_dependency,
)
from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
    UserEmailConflictError,
    UserNotFoundError,
    UserSortableField,
)
from src.core.ports.input.user_input_port import UserInputPort
from src.core.shared import ListQuery, Page

from ..schemas import PageResponse
from ..schemas.user_schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)


class UserListSortField(StrEnum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    EMAIL = "email"
    BIRTH_DATE = "birth_date"


def _to_user_response(
    user: User,
) -> UserResponse:
    return UserResponse(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        birth_date=user.birth_date,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _to_user_page_response(
    page: Page[User],
) -> PageResponse[UserResponse]:
    return PageResponse[UserResponse](
        items=[
            _to_user_response(
                user=user,
            )
            for user in page.items
        ],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
    )


def create_router(
    user_input_port: UserInputPort,
    pagination_default_limit: int,
    pagination_max_limit: int,
) -> APIRouter:
    user_not_found_translation = HTTPExceptionTranslation(
        exception_type=UserNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found.",
    )
    user_email_conflict_translation = HTTPExceptionTranslation(
        exception_type=UserEmailConflictError,
        status_code=status.HTTP_409_CONFLICT,
        detail="User email already exists.",
    )
    list_sort_config = ListQuerySortConfig(
        fields=tuple(
            EndpointSortField(
                query_name=sort_field.value,
                item_field_name=UserSortableField[sort_field.name].name.lower(),
            )
            for sort_field in UserListSortField
        ),
        default_sort=(UserListSortField.CREATED_AT.value,),
    )

    router = APIRouter(
        prefix="/user",
        tags=["User"],
    )

    @router.get(
        path="/list",
        response_model=PageResponse[UserResponse],
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to list persisted active users with offset/limit "
            "pagination and optional sort expressions such as `email` or "
            "`-created_at`. Soft-deleted users are excluded, and the response "
            "returns items together with offset, limit and total."
        ),
        responses={
            200: {
                "description": (
                    "The paginated user collection was returned successfully."
                ),
            },
            400: {
                "description": "The pagination query parameters failed validation.",
            },
        },
        summary="List Users",
    )
    async def list_users(
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
    ) -> PageResponse[UserResponse]:
        page = await user_input_port.list_users(
            list_query=list_query,
        )

        return _to_user_page_response(
            page=page,
        )

    @router.get(
        path="",
        response_model=UserResponse,
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to retrieve a single user by its email address. "
            "Returns the persisted user data, including audit timestamps, "
            "without exposing password information."
        ),
        responses={
            200: {
                "description": "The user was found and returned successfully.",
            },
            404: {
                "description": "No user exists for the provided email address.",
            },
            422: {
                "description": "The required email query parameter failed validation.",
            },
        },
        summary="Get User",
    )
    async def get_user(
        email: str = Query(
            ...,
            description="Email address of the user to retrieve.",
        ),
    ) -> UserResponse:
        with translate_exceptions_to_http(user_not_found_translation):
            user = await user_input_port.get_user(
                email=email,
            )

        return _to_user_response(
            user=user,
        )

    @router.post(
        path="",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
        description=(
            "Endpoint used to create a new user. The password received in the "
            "request is hashed before persistence, and the response returns the "
            "created user without any password fields."
        ),
        responses={
            201: {
                "description": "The user was created successfully.",
            },
            409: {
                "description": "A user with the same email address already exists.",
            },
            422: {
                "description": "The request body failed validation.",
            },
        },
        summary="Create User",
    )
    async def create_user(
        payload: CreateUserRequest,
    ) -> UserResponse:
        with translate_exceptions_to_http(user_email_conflict_translation):
            user = await user_input_port.create_user(
                data=CreateUserData(
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    email=payload.email,
                    password=payload.password,
                    birth_date=payload.birth_date,
                ),
            )

        return _to_user_response(
            user=user,
        )

    @router.put(
        path="",
        response_model=UserResponse,
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to fully replace an existing user by its current email. "
            "The update refreshes the audit timestamp and returns the updated "
            "representation without password fields."
        ),
        responses={
            200: {
                "description": "The user was updated successfully.",
            },
            404: {
                "description": "No user exists for the provided current email.",
            },
            409: {
                "description": "A different user already uses the provided email.",
            },
            422: {
                "description": (
                    "The request payload or query parameters failed validation."
                ),
            },
        },
        summary="Update User",
    )
    async def update_user(
        payload: UpdateUserRequest,
        current_email: str = Query(
            ...,
            description="Current email address of the user to update.",
        ),
    ) -> UserResponse:
        with translate_exceptions_to_http(
            user_not_found_translation,
            user_email_conflict_translation,
        ):
            user = await user_input_port.update_user(
                current_email=current_email,
                data=UpdateUserData(
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    email=payload.email,
                    password=payload.password,
                    birth_date=payload.birth_date,
                ),
            )

        return _to_user_response(
            user=user,
        )

    @router.delete(
        path="",
        status_code=status.HTTP_204_NO_CONTENT,
        description=(
            "Endpoint used to delete an existing user by its email address. "
            "By default the operation performs a soft delete; when "
            "`hard_delete=true` is provided, the persisted row is removed "
            "physically. On success, the operation returns no response body."
        ),
        responses={
            204: {
                "description": (
                    "The user was deleted successfully, either logically or "
                    "physically depending on the hard_delete query parameter."
                ),
            },
            404: {
                "description": "No user exists for the provided email address.",
            },
            422: {
                "description": "The required email query parameter failed validation.",
            },
        },
        summary="Delete User",
    )
    async def delete_user(
        email: str = Query(
            ...,
            description="Email address of the user to delete.",
        ),
        hard_delete: bool = Query(
            False,
            description=(
                "When true, removes the row physically. When false, performs "
                "a soft delete. Defaults to false."
            ),
        ),
    ) -> Response:
        with translate_exceptions_to_http(user_not_found_translation):
            await user_input_port.delete_user(
                email=email,
                hard_delete=hard_delete,
            )

        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
        )

    return router

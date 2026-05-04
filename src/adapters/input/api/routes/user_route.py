from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    status,
)

from src.core.domain.user import (
    CreateUserData,
    UpdateUserData,
    User,
    UserEmailConflictError,
    UserNotFoundError,
)
from src.core.ports.input.user_input_port import UserInputPort

from ..schemas.user_schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)


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


def create_router(
    user_input_port: UserInputPort,
) -> APIRouter:
    router = APIRouter(
        prefix="/user",
        tags=["User"],
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
        try:
            user = await user_input_port.get_user(
                email=email,
            )
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            ) from exc

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
        try:
            user = await user_input_port.create_user(
                data=CreateUserData(
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    email=payload.email,
                    password=payload.password,
                    birth_date=payload.birth_date,
                ),
            )
        except UserEmailConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User email already exists.",
            ) from exc

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
        try:
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
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            ) from exc
        except UserEmailConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User email already exists.",
            ) from exc

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
        try:
            await user_input_port.delete_user(
                email=email,
                hard_delete=hard_delete,
            )
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            ) from exc

        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
        )

    return router

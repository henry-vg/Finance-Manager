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
from src.core.domain.ledger_account import (
    CreateLedgerAccountData,
    Currency,
    LedgerAccount,
    LedgerAccountKind,
    LedgerAccountNotFoundError,
    LedgerAccountSortableField,
    LedgerAccountType,
    UpdateLedgerAccountData,
)
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.shared import ListQuery, Page

from ..schemas import PageResponse
from ..schemas.ledger_account_schema import (
    CreateLedgerAccountRequest,
    CurrencySchema,
    LedgerAccountKindSchema,
    LedgerAccountResponse,
    LedgerAccountTypeSchema,
    UpdateLedgerAccountRequest,
)


class LedgerAccountListSortField(StrEnum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"
    TYPE = "type"
    KIND = "kind"
    CURRENCY = "currency"


def _to_ledger_account_response(
    ledger_account: LedgerAccount,
) -> LedgerAccountResponse:
    return LedgerAccountResponse(
        id=ledger_account.id,
        title=ledger_account.title,
        type=LedgerAccountTypeSchema[ledger_account.type.name],
        kind=LedgerAccountKindSchema[ledger_account.kind.name],
        currency=CurrencySchema[ledger_account.currency.name],
        created_at=ledger_account.created_at,
        updated_at=ledger_account.updated_at,
    )


def _to_ledger_account_page_response(
    page: Page[LedgerAccount],
) -> PageResponse[LedgerAccountResponse]:
    return PageResponse[LedgerAccountResponse](
        items=[
            _to_ledger_account_response(
                ledger_account=ledger_account,
            )
            for ledger_account in page.items
        ],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
    )


def create_router(
    ledger_account_input_port: LedgerAccountInputPort,
    pagination_default_limit: int,
    pagination_max_limit: int,
) -> APIRouter:
    ledger_account_not_found_translation = HTTPExceptionTranslation(
        exception_type=LedgerAccountNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Ledger account not found.",
    )
    list_sort_config = ListQuerySortConfig(
        fields=tuple(
            EndpointSortField(
                query_name=sort_field.value,
                item_field_name=LedgerAccountSortableField[
                    sort_field.name
                ].name.lower(),
            )
            for sort_field in LedgerAccountListSortField
        ),
        default_sort=(LedgerAccountListSortField.CREATED_AT.value,),
    )
    router = APIRouter(
        prefix="/ledger-account",
        tags=["LedgerAccount"],
    )

    @router.get(
        path="/list",
        response_model=PageResponse[LedgerAccountResponse],
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to list persisted active ledger accounts with "
            "offset/limit pagination and optional sort expressions such as "
            "`title` or `-created_at`."
        ),
        responses={
            200: {
                "description": (
                    "The paginated ledger account collection was returned successfully."
                ),
            },
            400: {
                "description": "The pagination query parameters failed validation.",
            },
        },
        summary="List Ledger Accounts",
    )
    async def list_ledger_accounts(
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
    ) -> PageResponse[LedgerAccountResponse]:
        page = await ledger_account_input_port.list_ledger_accounts(
            list_query=list_query,
        )

        return _to_ledger_account_page_response(page=page)

    @router.get(
        path="",
        response_model=LedgerAccountResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to retrieve a single ledger account by its id.",
        responses={
            200: {
                "description": (
                    "The ledger account was found and returned successfully."
                ),
            },
            404: {
                "description": "No ledger account exists for the provided id.",
            },
            422: {
                "description": "The required id query parameter failed validation.",
            },
        },
        summary="Get Ledger Account",
    )
    async def get_ledger_account(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the ledger account to retrieve.",
        ),
    ) -> LedgerAccountResponse:
        with translate_exceptions_to_http(ledger_account_not_found_translation):
            ledger_account = await ledger_account_input_port.get_ledger_account(
                ledger_account_id=id,
            )

        return _to_ledger_account_response(ledger_account=ledger_account)

    @router.post(
        path="",
        response_model=LedgerAccountResponse,
        status_code=status.HTTP_201_CREATED,
        description="Endpoint used to create a new ledger account.",
        responses={
            201: {
                "description": "The ledger account was created successfully.",
            },
            422: {
                "description": "The request body failed validation.",
            },
        },
        summary="Create Ledger Account",
    )
    async def create_ledger_account(
        payload: CreateLedgerAccountRequest,
    ) -> LedgerAccountResponse:
        ledger_account = await ledger_account_input_port.create_ledger_account(
            data=CreateLedgerAccountData(
                title=payload.title,
                type=LedgerAccountType[payload.type.name],
                kind=LedgerAccountKind[payload.kind.name],
                currency=Currency[payload.currency.name],
            ),
        )

        return _to_ledger_account_response(ledger_account=ledger_account)

    @router.put(
        path="",
        response_model=LedgerAccountResponse,
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to fully replace an existing ledger account by its id."
        ),
        responses={
            200: {
                "description": "The ledger account was updated successfully.",
            },
            404: {
                "description": "No ledger account exists for the provided id.",
            },
            422: {
                "description": (
                    "The request payload or query parameters failed validation."
                ),
            },
        },
        summary="Update Ledger Account",
    )
    async def update_ledger_account(
        payload: UpdateLedgerAccountRequest,
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the ledger account to update.",
        ),
    ) -> LedgerAccountResponse:
        with translate_exceptions_to_http(ledger_account_not_found_translation):
            ledger_account = await ledger_account_input_port.update_ledger_account(
                ledger_account_id=id,
                data=UpdateLedgerAccountData(
                    title=payload.title,
                    type=LedgerAccountType[payload.type.name],
                    kind=LedgerAccountKind[payload.kind.name],
                    currency=Currency[payload.currency.name],
                ),
            )

        return _to_ledger_account_response(ledger_account=ledger_account)

    @router.delete(
        path="",
        status_code=status.HTTP_204_NO_CONTENT,
        description="Endpoint used to delete an existing ledger account by its id.",
        responses={
            204: {
                "description": "The ledger account was deleted successfully.",
            },
            404: {
                "description": "No ledger account exists for the provided id.",
            },
            422: {
                "description": "The query parameters failed validation.",
            },
        },
        summary="Delete Ledger Account",
    )
    async def delete_ledger_account(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the ledger account to delete.",
        ),
        hard_delete: bool = Query(
            False,
            description=(
                "When true, permanently deletes the ledger account instead "
                "of soft deleting it."
            ),
        ),
    ) -> None:
        with translate_exceptions_to_http(ledger_account_not_found_translation):
            await ledger_account_input_port.delete_ledger_account(
                ledger_account_id=id,
                hard_delete=hard_delete,
            )

    return router

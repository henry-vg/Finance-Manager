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
from src.core.domain.ledger_account import LedgerAccountNotFoundError
from src.core.domain.statement_cycle import (
    CreateStatementCycleData,
    StatementCycle,
    StatementCycleLedgerAccountInvalidError,
    StatementCycleNotFoundError,
    StatementCycleSortableField,
    UpdateStatementCycleData,
)
from src.core.ports.input.statement_cycle_input_port import StatementCycleInputPort
from src.core.shared import ListQuery, Page

from ..schemas import PageResponse
from ..schemas.statement_cycle_schema import (
    CreateStatementCycleRequest,
    StatementCycleResponse,
    UpdateStatementCycleRequest,
)


class StatementCycleListSortField(StrEnum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    LEDGER_ACCOUNT_ID = "ledger_account_id"
    CYCLE_START = "cycle_start"
    CYCLE_END = "cycle_end"
    CLOSING_DATE = "closing_date"
    DUE_DATE = "due_date"


def _to_statement_cycle_response(
    statement_cycle: StatementCycle,
) -> StatementCycleResponse:
    return StatementCycleResponse(
        id=statement_cycle.id,
        ledger_account_id=statement_cycle.ledger_account_id,
        cycle_start=statement_cycle.cycle_start,
        cycle_end=statement_cycle.cycle_end,
        closing_date=statement_cycle.closing_date,
        due_date=statement_cycle.due_date,
        created_at=statement_cycle.created_at,
        updated_at=statement_cycle.updated_at,
    )


def _to_statement_cycle_page_response(
    page: Page[StatementCycle],
) -> PageResponse[StatementCycleResponse]:
    return PageResponse[StatementCycleResponse](
        items=[
            _to_statement_cycle_response(
                statement_cycle=statement_cycle,
            )
            for statement_cycle in page.items
        ],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
    )


def create_router(
    statement_cycle_input_port: StatementCycleInputPort,
    pagination_default_limit: int,
    pagination_max_limit: int,
) -> APIRouter:
    statement_cycle_not_found_translation = HTTPExceptionTranslation(
        exception_type=StatementCycleNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Statement cycle not found.",
    )
    ledger_account_not_found_translation = HTTPExceptionTranslation(
        exception_type=LedgerAccountNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Ledger account not found.",
    )
    invalid_ledger_account_translation = HTTPExceptionTranslation(
        exception_type=StatementCycleLedgerAccountInvalidError,
        status_code=status.HTTP_409_CONFLICT,
        detail="Statement cycle ledger account must be a liability credit card.",
    )
    list_sort_config = ListQuerySortConfig(
        fields=tuple(
            EndpointSortField(
                query_name=sort_field.value,
                item_field_name=StatementCycleSortableField[
                    sort_field.name
                ].name.lower(),
            )
            for sort_field in StatementCycleListSortField
        ),
        default_sort=(StatementCycleListSortField.CREATED_AT.value,),
    )
    router = APIRouter(
        prefix="/statement-cycle",
        tags=["StatementCycle"],
    )

    @router.get(
        path="/list",
        response_model=PageResponse[StatementCycleResponse],
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to list persisted active statement cycles with "
            "offset/limit pagination and optional sort expressions such as "
            "`cycle_start` or `-created_at`."
        ),
        responses={
            200: {
                "description": (
                    "The paginated statement cycle collection was returned "
                    "successfully."
                ),
            },
            400: {
                "description": "The pagination query parameters failed validation.",
            },
        },
        summary="List Statement Cycles",
    )
    async def list_statement_cycles(
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
    ) -> PageResponse[StatementCycleResponse]:
        page = await statement_cycle_input_port.list_statement_cycles(
            list_query=list_query,
        )

        return _to_statement_cycle_page_response(page=page)

    @router.get(
        path="",
        response_model=StatementCycleResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to retrieve a single statement cycle by its id.",
        responses={
            200: {
                "description": (
                    "The statement cycle was found and returned successfully."
                ),
            },
            404: {
                "description": "No statement cycle exists for the provided id.",
            },
            422: {
                "description": "The required id query parameter failed validation.",
            },
        },
        summary="Get Statement Cycle",
    )
    async def get_statement_cycle(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the statement cycle to retrieve.",
        ),
    ) -> StatementCycleResponse:
        with translate_exceptions_to_http(statement_cycle_not_found_translation):
            statement_cycle = await statement_cycle_input_port.get_statement_cycle(
                statement_cycle_id=id,
            )

        return _to_statement_cycle_response(statement_cycle=statement_cycle)

    @router.post(
        path="",
        response_model=StatementCycleResponse,
        status_code=status.HTTP_201_CREATED,
        description="Endpoint used to create a new statement cycle.",
        responses={
            201: {
                "description": "The statement cycle was created successfully.",
            },
            404: {
                "description": "No ledger account exists for the provided id.",
            },
            409: {
                "description": (
                    "The referenced ledger account is not a liability credit card."
                ),
            },
            422: {
                "description": "The request body failed validation.",
            },
        },
        summary="Create Statement Cycle",
    )
    async def create_statement_cycle(
        payload: CreateStatementCycleRequest,
    ) -> StatementCycleResponse:
        with translate_exceptions_to_http(
            ledger_account_not_found_translation,
            invalid_ledger_account_translation,
        ):
            statement_cycle = await statement_cycle_input_port.create_statement_cycle(
                data=CreateStatementCycleData(
                    ledger_account_id=payload.ledger_account_id,
                    cycle_start=payload.cycle_start,
                    cycle_end=payload.cycle_end,
                    closing_date=payload.closing_date,
                    due_date=payload.due_date,
                ),
            )

        return _to_statement_cycle_response(statement_cycle=statement_cycle)

    @router.put(
        path="",
        response_model=StatementCycleResponse,
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to fully replace an existing statement cycle by its id."
        ),
        responses={
            200: {
                "description": "The statement cycle was updated successfully.",
            },
            404: {
                "description": (
                    "The statement cycle or referenced ledger account was not found."
                ),
            },
            409: {
                "description": (
                    "The referenced ledger account is not a liability credit card."
                ),
            },
            422: {
                "description": (
                    "The request payload or query parameters failed validation."
                ),
            },
        },
        summary="Update Statement Cycle",
    )
    async def update_statement_cycle(
        payload: UpdateStatementCycleRequest,
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the statement cycle to update.",
        ),
    ) -> StatementCycleResponse:
        with translate_exceptions_to_http(
            statement_cycle_not_found_translation,
            ledger_account_not_found_translation,
            invalid_ledger_account_translation,
        ):
            statement_cycle = await statement_cycle_input_port.update_statement_cycle(
                statement_cycle_id=id,
                data=UpdateStatementCycleData(
                    ledger_account_id=payload.ledger_account_id,
                    cycle_start=payload.cycle_start,
                    cycle_end=payload.cycle_end,
                    closing_date=payload.closing_date,
                    due_date=payload.due_date,
                ),
            )

        return _to_statement_cycle_response(statement_cycle=statement_cycle)

    @router.delete(
        path="",
        status_code=status.HTTP_204_NO_CONTENT,
        description="Endpoint used to delete an existing statement cycle by its id.",
        responses={
            204: {
                "description": "The statement cycle was deleted successfully.",
            },
            404: {
                "description": "No statement cycle exists for the provided id.",
            },
            422: {
                "description": "The query parameters failed validation.",
            },
        },
        summary="Delete Statement Cycle",
    )
    async def delete_statement_cycle(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the statement cycle to delete.",
        ),
        hard_delete: bool = Query(
            False,
            description=(
                "When true, permanently deletes the statement cycle instead "
                "of soft deleting it."
            ),
        ),
    ) -> None:
        with translate_exceptions_to_http(statement_cycle_not_found_translation):
            await statement_cycle_input_port.delete_statement_cycle(
                statement_cycle_id=id,
                hard_delete=hard_delete,
            )

    return router

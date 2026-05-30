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
from src.core.domain.currency import (
    CreateCurrencyData,
    Currency,
    CurrencyDataValidationError,
    CurrencyISOCodeConflictError,
    CurrencyNotFoundError,
    CurrencySortableField,
    UpdateCurrencyData,
)
from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.shared import ListQuery, Page

from ..schemas import PageResponse
from ..schemas.currency_schema import (
    CreateCurrencyRequest,
    CurrencyResponse,
    UpdateCurrencyRequest,
)


class CurrencyListSortField(StrEnum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    ISO_CODE = "iso_code"
    ISO_NUMERIC = "iso_numeric"
    NAME = "name"
    SYMBOL = "symbol"
    DECIMAL_PLACES = "decimal_places"


def _to_currency_response(
    currency: Currency,
) -> CurrencyResponse:
    return CurrencyResponse(
        id=currency.id,
        created_at=currency.created_at,
        updated_at=currency.updated_at,
        iso_code=currency.iso_code,
        iso_numeric=currency.iso_numeric,
        name=currency.name,
        symbol=currency.symbol,
        decimal_places=currency.decimal_places,
        storage_decimal_places=currency.storage_decimal_places,
    )


def _to_currency_page_response(
    page: Page[Currency],
) -> PageResponse[CurrencyResponse]:
    return PageResponse[CurrencyResponse](
        items=[_to_currency_response(currency=currency) for currency in page.items],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
    )


def create_router(
    currency_input_port: CurrencyInputPort,
    pagination_default_limit: int,
    pagination_max_limit: int,
) -> APIRouter:
    currency_not_found_translation = HTTPExceptionTranslation(
        exception_type=CurrencyNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Currency not found.",
    )
    currency_iso_code_conflict_translation = HTTPExceptionTranslation(
        exception_type=CurrencyISOCodeConflictError,
        status_code=status.HTTP_409_CONFLICT,
        detail="Currency ISO code already exists.",
    )
    currency_data_validation_translation = HTTPExceptionTranslation(
        exception_type=CurrencyDataValidationError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Currency data is invalid.",
    )
    list_sort_config = ListQuerySortConfig(
        fields=tuple(
            EndpointSortField(
                query_name=sort_field.value,
                item_field_name=CurrencySortableField[sort_field.name].name.lower(),
            )
            for sort_field in CurrencyListSortField
        ),
        default_sort=(CurrencyListSortField.CREATED_AT.value,),
    )
    router = APIRouter(prefix="/currency", tags=["Currency"])

    @router.get(
        path="/list",
        response_model=PageResponse[CurrencyResponse],
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to list persisted active currencies with offset/limit "
            "pagination and optional sort expressions such as `iso_code` or "
            "`-created_at`."
        ),
        responses={
            200: {
                "description": (
                    "The paginated currency collection was returned successfully."
                ),
            },
            400: {
                "description": "The pagination query parameters failed validation.",
            },
        },
        summary="List Currencies",
    )
    async def list_currencies(
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
    ) -> PageResponse[CurrencyResponse]:
        page = await currency_input_port.list_currencies(list_query=list_query)
        return _to_currency_page_response(page=page)

    @router.get(
        path="",
        response_model=CurrencyResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to retrieve a single currency by its id.",
        responses={
            200: {
                "description": "The currency was found and returned successfully.",
            },
            404: {
                "description": "No currency exists for the provided id.",
            },
            422: {
                "description": "The required id query parameter failed validation.",
            },
        },
        summary="Get Currency",
    )
    async def get_currency(
        id: int = Query(..., ge=1, description="Identifier of the currency."),
    ) -> CurrencyResponse:
        with translate_exceptions_to_http(currency_not_found_translation):
            currency = await currency_input_port.get_currency(currency_id=id)

        return _to_currency_response(currency=currency)

    @router.post(
        path="",
        response_model=CurrencyResponse,
        status_code=status.HTTP_201_CREATED,
        description="Endpoint used to create a new currency.",
        responses={
            201: {
                "description": "The currency was created successfully.",
            },
            409: {
                "description": "A currency with the same ISO code already exists.",
            },
            422: {
                "description": "The request body failed validation.",
            },
        },
        summary="Create Currency",
    )
    async def create_currency(
        payload: CreateCurrencyRequest,
    ) -> CurrencyResponse:
        with translate_exceptions_to_http(
            currency_data_validation_translation,
            currency_iso_code_conflict_translation,
        ):
            currency = await currency_input_port.create_currency(
                data=CreateCurrencyData(
                    iso_code=payload.iso_code,
                    iso_numeric=payload.iso_numeric,
                    name=payload.name,
                    symbol=payload.symbol,
                    decimal_places=payload.decimal_places,
                ),
            )

        return _to_currency_response(currency=currency)

    @router.put(
        path="",
        response_model=CurrencyResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to fully replace an existing currency by its id.",
        responses={
            200: {
                "description": "The currency was updated successfully.",
            },
            404: {
                "description": "No currency exists for the provided id.",
            },
            409: {
                "description": "A different currency already uses the same ISO code.",
            },
            422: {
                "description": (
                    "- The request payload failed validation.\n"
                    "- The query parameters failed validation."
                ),
            },
        },
        summary="Update Currency",
    )
    async def update_currency(
        payload: UpdateCurrencyRequest,
        id: int = Query(..., ge=1, description="Identifier of the currency."),
    ) -> CurrencyResponse:
        with translate_exceptions_to_http(
            currency_data_validation_translation,
            currency_not_found_translation,
            currency_iso_code_conflict_translation,
        ):
            currency = await currency_input_port.update_currency(
                currency_id=id,
                data=UpdateCurrencyData(
                    iso_code=payload.iso_code,
                    iso_numeric=payload.iso_numeric,
                    name=payload.name,
                    symbol=payload.symbol,
                    decimal_places=payload.decimal_places,
                ),
            )

        return _to_currency_response(currency=currency)

    @router.delete(
        path="",
        status_code=status.HTTP_204_NO_CONTENT,
        description="Endpoint used to delete an existing currency by its id.",
        responses={
            204: {
                "description": (
                    "- The currency was soft-deleted when `hard_delete=false`.\n"
                    "- The currency was permanently deleted when `hard_delete=true`."
                ),
            },
            404: {
                "description": "No currency exists for the provided id.",
            },
            422: {
                "description": "The query parameters failed validation.",
            },
        },
        summary="Delete Currency",
    )
    async def delete_currency(
        id: int = Query(..., ge=1, description="Identifier of the currency."),
        hard_delete: bool = Query(
            False,
            description=(
                "When true, permanently deletes the currency instead of soft "
                "deleting it."
            ),
        ),
    ) -> None:
        with translate_exceptions_to_http(currency_not_found_translation):
            await currency_input_port.delete_currency(
                currency_id=id,
                hard_delete=hard_delete,
            )

    return router

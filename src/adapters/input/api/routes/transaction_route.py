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
from src.core.domain.transaction import (
    CreateTransactionData,
    Entry,
    EntryTag,
    EntryWithTags,
    NewEntry,
    NewEntryTag,
    Transaction,
    TransactionEntriesMustBalanceError,
    TransactionEntryCurrencyNotFoundError,
    TransactionEntryExchangeRateUnavailableError,
    TransactionEntryRequiresCreditCardLedgerAccountError,
    TransactionEntryStatementDatesMustBeProvidedTogetherError,
    TransactionEntryStatementDueDateMustBeAfterClosingDateError,
    TransactionEntryTagsMustBeUniqueError,
    TransactionLedgerAccountNotFoundError,
    TransactionMustBePendingError,
    TransactionMustHaveAtLeastTwoEntriesError,
    TransactionNotFoundError,
    TransactionSortableField,
    TransactionStatus,
    TransactionStatusTransitionNotAllowedError,
    TransactionTagNotFoundError,
    TransactionWithEntries,
    UpdateTransactionData,
)
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.shared import ListQuery, Page

from ..schemas import PageResponse
from ..schemas.transaction_schema import (
    CreateTransactionRequest,
    TransactionEntryRequest,
    TransactionEntryResponse,
    TransactionEntryTagResponse,
    TransactionEntryWithTagsResponse,
    TransactionResponse,
    TransactionStatusSchema,
    TransactionSummaryResponse,
    UpdateTransactionRequest,
)


class TransactionListSortField(StrEnum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    EFFECTIVE_AT = "effective_at"
    TITLE = "title"
    STATUS = "status"


def _to_new_entry_tags(
    entry_request: TransactionEntryRequest,
) -> tuple[NewEntryTag, ...]:
    return tuple(
        NewEntryTag(tag_id=entry_tag_item.tag_id)
        for entry_tag_item in entry_request.entry_tags
    )


def _to_new_entry(
    entry: TransactionEntryRequest,
) -> NewEntry:
    return NewEntry(
        ledger_account_id=entry.ledger_account_id,
        amount=entry.amount,
        amount_in_dollars=None,
        currency_id=entry.currency_id,
        statement_closing_date=entry.statement_closing_date,
        statement_due_date=entry.statement_due_date,
        entry_tags=_to_new_entry_tags(entry),
    )


def _to_transaction_status_schema(
    status_value: TransactionStatus,
) -> TransactionStatusSchema:
    return TransactionStatusSchema[status_value.name]


def _to_transaction_entry_tag_response(
    entry_tag: EntryTag,
) -> TransactionEntryTagResponse:
    return TransactionEntryTagResponse(
        entry_id=entry_tag.entry_id,
        tag_id=entry_tag.tag_id,
    )


def _to_transaction_entry_response(
    entry: Entry,
) -> TransactionEntryResponse:
    return TransactionEntryResponse(
        id=entry.id,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        transaction_id=entry.transaction_id,
        ledger_account_id=entry.ledger_account_id,
        amount_in_dollars=entry.amount_in_dollars,
        currency_id=entry.currency_id,
        planned_exchange_rate_to_dollars=entry.planned_exchange_rate_to_dollars,
        posting_exchange_rate_to_dollars=entry.posting_exchange_rate_to_dollars,
        statement_closing_date=entry.statement_closing_date,
        statement_due_date=entry.statement_due_date,
    )


def _to_transaction_entry_with_tags_response(
    entry_with_tags: EntryWithTags,
) -> TransactionEntryWithTagsResponse:
    return TransactionEntryWithTagsResponse(
        entry=_to_transaction_entry_response(entry_with_tags.entry),
        entry_tags=tuple(
            _to_transaction_entry_tag_response(entry_tag)
            for entry_tag in entry_with_tags.entry_tags
        ),
    )


def _to_transaction_response(
    transaction_with_entries: TransactionWithEntries,
) -> TransactionResponse:
    transaction: Transaction = transaction_with_entries.transaction
    return TransactionResponse(
        id=transaction.id,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        effective_at=transaction.effective_at,
        title=transaction.title,
        description=transaction.description,
        status=_to_transaction_status_schema(transaction.status),
        entries=tuple(
            _to_transaction_entry_with_tags_response(entry_with_tags)
            for entry_with_tags in transaction_with_entries.entries
        ),
    )


def _to_transaction_summary_response(
    transaction: Transaction,
) -> TransactionSummaryResponse:
    return TransactionSummaryResponse(
        id=transaction.id,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        effective_at=transaction.effective_at,
        title=transaction.title,
        description=transaction.description,
        status=_to_transaction_status_schema(transaction.status),
    )


def _to_transaction_page_response(
    page: Page[Transaction],
) -> PageResponse[TransactionSummaryResponse]:
    return PageResponse[TransactionSummaryResponse](
        items=[
            _to_transaction_summary_response(
                transaction=transaction,
            )
            for transaction in page.items
        ],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
    )


def create_router(
    transaction_input_port: TransactionInputPort,
    pagination_default_limit: int,
    pagination_max_limit: int,
) -> APIRouter:
    transaction_not_found_translation = HTTPExceptionTranslation(
        exception_type=TransactionNotFoundError,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Transaction not found.",
    )
    transaction_must_be_pending_translation = HTTPExceptionTranslation(
        exception_type=TransactionMustBePendingError,
        status_code=status.HTTP_409_CONFLICT,
        detail="Transaction must be pending.",
    )
    transaction_status_transition_not_allowed_translation = HTTPExceptionTranslation(
        exception_type=TransactionStatusTransitionNotAllowedError,
        status_code=status.HTTP_409_CONFLICT,
        detail="Transaction status transition is not allowed.",
    )
    transaction_must_have_at_least_two_entries_translation = HTTPExceptionTranslation(
        exception_type=TransactionMustHaveAtLeastTwoEntriesError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction must have at least two entries.",
    )
    transaction_entries_must_balance_translation = HTTPExceptionTranslation(
        exception_type=TransactionEntriesMustBalanceError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction entries must balance to zero.",
    )
    transaction_ledger_account_not_found_translation = HTTPExceptionTranslation(
        exception_type=TransactionLedgerAccountNotFoundError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction ledger account was not found.",
    )
    transaction_entry_currency_not_found_translation = HTTPExceptionTranslation(
        exception_type=TransactionEntryCurrencyNotFoundError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction entry currency was not found.",
    )
    transaction_entry_exchange_rate_unavailable_translation = HTTPExceptionTranslation(
        exception_type=TransactionEntryExchangeRateUnavailableError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction entry exchange rate is unavailable.",
    )
    transaction_tag_not_found_translation = HTTPExceptionTranslation(
        exception_type=TransactionTagNotFoundError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction tag was not found.",
    )
    transaction_entry_tags_must_be_unique_translation = HTTPExceptionTranslation(
        exception_type=TransactionEntryTagsMustBeUniqueError,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Transaction entry tags must be unique.",
    )
    transaction_entry_statement_dates_must_be_provided_together_translation = (
        HTTPExceptionTranslation(
            exception_type=TransactionEntryStatementDatesMustBeProvidedTogetherError,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Transaction statement closing and due dates must be provided together."
            ),
        )
    )
    transaction_entry_requires_credit_card_ledger_account_translation = (
        HTTPExceptionTranslation(
            exception_type=TransactionEntryRequiresCreditCardLedgerAccountError,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Transaction statement entries require a credit card ledger account."
            ),
        )
    )
    transaction_entry_statement_due_date_after_closing_date_translation = (
        HTTPExceptionTranslation(
            exception_type=TransactionEntryStatementDueDateMustBeAfterClosingDateError,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Transaction statement due date must be after closing date.",
        )
    )
    transaction_write_translations = (
        transaction_must_have_at_least_two_entries_translation,
        transaction_entries_must_balance_translation,
        transaction_ledger_account_not_found_translation,
        transaction_entry_currency_not_found_translation,
        transaction_entry_exchange_rate_unavailable_translation,
        transaction_tag_not_found_translation,
        transaction_entry_tags_must_be_unique_translation,
        transaction_entry_statement_dates_must_be_provided_together_translation,
        transaction_entry_requires_credit_card_ledger_account_translation,
        transaction_entry_statement_due_date_after_closing_date_translation,
    )
    list_sort_config = ListQuerySortConfig(
        fields=tuple(
            EndpointSortField(
                query_name=sort_field.value,
                item_field_name=TransactionSortableField[sort_field.name].name.lower(),
            )
            for sort_field in TransactionListSortField
        ),
        default_sort=(TransactionListSortField.CREATED_AT.value,),
    )
    router = APIRouter(prefix="/transaction", tags=["Transaction"])

    @router.get(
        path="/list",
        response_model=PageResponse[TransactionSummaryResponse],
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to list persisted active transactions with offset/limit "
            "pagination and optional sort expressions such as `effective_at` or "
            "`-created_at`."
        ),
        responses={
            200: {
                "description": (
                    "The paginated transaction collection was returned successfully."
                ),
            },
            400: {
                "description": "The pagination query parameters failed validation.",
            },
        },
        summary="List Transactions",
    )
    async def list_transactions(
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
    ) -> PageResponse[TransactionSummaryResponse]:
        page = await transaction_input_port.list_transactions(list_query=list_query)

        return _to_transaction_page_response(page)

    @router.get(
        path="",
        response_model=TransactionResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to retrieve a single transaction by its id.",
        responses={
            200: {
                "description": "The transaction was found and returned successfully.",
            },
            404: {
                "description": "No transaction exists for the provided id.",
            },
            422: {
                "description": "The required id query parameter failed validation.",
            },
        },
        summary="Get Transaction",
    )
    async def get_transaction(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the transaction to retrieve.",
        ),
    ) -> TransactionResponse:
        with translate_exceptions_to_http(transaction_not_found_translation):
            transaction = await transaction_input_port.get_transaction(
                transaction_id=id,
            )

        return _to_transaction_response(transaction)

    @router.post(
        path="",
        response_model=TransactionResponse,
        status_code=status.HTTP_201_CREATED,
        description=(
            "Endpoint used to create a new transaction with subordinate entries."
        ),
        responses={
            201: {
                "description": "The transaction was created successfully.",
            },
            422: {
                "description": (
                    "- The request body failed validation.\n"
                    "- The transaction violated one or more business rules."
                ),
            },
        },
        summary="Create Transaction",
    )
    async def create_transaction(
        payload: CreateTransactionRequest,
    ) -> TransactionResponse:
        with translate_exceptions_to_http(*transaction_write_translations):
            transaction = await transaction_input_port.create_transaction(
                data=CreateTransactionData(
                    effective_at=payload.effective_at,
                    title=payload.title,
                    description=payload.description,
                    status=TransactionStatus[payload.status.name],
                    entries=tuple(_to_new_entry(entry) for entry in payload.entries),
                ),
            )

        return _to_transaction_response(transaction)

    @router.put(
        path="",
        response_model=TransactionResponse,
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to fully replace an existing pending transaction by its id."
        ),
        responses={
            200: {
                "description": "The transaction was updated successfully.",
            },
            404: {
                "description": "No transaction exists for the provided id.",
            },
            409: {
                "description": (
                    "The current transaction state does not allow the requested update."
                ),
            },
            422: {
                "description": (
                    "- The request body or query parameters failed validation.\n"
                    "- The transaction violated one or more business rules."
                ),
            },
        },
        summary="Update Transaction",
    )
    async def update_transaction(
        payload: UpdateTransactionRequest,
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the transaction to update.",
        ),
    ) -> TransactionResponse:
        with translate_exceptions_to_http(
            transaction_not_found_translation,
            transaction_must_be_pending_translation,
            *transaction_write_translations,
        ):
            transaction = await transaction_input_port.update_transaction(
                transaction_id=id,
                data=UpdateTransactionData(
                    effective_at=payload.effective_at,
                    title=payload.title,
                    description=payload.description,
                    entries=tuple(_to_new_entry(entry) for entry in payload.entries),
                ),
            )

        return _to_transaction_response(transaction)

    @router.post(
        path="/post",
        response_model=TransactionResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to post an existing pending transaction by its id.",
        responses={
            200: {
                "description": "The transaction was posted successfully.",
            },
            404: {
                "description": "No transaction exists for the provided id.",
            },
            409: {
                "description": "The current transaction state does not allow posting.",
            },
            422: {
                "description": (
                    "- The required id query parameter failed validation.\n"
                    "- The transaction violated one or more business rules."
                ),
            },
        },
        summary="Post Transaction",
    )
    async def post_transaction(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the transaction to post.",
        ),
    ) -> TransactionResponse:
        with translate_exceptions_to_http(
            transaction_not_found_translation,
            transaction_status_transition_not_allowed_translation,
            transaction_entries_must_balance_translation,
            transaction_entry_currency_not_found_translation,
            transaction_entry_exchange_rate_unavailable_translation,
        ):
            transaction = await transaction_input_port.post_transaction(
                transaction_id=id,
            )

        return _to_transaction_response(transaction)

    @router.post(
        path="/void",
        response_model=TransactionResponse,
        status_code=status.HTTP_200_OK,
        description="Endpoint used to void an existing pending transaction by its id.",
        responses={
            200: {
                "description": "The transaction was voided successfully.",
            },
            404: {
                "description": "No transaction exists for the provided id.",
            },
            409: {
                "description": "The current transaction state does not allow voiding.",
            },
            422: {
                "description": "The required id query parameter failed validation.",
            },
        },
        summary="Void Transaction",
    )
    async def void_transaction(
        id: int = Query(
            ...,
            ge=1,
            description="Identifier of the transaction to void.",
        ),
    ) -> TransactionResponse:
        with translate_exceptions_to_http(
            transaction_not_found_translation,
            transaction_status_transition_not_allowed_translation,
        ):
            transaction = await transaction_input_port.void_transaction(
                transaction_id=id,
            )

        return _to_transaction_response(transaction)

    return router

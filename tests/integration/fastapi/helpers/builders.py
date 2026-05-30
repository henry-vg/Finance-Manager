from typing import Any


def build_page_response(
    items: list[dict[str, Any]],
    *,
    offset: int = 0,
    limit: int = 10,
    total: int | None = None,
) -> dict[str, Any]:
    return {
        "items": items,
        "offset": offset,
        "limit": limit,
        "total": len(items) if total is None else total,
    }


def build_currency_create_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "iso_code": "BRL",
        "iso_numeric": "986",
        "name": "Real",
        "symbol": "R$",
        "decimal_places": 2,
    } | overrides


def build_currency_update_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "iso_code": "USD",
        "iso_numeric": "840",
        "name": "Dólar",
        "symbol": "$",
        "decimal_places": 2,
    } | overrides


def build_currency_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "iso_code": "BRL",
        "iso_numeric": "986",
        "name": "Real",
        "symbol": "R$",
        "decimal_places": 2,
        "storage_decimal_places": 3,
    } | overrides


def build_updated_currency_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
        "iso_code": "USD",
        "iso_numeric": "840",
        "name": "Dólar",
        "symbol": "$",
        "decimal_places": 2,
        "storage_decimal_places": 3,
    } | overrides


def build_tag_create_payload(**overrides: Any) -> dict[str, Any]:
    return {"title": "Food"} | overrides


def build_tag_update_payload(**overrides: Any) -> dict[str, Any]:
    return {"title": "Utilities"} | overrides


def build_tag_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "title": "Food",
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
    } | overrides


def build_updated_tag_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "title": "Utilities",
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
    } | overrides


def build_ledger_account_create_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Main Account",
        "type": "asset",
        "instrument_kind": "bank_account",
    } | overrides


def build_ledger_account_update_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Credit Card",
        "type": "liability",
        "instrument_kind": "credit_card",
    } | overrides


def build_ledger_account_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "title": "Main Account",
        "type": "asset",
        "instrument_kind": "bank_account",
        "balances": [],
    } | overrides


def build_updated_ledger_account_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
        "title": "Credit Card",
        "type": "liability",
        "instrument_kind": "credit_card",
        "balances": [],
    } | overrides


def build_transaction_create_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "effective_at": "2026-05-11T00:00:00.000Z",
        "title": "Airline tickets",
        "description": "Family vacation purchase",
        "status": "pending",
        "entries": [
            {
                "ledger_account_id": 1,
                "amount": "1200.00",
                "currency_id": 1,
                "statement_closing_date": None,
                "statement_due_date": None,
                "entry_tags": [
                    {"tag_id": 10},
                    {"tag_id": 11},
                ],
            },
            {
                "ledger_account_id": 2,
                "amount": "-1200.00",
                "currency_id": 1,
                "statement_closing_date": "2026-05-31",
                "statement_due_date": "2026-06-10",
                "entry_tags": [],
            },
        ],
    } | overrides


def build_transaction_update_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "effective_at": "2026-05-12T00:00:00.000Z",
        "title": "Updated airline tickets",
        "description": "Updated family vacation purchase",
        "entries": [
            {
                "ledger_account_id": 1,
                "amount": "1300.00",
                "currency_id": 1,
                "statement_closing_date": None,
                "statement_due_date": None,
                "entry_tags": [{"tag_id": 11}],
            },
            {
                "ledger_account_id": 2,
                "amount": "-1300.00",
                "currency_id": 1,
                "statement_closing_date": "2026-05-31",
                "statement_due_date": "2026-06-10",
                "entry_tags": [],
            },
        ],
    } | overrides


def build_transaction_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "effective_at": "2026-05-11T00:00:00.000Z",
        "title": "Airline tickets",
        "description": "Family vacation purchase",
        "status": "pending",
        "entries": [
            {
                "entry": {
                    "id": 100,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": "2026-05-01T00:00:00.000Z",
                    "transaction_id": 1,
                    "ledger_account_id": 1,
                    "amount": "1200.00",
                    "currency_id": 1,
                    "statement_closing_date": None,
                    "statement_due_date": None,
                },
                "entry_tags": [
                    {"entry_id": 100, "tag_id": 10},
                    {"entry_id": 100, "tag_id": 11},
                ],
            },
            {
                "entry": {
                    "id": 101,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": "2026-05-01T00:00:00.000Z",
                    "transaction_id": 1,
                    "ledger_account_id": 2,
                    "amount": "-1200.00",
                    "currency_id": 1,
                    "statement_closing_date": "2026-05-31",
                    "statement_due_date": "2026-06-10",
                },
                "entry_tags": [],
            },
        ],
    } | overrides


def build_updated_transaction_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
        "effective_at": "2026-05-12T00:00:00.000Z",
        "title": "Updated airline tickets",
        "description": "Updated family vacation purchase",
        "status": "pending",
        "entries": [
            {
                "entry": {
                    "id": 100,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": "2026-05-02T00:00:00.000Z",
                    "transaction_id": 1,
                    "ledger_account_id": 1,
                    "amount": "1300.00",
                    "currency_id": 1,
                    "statement_closing_date": None,
                    "statement_due_date": None,
                },
                "entry_tags": [{"entry_id": 100, "tag_id": 11}],
            },
            {
                "entry": {
                    "id": 101,
                    "created_at": "2026-05-01T00:00:00.000Z",
                    "updated_at": "2026-05-02T00:00:00.000Z",
                    "transaction_id": 1,
                    "ledger_account_id": 2,
                    "amount": "-1300.00",
                    "currency_id": 1,
                    "statement_closing_date": "2026-05-31",
                    "statement_due_date": "2026-06-10",
                },
                "entry_tags": [],
            },
        ],
    } | overrides


def build_posted_transaction_response(**overrides: Any) -> dict[str, Any]:
    return build_transaction_response(
        updated_at="2026-05-02T00:00:00.000Z",
        status="posted",
        **overrides,
    )


def build_voided_transaction_response(**overrides: Any) -> dict[str, Any]:
    return build_transaction_response(
        updated_at="2026-05-02T00:00:00.000Z",
        status="voided",
        **overrides,
    )


def build_user_create_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "password": "plain-password",
        "birth_date": "1815-12-10",
    } | overrides


def build_user_update_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@example.com",
        "password": "new-password",
        "birth_date": "1906-12-09",
    } | overrides


def build_user_response(**overrides: Any) -> dict[str, Any]:
    return {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "birth_date": "1815-12-10",
        "created_at": "2026-05-03T12:30:15.123Z",
        "updated_at": "2026-05-03T12:30:15.123Z",
    } | overrides


def build_updated_user_response(**overrides: Any) -> dict[str, Any]:
    return {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@example.com",
        "birth_date": "1906-12-09",
        "created_at": "2026-05-03T12:30:15.123Z",
        "updated_at": "2026-05-03T13:45:30.456Z",
    } | overrides

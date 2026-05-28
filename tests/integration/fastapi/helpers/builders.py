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
        "kind": "bank_account",
        "currency_iso_code": "BRL",
    } | overrides


def build_ledger_account_update_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Credit Card",
        "type": "liability",
        "kind": "credit_card",
        "currency_iso_code": "USD",
    } | overrides


def build_ledger_account_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-01T00:00:00.000Z",
        "title": "Main Account",
        "type": "asset",
        "kind": "bank_account",
        "currency_iso_code": "BRL",
    } | overrides


def build_updated_ledger_account_response(**overrides: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "created_at": "2026-05-01T00:00:00.000Z",
        "updated_at": "2026-05-02T00:00:00.000Z",
        "title": "Credit Card",
        "type": "liability",
        "kind": "credit_card",
        "currency_iso_code": "USD",
    } | overrides


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

import httpx
import pytest

from tests.integration.fastapi.app_builder import create_default_test_app
from tests.integration.fastapi.stubs import InMemoryLedgerAccountInputPortStub


@pytest.mark.anyio
async def test_ledger_account_crud_flow_through_http_app(
    ledger_account_input_port_stub: InMemoryLedgerAccountInputPortStub,
) -> None:
    app = create_default_test_app(
        ledger_account_input_port=ledger_account_input_port_stub,
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/ledger-account",
            json={
                "title": "Main Account",
                "type": "asset",
                "kind": "bank_account",
                "currency_iso_code": "BRL",
            },
        )
        created_id = create_response.json()["id"]
        get_response = await client.get("/ledger-account", params={"id": created_id})
        list_response = await client.get("/ledger-account/list")
        update_response = await client.put(
            "/ledger-account",
            params={"id": created_id},
            json={
                "title": "Credit Card",
                "type": "liability",
                "kind": "credit_card",
                "currency_iso_code": "USD",
            },
        )
        delete_response = await client.delete(
            "/ledger-account",
            params={"id": created_id},
        )

    assert create_response.status_code == 201
    assert list(create_response.json().keys()) == [
        "id",
        "created_at",
        "updated_at",
        "title",
        "type",
        "kind",
        "currency_iso_code",
    ]
    assert create_response.json()["title"] == "Main Account"
    assert get_response.status_code == 200
    assert list(get_response.json().keys()) == [
        "id",
        "created_at",
        "updated_at",
        "title",
        "type",
        "kind",
        "currency_iso_code",
    ]
    assert get_response.json()["id"] == created_id
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Credit Card"
    assert update_response.json()["type"] == "liability"
    assert delete_response.status_code == 204

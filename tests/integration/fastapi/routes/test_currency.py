import httpx
import pytest

from tests.integration.fastapi.app_builder import create_default_test_app
from tests.integration.fastapi.stubs import CurrencyInputPortStub


@pytest.mark.anyio
async def test_currency_crud_flow_through_http_app(
    currency_input_port_stub: CurrencyInputPortStub,
) -> None:
    app = create_default_test_app(currency_input_port=currency_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/currency",
            json={
                "iso_code": "BRL",
                "iso_numeric": "986",
                "name": "Real",
                "symbol": "R$",
                "decimal_places": 2,
            },
        )
        created_id = create_response.json()["id"]
        get_response = await client.get("/currency", params={"id": created_id})
        list_response = await client.get("/currency/list")
        update_response = await client.put(
            "/currency",
            params={"id": created_id},
            json={
                "iso_code": "USD",
                "iso_numeric": "840",
                "name": "Dólar",
                "symbol": "$",
                "decimal_places": 2,
            },
        )
        delete_response = await client.delete(
            "/currency",
            params={"id": created_id},
        )

    assert create_response.status_code == 201
    assert list(create_response.json().keys()) == [
        "id",
        "created_at",
        "updated_at",
        "iso_code",
        "iso_numeric",
        "name",
        "symbol",
        "decimal_places",
        "storage_decimal_places",
    ]
    assert create_response.json()["name"] == "Real"
    assert create_response.json()["storage_decimal_places"] == 3
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_id
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["iso_code"] == "USD"
    assert update_response.json()["name"] == "Dólar"
    assert delete_response.status_code == 204

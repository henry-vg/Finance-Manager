import pytest

from tests.integration.fastapi.helpers.builders import (
    build_currency_create_payload,
    build_currency_response,
    build_currency_update_payload,
    build_page_response,
    build_updated_currency_response,
)
from tests.integration.fastapi.helpers.stubs import CurrencyInputPortStub


@pytest.mark.anyio
async def test_currency_crud_flow_through_http_app(
    currency_input_port_stub: CurrencyInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(currency_input_port=currency_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/currency",
            json=build_currency_create_payload(),
        )
        created_id = create_response.json()["id"]
        get_response = await client.get("/currency", params={"id": created_id})
        list_response = await client.get(
            "/currency/list",
            params={"offset": 0, "limit": 10},
        )
        update_response = await client.put(
            "/currency",
            params={"id": created_id},
            json=build_currency_update_payload(),
        )
        delete_response = await client.delete(
            "/currency",
            params={"id": created_id},
        )
        missing_response = await client.get("/currency", params={"id": created_id})

    assert create_response.status_code == 201
    assert create_response.json() == build_currency_response()
    assert get_response.status_code == 200
    assert get_response.json() == build_currency_response(id=created_id)
    assert list_response.status_code == 200
    assert list_response.json() == build_page_response(
        [build_currency_response(id=created_id)],
    )
    assert update_response.status_code == 200
    assert update_response.json() == build_updated_currency_response()
    assert delete_response.status_code == 204
    assert currency_input_port_stub.delete_calls == [(created_id, False)]
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_delete_currency_hard_deletes_when_requested_through_http_app(
    currency_input_port_stub: CurrencyInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(currency_input_port=currency_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/currency",
            json=build_currency_create_payload(),
        )
        created_id = create_response.json()["id"]
        delete_response = await client.delete(
            "/currency",
            params={"id": created_id, "hard_delete": "true"},
        )
        missing_response = await client.get("/currency", params={"id": created_id})

    assert delete_response.status_code == 204
    assert currency_input_port_stub.delete_calls == [(created_id, True)]
    assert missing_response.status_code == 404

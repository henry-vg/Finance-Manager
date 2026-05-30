import pytest

from tests.integration.fastapi.helpers.builders import (
    build_posted_transaction_response,
    build_transaction_create_payload,
    build_transaction_response,
    build_transaction_update_payload,
    build_updated_transaction_response,
    build_voided_transaction_response,
)
from tests.integration.fastapi.helpers.stubs import TransactionInputPortStub


@pytest.mark.anyio
async def test_transaction_create_get_and_update_flow_through_http_app(
    transaction_input_port_stub: TransactionInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(transaction_input_port=transaction_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/transaction",
            json=build_transaction_create_payload(),
        )
        created_id = create_response.json()["id"]
        get_response = await client.get("/transaction", params={"id": created_id})
        update_response = await client.put(
            "/transaction",
            params={"id": created_id},
            json=build_transaction_update_payload(),
        )

    assert create_response.status_code == 201
    assert create_response.json() == build_transaction_response()
    assert get_response.status_code == 200
    assert get_response.json() == build_transaction_response(id=created_id)
    assert update_response.status_code == 200
    assert update_response.json() == build_updated_transaction_response(id=created_id)


@pytest.mark.anyio
async def test_transaction_post_flow_through_http_app(
    transaction_input_port_stub: TransactionInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(transaction_input_port=transaction_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/transaction",
            json=build_transaction_create_payload(),
        )
        created_id = create_response.json()["id"]
        post_response = await client.post(
            "/transaction/post", params={"id": created_id}
        )

    assert post_response.status_code == 200
    assert post_response.json() == build_posted_transaction_response(id=created_id)


@pytest.mark.anyio
async def test_transaction_void_flow_through_http_app(
    transaction_input_port_stub: TransactionInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(transaction_input_port=transaction_input_port_stub)

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/transaction",
            json=build_transaction_create_payload(),
        )
        created_id = create_response.json()["id"]
        void_response = await client.post(
            "/transaction/void", params={"id": created_id}
        )

    assert void_response.status_code == 200
    assert void_response.json() == build_voided_transaction_response(id=created_id)

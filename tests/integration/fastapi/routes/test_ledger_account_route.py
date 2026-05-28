import pytest

from tests.integration.fastapi.helpers.builders import (
    build_ledger_account_create_payload,
    build_ledger_account_response,
    build_ledger_account_update_payload,
    build_page_response,
    build_updated_ledger_account_response,
)
from tests.integration.fastapi.helpers.stubs import LedgerAccountInputPortStub


@pytest.mark.anyio
async def test_ledger_account_crud_flow_through_http_app(
    ledger_account_input_port_stub: LedgerAccountInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(
        ledger_account_input_port=ledger_account_input_port_stub,
    )

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/ledger-account",
            json=build_ledger_account_create_payload(),
        )
        created_id = create_response.json()["id"]
        get_response = await client.get("/ledger-account", params={"id": created_id})
        list_response = await client.get(
            "/ledger-account/list",
            params={"offset": 0, "limit": 10},
        )
        update_response = await client.put(
            "/ledger-account",
            params={"id": created_id},
            json=build_ledger_account_update_payload(),
        )
        delete_response = await client.delete(
            "/ledger-account",
            params={"id": created_id},
        )
        missing_response = await client.get(
            "/ledger-account",
            params={"id": created_id},
        )

    assert create_response.status_code == 201
    assert create_response.json() == build_ledger_account_response()
    assert get_response.status_code == 200
    assert get_response.json() == build_ledger_account_response(id=created_id)
    assert list_response.status_code == 200
    assert list_response.json() == build_page_response(
        [build_ledger_account_response(id=created_id)],
    )
    assert update_response.status_code == 200
    assert update_response.json() == build_updated_ledger_account_response()
    assert delete_response.status_code == 204
    assert ledger_account_input_port_stub.delete_calls == [(created_id, False)]
    assert missing_response.status_code == 404


@pytest.mark.anyio
async def test_delete_ledger_account_hard_deletes_when_requested_through_http_app(
    ledger_account_input_port_stub: LedgerAccountInputPortStub,
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(
        ledger_account_input_port=ledger_account_input_port_stub,
    )

    async with fastapi_client_factory(app) as client:
        create_response = await client.post(
            "/ledger-account",
            json=build_ledger_account_create_payload(),
        )
        created_id = create_response.json()["id"]
        delete_response = await client.delete(
            "/ledger-account",
            params={"id": created_id, "hard_delete": "true"},
        )
        missing_response = await client.get(
            "/ledger-account",
            params={"id": created_id},
        )

    assert delete_response.status_code == 204
    assert ledger_account_input_port_stub.delete_calls == [(created_id, True)]
    assert missing_response.status_code == 404

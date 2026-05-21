import httpx
import pytest

from tests.integration.fastapi.app_builder import create_default_test_app
from tests.integration.fastapi.stubs import InMemoryTagInputPortStub


@pytest.mark.anyio
async def test_tag_crud_flow_through_http_app(
    tag_input_port_stub: InMemoryTagInputPortStub,
) -> None:
    app = create_default_test_app(tag_input_port=tag_input_port_stub)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post("/tag", json={"title": "Food"})
        created_id = create_response.json()["id"]
        get_response = await client.get("/tag", params={"id": created_id})
        list_response = await client.get("/tag/list")
        update_response = await client.put(
            "/tag",
            params={"id": created_id},
            json={"title": "Utilities"},
        )
        delete_response = await client.delete("/tag", params={"id": created_id})

    assert create_response.status_code == 201
    assert create_response.json()["title"] == "Food"
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_id
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Utilities"
    assert delete_response.status_code == 204

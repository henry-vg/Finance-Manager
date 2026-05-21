import httpx
import pytest

from tests.integration.fastapi.app_builder import create_default_test_app


@pytest.mark.anyio
async def test_docs_endpoint_is_customized_and_returns_html() -> None:
    app = create_default_test_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text
    assert 'document.documentElement.classList.add("dark-mode")' in response.text

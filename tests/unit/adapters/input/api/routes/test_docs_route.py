import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.docs_route import create_router


@pytest.mark.anyio
async def test_get_docs_returns_html_with_dark_mode_enabled():
    app = FastAPI(docs_url=None)
    app.include_router(
        create_router(
            docs_url="/docs",
            docs_title="Docs - Finance Manager API",
            docs_dark_mode=True,
            openapi_url="/openapi.json",
        ),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text
    assert 'document.documentElement.classList.add("dark-mode")' in response.text


@pytest.mark.anyio
async def test_get_docs_returns_html_without_dark_mode_script_when_disabled():
    app = FastAPI(docs_url=None)
    app.include_router(
        create_router(
            docs_url="/docs",
            docs_title="Docs - Finance Manager API",
            docs_dark_mode=False,
            openapi_url="/openapi.json",
        ),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert "/openapi.json" in response.text
    assert 'document.documentElement.classList.add("dark-mode")' not in response.text

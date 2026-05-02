import httpx
import pytest


@pytest.mark.anyio
async def test_healthz_liveness_returns_ok(app):
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_healthz_readiness_returns_ok(app):
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "dependencies": {"fastapi": "ok"}}

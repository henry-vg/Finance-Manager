import httpx
import pytest

from src.core.usecases.healthz_usecase import HealthzUseCase
from tests.integration.fastapi.app_builder import create_default_test_app
from tests.integration.fastapi.stubs import (
    HealthyDatabaseHealthOutputPortStub,
    UnhealthyDatabaseHealthOutputPortStub,
)


@pytest.mark.anyio
async def test_healthz_liveness_returns_ok():
    app = create_default_test_app(
        healthz_input_port=HealthzUseCase(HealthyDatabaseHealthOutputPortStub()),
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_healthz_readiness_returns_ok():
    app = create_default_test_app(
        healthz_input_port=HealthzUseCase(HealthyDatabaseHealthOutputPortStub()),
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {"api": "ok", "database": "ok"},
    }


@pytest.mark.anyio
async def test_healthz_readiness_returns_not_ok_when_database_is_unavailable():
    app = create_default_test_app(
        healthz_input_port=HealthzUseCase(UnhealthyDatabaseHealthOutputPortStub()),
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ok",
        "dependencies": {"api": "ok", "database": "not_ok"},
    }

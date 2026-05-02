import httpx
import pytest

from src.core.domain.healthz import HealthzStatus
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.use_cases.healthz_use_case import HealthzUseCase
from src.infra.fastapi.app import create_http_app
from src.infra.settings import load_settings


class _UnhealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.NOT_OK


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
    assert response.json() == {
        "status": "ok",
        "dependencies": {"api": "ok", "database": "ok"},
    }


@pytest.mark.anyio
async def test_healthz_readiness_returns_not_ok_when_database_is_unavailable():
    unhealthy_database_health_output_port_stub = (
        _UnhealthyDatabaseHealthOutputPortStub()
    )
    app = create_http_app(
        settings=load_settings(),
        healthz_input_port=HealthzUseCase(unhealthy_database_health_output_port_stub),
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ok",
        "dependencies": {"api": "ok", "database": "not_ok"},
    }

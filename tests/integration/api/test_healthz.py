import httpx
import pytest
from fastapi import FastAPI

from src.core.domain.healthz import HealthzStatus
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.use_cases.healthz_use_case import HealthzUseCase
from src.infra.fastapi.app import create_http_app
from src.infra.settings import load_settings


class _UnhealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.NOT_OK


class _HealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.OK


def _create_test_app(
    database_health_output_port: DatabaseHealthOutputPort,
) -> FastAPI:
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=HealthzUseCase(database_health_output_port),
    )


@pytest.mark.anyio
async def test_healthz_liveness_returns_ok():
    app = _create_test_app(_HealthyDatabaseHealthOutputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_healthz_readiness_returns_ok():
    app = _create_test_app(_HealthyDatabaseHealthOutputPortStub())
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
    app = _create_test_app(_UnhealthyDatabaseHealthOutputPortStub())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ok",
        "dependencies": {"api": "ok", "database": "not_ok"},
    }

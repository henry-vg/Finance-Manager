import pytest

from src.core.usecases.healthz_usecase import HealthzUseCase
from tests.integration.fastapi.helpers.stubs import (
    HealthyDatabaseHealthOutputPortStub,
    UnhealthyDatabaseHealthOutputPortStub,
)


@pytest.mark.anyio
async def test_get_healthz_liveness_returns_ok(
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(
        healthz_input_port=HealthzUseCase(HealthyDatabaseHealthOutputPortStub()),
    )

    async with fastapi_client_factory(app) as client:
        response = await client.get("/healthz/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_get_healthz_readiness_returns_ok(
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(
        healthz_input_port=HealthzUseCase(HealthyDatabaseHealthOutputPortStub()),
    )

    async with fastapi_client_factory(app) as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {"api": "ok", "database": "ok"},
    }


@pytest.mark.anyio
async def test_get_healthz_readiness_returns_503_when_database_is_unavailable(
    fastapi_app_builder,
    fastapi_client_factory,
) -> None:
    app = fastapi_app_builder(
        healthz_input_port=HealthzUseCase(UnhealthyDatabaseHealthOutputPortStub()),
    )

    async with fastapi_client_factory(app) as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ok",
        "dependencies": {"api": "ok", "database": "not_ok"},
    }

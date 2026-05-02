import httpx
import pytest
from fastapi import FastAPI

from src.adapters.input.api.routes.healthz_route import create_router
from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort


class _NotReadyHealthzUseCase(HealthzInputPort):
    def get_healthz_liveness(self) -> HealthzLiveness:
        return HealthzLiveness(status=HealthzStatus.OK)

    def get_healthz_readiness(self) -> HealthzReadiness:
        return HealthzReadiness(
            status=HealthzStatus.NOT_OK,
            dependencies=HealthzReadinessDependencies(api_server=HealthzStatus.NOT_OK),
        )


@pytest.mark.anyio
async def test_healthz_readiness_returns_503_when_not_ok():
    app = FastAPI()
    app.include_router(create_router(_NotReadyHealthzUseCase()))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ok",
        "dependencies": {"fastapi": "not_ok"},
    }

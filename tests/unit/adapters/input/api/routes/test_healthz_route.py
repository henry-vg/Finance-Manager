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


class _ReadyHealthzUseCase(HealthzInputPort):
    def get_healthz_liveness(self) -> HealthzLiveness:
        return HealthzLiveness(status=HealthzStatus.OK)

    def get_healthz_readiness(self) -> HealthzReadiness:
        return HealthzReadiness(
            status=HealthzStatus.OK,
            dependencies=HealthzReadinessDependencies(api_server=HealthzStatus.OK),
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


@pytest.mark.anyio
async def test_healthz_liveness_returns_200_when_ok():
    app = FastAPI()
    app.include_router(create_router(_ReadyHealthzUseCase()))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_healthz_readiness_returns_200_when_ok():
    app = FastAPI()
    app.include_router(create_router(_ReadyHealthzUseCase()))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {"fastapi": "ok"},
    }
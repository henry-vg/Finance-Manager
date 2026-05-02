from fastapi.routing import APIRoute

from src.adapters.input.api.router import create_api_router
from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort


class _HealthyHealthzUseCase(HealthzInputPort):
    def get_healthz_liveness(self) -> HealthzLiveness:
        return HealthzLiveness(status=HealthzStatus.OK)

    def get_healthz_readiness(self) -> HealthzReadiness:
        return HealthzReadiness(
            status=HealthzStatus.OK,
            dependencies=HealthzReadinessDependencies(api_server=HealthzStatus.OK),
        )


def test_create_api_router_mounts_docs_and_healthz_routes():
    router = create_api_router(
        docs_url="/docs",
        docs_title="Docs",
        docs_dark_mode=True,
        openapi_url="/openapi.json",
        healthz_input_port=_HealthyHealthzUseCase(),
    )

    routes_by_path = {
        route.path: route for route in router.routes if isinstance(route, APIRoute)
    }

    assert "/docs" in routes_by_path
    assert "/healthz/liveness" in routes_by_path
    assert "/healthz/readiness" in routes_by_path
    assert routes_by_path["/docs"].include_in_schema is False

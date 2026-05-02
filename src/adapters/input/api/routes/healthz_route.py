from fastapi import (
    APIRouter,
    Response,
    status,
)

from src.core.domain.healthz import HealthzStatus as DomainHealthzStatus
from src.core.ports.input.healthz_input_port import HealthzInputPort

from ..schemas.healthz_schema import (
    HealthzLivenessResponse,
    HealthzReadinessDependencies,
    HealthzReadinessResponse,
    HealthzStatus,
)


def create_router(
    healthz_input_port: HealthzInputPort,
) -> APIRouter:
    router = APIRouter(
        prefix="/healthz",
        tags=["HealthZ"],
    )

    @router.get(
        path="/liveness",
        response_model=HealthzLivenessResponse,
        status_code=200,
        description=(
            "Endpoint used to verify that the application process is running "
            "and responsive. Liveness checks do not validate external dependencies."
        ),
        responses={
            200: {
                "description": "The application is alive and responsive.",
            },
        },
        summary="Healthz Liveness",
    )
    def get_healthz_liveness() -> HealthzLivenessResponse:
        result = healthz_input_port.get_healthz_liveness()

        return HealthzLivenessResponse(
            status=HealthzStatus(result.status.value),
        )

    @router.get(
        path="/readiness",
        response_model=HealthzReadinessResponse,
        status_code=200,
        description=(
            "Endpoint used to determine whether the application is ready to receive traffic. "
            "Readiness checks may validate required dependencies and internal state."
        ),
        responses={
            200: {
                "description": "The application is ready to receive traffic.",
            },
            503: {
                "description": "The application is not ready to receive traffic because one or more required services are unavailable.",
            },
        },
        summary="Healthz Readiness",
    )
    def get_healthz_readiness(response: Response) -> HealthzReadinessResponse:
        result = healthz_input_port.get_healthz_readiness()

        response.status_code = (
            status.HTTP_200_OK
            if result.status == DomainHealthzStatus.OK
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return HealthzReadinessResponse(
            status=HealthzStatus(result.status.value),
            dependencies=HealthzReadinessDependencies(
                fastapi=HealthzStatus(result.dependencies.api_server.value),
            ),
        )

    return router

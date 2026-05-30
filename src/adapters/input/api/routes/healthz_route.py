from fastapi import (
    APIRouter,
    Response,
    status,
)

from src.core.domain.healthz import HealthzStatus as DomainHealthzStatus
from src.core.ports.input.healthz_input_port import HealthzInputPort

from ..schemas.healthz_schema import (
    GetHealthzLivenessResponse,
    GetHealthzReadinessDependencies,
    GetHealthzReadinessResponse,
    HealthzStatusSchema,
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
        response_model=GetHealthzLivenessResponse,
        status_code=status.HTTP_200_OK,
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
    async def get_healthz_liveness() -> GetHealthzLivenessResponse:
        result = await healthz_input_port.get_healthz_liveness()

        return GetHealthzLivenessResponse(
            status=HealthzStatusSchema[result.status.name],
        )

    @router.get(
        path="/readiness",
        response_model=GetHealthzReadinessResponse,
        status_code=status.HTTP_200_OK,
        description=(
            "Endpoint used to determine whether the application is ready "
            "to receive traffic. "
            "Readiness checks may validate required dependencies and internal state."
        ),
        responses={
            200: {
                "description": "The application is ready to receive traffic.",
            },
            503: {
                "description": (
                    "The application is not ready to receive traffic because "
                    "one or more required services are unavailable."
                ),
            },
        },
        summary="Healthz Readiness",
    )
    async def get_healthz_readiness(response: Response) -> GetHealthzReadinessResponse:
        result = await healthz_input_port.get_healthz_readiness()

        response.status_code = (
            status.HTTP_200_OK
            if result.status == DomainHealthzStatus.OK
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return GetHealthzReadinessResponse(
            status=HealthzStatusSchema[result.status.name],
            dependencies=GetHealthzReadinessDependencies(
                api=HealthzStatusSchema[result.dependencies.api.name],
                database=HealthzStatusSchema[result.dependencies.database.name],
            ),
        )

    return router

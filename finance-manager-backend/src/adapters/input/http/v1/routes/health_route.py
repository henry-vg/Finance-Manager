from fastapi import APIRouter

from src.adapters.input.http.v1.schemas.health_schema import HealthResponse
from src.core.use_cases.health_use_case import HealthUseCase

router = APIRouter()


@router.get(
    path="/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Health",
)
def ping():
    health_use_case = HealthUseCase()
    result = health_use_case.execute()

    return HealthResponse(
        status=result.status.value,
    )

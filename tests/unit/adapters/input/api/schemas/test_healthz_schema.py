import json

from src.adapters.input.api.schemas.healthz_schema import (
    GetHealthzReadinessDependencies,
    GetHealthzReadinessResponse,
    HealthzStatusResponse,
)


def test_get_healthz_readiness_response_serializes_nested_status_values() -> None:
    response = GetHealthzReadinessResponse(
        status=HealthzStatusResponse.OK,
        dependencies=GetHealthzReadinessDependencies(
            api=HealthzStatusResponse.OK,
            database=HealthzStatusResponse.NOT_OK,
        ),
    )

    payload = json.loads(response.model_dump_json())

    assert payload == {
        "status": "ok",
        "dependencies": {
            "api": "ok",
            "database": "not_ok",
        },
    }

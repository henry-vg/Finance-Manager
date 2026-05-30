import json

from src.adapters.input.api.schemas.healthz_schema import (
    GetHealthzReadinessDependencies,
    GetHealthzReadinessResponse,
    HealthzStatusSchema,
)


def test_get_healthz_readiness_response_serializes_nested_status_values() -> None:
    response = GetHealthzReadinessResponse(
        status=HealthzStatusSchema.OK,
        dependencies=GetHealthzReadinessDependencies(
            api=HealthzStatusSchema.OK,
            database=HealthzStatusSchema.NOT_OK,
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

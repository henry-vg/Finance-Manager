from enum import StrEnum

from .base import ApiSchemaBase


class HealthzStatusResponse(StrEnum):
    OK = "ok"
    NOT_OK = "not_ok"


class GetHealthzLivenessResponse(ApiSchemaBase):
    status: HealthzStatusResponse


class GetHealthzReadinessDependencies(ApiSchemaBase):
    api: HealthzStatusResponse
    database: HealthzStatusResponse


class GetHealthzReadinessResponse(ApiSchemaBase):
    status: HealthzStatusResponse
    dependencies: GetHealthzReadinessDependencies

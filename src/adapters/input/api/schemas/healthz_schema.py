from enum import StrEnum

from .base import ApiSchemaBase


class HealthzStatus(StrEnum):
    OK = "ok"
    NOT_OK = "not_ok"


class GetHealthzLivenessResponse(ApiSchemaBase):
    status: HealthzStatus


class GetHealthzReadinessDependencies(ApiSchemaBase):
    api: HealthzStatus
    database: HealthzStatus


class GetHealthzReadinessResponse(ApiSchemaBase):
    status: HealthzStatus
    dependencies: GetHealthzReadinessDependencies

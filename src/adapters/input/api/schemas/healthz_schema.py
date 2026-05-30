from enum import StrEnum

from .base import ApiSchemaBase


class HealthzStatusSchema(StrEnum):
    OK = "ok"
    NOT_OK = "not_ok"


class GetHealthzLivenessResponse(ApiSchemaBase):
    status: HealthzStatusSchema


class GetHealthzReadinessDependencies(ApiSchemaBase):
    api: HealthzStatusSchema
    database: HealthzStatusSchema


class GetHealthzReadinessResponse(ApiSchemaBase):
    status: HealthzStatusSchema
    dependencies: GetHealthzReadinessDependencies

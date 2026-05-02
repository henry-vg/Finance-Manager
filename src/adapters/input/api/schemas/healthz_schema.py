from enum import StrEnum

from pydantic import BaseModel


class HealthzStatus(StrEnum):
    OK = "ok"
    NOT_OK = "not_ok"


class HealthzLivenessResponse(BaseModel):
    status: HealthzStatus


class HealthzReadinessDependencies(BaseModel):
    fastapi: HealthzStatus


class HealthzReadinessResponse(BaseModel):
    status: HealthzStatus
    dependencies: HealthzReadinessDependencies

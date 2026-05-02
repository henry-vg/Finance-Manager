from dataclasses import dataclass
from enum import StrEnum


class HealthzStatus(StrEnum):
    OK = "ok"
    NOT_OK = "not_ok"


@dataclass(frozen=True)
class HealthzLiveness:
    status: HealthzStatus


@dataclass(frozen=True)
class HealthzReadinessDependencies:
    api: HealthzStatus
    database: HealthzStatus


@dataclass(frozen=True)
class HealthzReadiness:
    status: HealthzStatus
    dependencies: HealthzReadinessDependencies

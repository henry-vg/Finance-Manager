from dataclasses import dataclass
from enum import IntEnum


class HealthzStatus(IntEnum):
    OK = 1
    NOT_OK = 2


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

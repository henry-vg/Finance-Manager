from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class Health:
    status: Status

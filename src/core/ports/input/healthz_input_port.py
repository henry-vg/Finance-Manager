from typing import Protocol

from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
)


class HealthzInputPort(Protocol):
    def get_healthz_liveness(self) -> HealthzLiveness: ...
    def get_healthz_readiness(self) -> HealthzReadiness: ...

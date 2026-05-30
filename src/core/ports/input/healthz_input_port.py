from typing import Protocol

from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
)


class HealthzInputPort(Protocol):  # pragma: no cover
    async def get_healthz_liveness(self) -> HealthzLiveness: ...
    async def get_healthz_readiness(self) -> HealthzReadiness: ...

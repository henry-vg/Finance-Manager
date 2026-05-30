from typing import Protocol

from src.core.domain.healthz import HealthzStatus


class DatabaseHealthOutputPort(Protocol):  # pragma: no cover
    async def get_database_status(self) -> HealthzStatus: ...

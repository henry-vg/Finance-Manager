import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.domain.healthz import HealthzStatus
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort

logger = logging.getLogger(__name__)


class SQLAlchemyPostgresHealthAdapter(DatabaseHealthOutputPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_database_status(self) -> HealthzStatus:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            logger.warning("Postgres readiness check failed.", exc_info=True)
            return HealthzStatus.NOT_OK

        return HealthzStatus.OK

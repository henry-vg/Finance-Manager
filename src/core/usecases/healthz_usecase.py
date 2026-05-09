from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort


class HealthzUseCase(HealthzInputPort):
    def __init__(
        self,
        database_health_output_port: DatabaseHealthOutputPort,
    ) -> None:
        self._database_health_output_port = database_health_output_port

    async def get_healthz_liveness(
        self,
    ) -> HealthzLiveness:
        return HealthzLiveness(
            status=HealthzStatus.OK,
        )

    async def get_healthz_readiness(
        self,
    ) -> HealthzReadiness:
        api_server_status = HealthzStatus.OK
        database_status = await self._database_health_output_port.get_database_status()

        status = (
            HealthzStatus.OK
            if all(
                dependency == HealthzStatus.OK
                for dependency in [
                    api_server_status,
                    database_status,
                ]
            )
            else HealthzStatus.NOT_OK
        )

        return HealthzReadiness(
            status=status,
            dependencies=HealthzReadinessDependencies(
                api=api_server_status,
                database=database_status,
            ),
        )
